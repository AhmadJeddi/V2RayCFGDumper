import base64
import json
import os
import shutil
import socket
import subprocess
import tempfile
import time

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit

import requests


# Lightweight HTTP endpoint used for proxy testing.
PROBE_URL = "https://www.gstatic.com/generate_204"

# Retry only after a failed probe.
ATTEMPTS = 2
RETRY_DELAY = 0.25

# (connect timeout, read timeout) in seconds.
PROBE_TIMEOUT = (3, 3)

# Maximum time allowed for sing-box to start.
STARTUP_TIMEOUT = 3

# Limit concurrent sing-box processes.
WORKERS = 8

SUPPORTED_SCHEMES = {
    "vless",
    "vmess",
    "trojan",
    "ss",
}


def _first(
    params: dict[str, list[str]],
    key: str,
    default: str = ""
) -> str:
    return params.get(key, [default])[0]


def _parse_bool(value: Any) -> bool:
    return str(value).lower() in {"1", "true", "yes"}


def _build_tls(
    params: dict[str, list[str]],
    host: str
) -> dict[str, Any] | None:
    security = _first(params, "security").lower()

    if security not in {"tls", "reality"}:
        return None

    # Build TLS settings for sing-box.
    tls: dict[str, Any] = {
        "enabled": True,
        "server_name": _first(params, "sni", host),
        "insecure": _parse_bool(
            _first(
                params,
                "insecure",
                _first(params, "allowInsecure", "0")
            )
        ),
    }

    alpn = _first(params, "alpn")

    if alpn:
        tls["alpn"] = [
            item for item in alpn.split(",")
            if item
        ]

    fingerprint = _first(params, "fp")

    if fingerprint:
        tls["utls"] = {
            "enabled": True,
            "fingerprint": fingerprint,
        }

    if security == "reality":
        public_key = _first(params, "pbk")

        if not public_key:
            raise ValueError("Reality config missing pbk")

        reality: dict[str, Any] = {
            "enabled": True,
            "public_key": public_key,
        }

        short_id = _first(params, "sid")

        if short_id:
            reality["short_id"] = short_id

        tls["reality"] = reality

    return tls


def _build_transport(
    params: dict[str, list[str]]
) -> dict[str, Any] | None:
    transport_type = _first(
        params,
        "type",
        _first(params, "net", "tcp")
    ).lower()

    if transport_type in {"", "tcp"}:
        return None

    path = unquote(_first(params, "path"))
    host = _first(params, "host")

    if transport_type == "ws":
        transport: dict[str, Any] = {
            "type": "ws"
        }

        if path:
            transport["path"] = path

        if host:
            transport["headers"] = {
                "Host": host
            }

        return transport

    if transport_type in {"grpc", "gun"}:
        service_name = _first(
            params,
            "serviceName",
            _first(params, "service_name")
        )

        if not service_name:
            raise ValueError(
                "gRPC config missing serviceName"
            )

        return {
            "type": "grpc",
            "service_name": service_name,
        }

    if transport_type in {"http", "h2"}:
        transport: dict[str, Any] = {
            "type": "http"
        }

        if host:
            transport["host"] = [host]

        if path:
            transport["path"] = path

        return transport

    if transport_type == "httpupgrade":
        transport = {
            "type": "httpupgrade"
        }

        if host:
            transport["host"] = host

        if path:
            transport["path"] = path

        return transport

    if transport_type == "quic":
        return {
            "type": "quic"
        }

    raise ValueError(
        f"Unsupported transport: {transport_type}"
    )


def _decode_base64_json(value: str) -> dict[str, Any]:
    # Decode the Base64-encoded VMess payload.
    value = value.strip()
    value += "=" * (-len(value) % 4)

    decoded = base64.urlsafe_b64decode(
        value
    ).decode("utf-8")

    data = json.loads(decoded)

    if not isinstance(data, dict):
        raise ValueError("Invalid VMess JSON")

    return data


def _parse_vmess(uri: str) -> dict[str, Any]:
    payload = (
        uri[len("vmess://"):]
        .split("#", 1)[0]
    )

    data = _decode_base64_json(payload)

    host = data.get("add") or data.get("address")
    uuid = data.get("id") or data.get("uuid")
    port = int(data.get("port", 0) or 0)

    if not host or not uuid or not port:
        raise ValueError(
            "Invalid VMess configuration"
        )

    # Convert VMess fields to common parameters.
    params: dict[str, list[str]] = {
        "security": [str(data.get("tls", ""))],
        "sni": [
            str(
                data.get("sni")
                or data.get("host", "")
            )
        ],
        "fp": [str(data.get("fp", ""))],
        "alpn": [str(data.get("alpn", ""))],
        "type": [
            str(
                data.get("type")
                or data.get("net", "")
            )
        ],
        "path": [str(data.get("path", ""))],
        "host": [str(data.get("host", ""))],
        "serviceName": [
            str(data.get("serviceName", ""))
        ],
        "insecure": [
            str(data.get("allowInsecure", "0"))
        ],
    }

    outbound: dict[str, Any] = {
        "type": "vmess",
        "tag": "proxy",
        "server": str(host),
        "server_port": port,
        "uuid": str(uuid),
        "security": str(data.get("scy", "auto")),
        "alter_id": int(
            data.get("aid", 0) or 0
        ),
    }

    tls = _build_tls(params, str(host))

    if tls:
        outbound["tls"] = tls

    transport = _build_transport(params)

    if transport:
        outbound["transport"] = transport

    return outbound


def _parse_shadowsocks(uri: str) -> dict[str, Any]:
    parsed = urlsplit(uri)

    host = parsed.hostname
    port = parsed.port

    if not host or not port:
        raise ValueError(
            "Invalid Shadowsocks endpoint"
        )

    if parsed.username:
        userinfo = unquote(parsed.username)

        if ":" not in userinfo:
            raise ValueError(
                "Invalid Shadowsocks userinfo"
            )

        method, password = userinfo.split(
            ":",
            1
        )

    else:
        # Decode the Base64 userinfo used by this format.
        payload = (
            uri[len("ss://"):]
            .split("#", 1)[0]
        )

        encoded = payload.split("@", 1)[0]
        encoded += "=" * (-len(encoded) % 4)

        decoded = base64.urlsafe_b64decode(
            encoded
        ).decode("utf-8")

        method, password = decoded.split(
            ":",
            1
        )

    return {
        "type": "shadowsocks",
        "tag": "proxy",
        "server": host,
        "server_port": port,
        "method": method,
        "password": password,
    }


def parse_config(uri: str) -> dict[str, Any]:
    # Convert a proxy URI to a sing-box outbound.
    uri = uri.strip()

    scheme = urlsplit(uri).scheme.lower()

    if scheme not in SUPPORTED_SCHEMES:
        raise ValueError(
            f"Unsupported scheme: {scheme}"
        )

    if scheme == "vmess":
        return _parse_vmess(uri)

    if scheme == "ss":
        return _parse_shadowsocks(uri)

    parsed = urlsplit(uri)

    params = parse_qs(
        parsed.query,
        keep_blank_values=True
    )

    host = parsed.hostname
    port = parsed.port

    if not host or not port:
        raise ValueError(
            "Missing server or port"
        )

    if scheme == "vless":
        uuid = unquote(
            parsed.username or ""
        )

        if not uuid:
            raise ValueError(
                "Missing VLESS UUID"
            )

        outbound: dict[str, Any] = {
            "type": "vless",
            "tag": "proxy",
            "server": host,
            "server_port": port,
            "uuid": uuid,
        }

        flow = _first(params, "flow")

        if flow:
            outbound["flow"] = flow

    else:
        password = unquote(
            parsed.username or ""
        )

        if not password:
            raise ValueError(
                "Missing Trojan password"
            )

        outbound = {
            "type": "trojan",
            "tag": "proxy",
            "server": host,
            "server_port": port,
            "password": password,
        }

    tls = _build_tls(params, host)

    if tls:
        outbound["tls"] = tls

    transport = _build_transport(params)

    if transport:
        outbound["transport"] = transport

    return outbound


def _find_free_port() -> int:
    # Let the OS choose an available local port.
    with socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    ) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_for_port(
    port: int,
    process: subprocess.Popen[bytes]
) -> bool:
    # Wait briefly for sing-box to start.
    deadline = (
        time.monotonic()
        + STARTUP_TIMEOUT
    )

    while time.monotonic() < deadline:
        if process.poll() is not None:
            return False

        try:
            with socket.create_connection(
                ("127.0.0.1", port),
                timeout=0.2
            ):
                return True

        except OSError:
            time.sleep(0.1)

    return False


def _check_http(
    session: requests.Session,
    port: int
) -> bool:
    proxy = f"http://127.0.0.1:{port}"

    try:
        response = session.get(
            PROBE_URL,
            proxies={
                "http": proxy,
                "https": proxy,
            },
            timeout=PROBE_TIMEOUT,
            allow_redirects=False,
        )

        return response.status_code == 204

    except requests.RequestException:
        return False


def _find_sing_box() -> str:
    # Find sing-box from environment or PATH.
    configured = os.getenv("SING_BOX_BIN")

    if configured:
        return configured

    binary = shutil.which("sing-box")

    if binary:
        return binary

    if os.name == "nt":
        binary = shutil.which("sing-box.exe")

        if binary:
            return binary

    raise RuntimeError(
        "sing-box was not found. "
        "Install sing-box or set SING_BOX_BIN."
    )


def check_config(
    uri: str,
    sing_box_bin: str
) -> bool:
    try:
        outbound = parse_config(uri)

    except (
        ValueError,
        KeyError,
        TypeError,
        json.JSONDecodeError
    ):
        return False

    local_port = _find_free_port()

    # Create a temporary sing-box config for this proxy.
    config: dict[str, Any] = {
        "log": {
            "level": "error"
        },
        "inbounds": [
            {
                "type": "mixed",
                "tag": "local",
                "listen": "127.0.0.1",
                "listen_port": local_port,
            }
        ],
        "outbounds": [
            outbound
        ],
    }

    with tempfile.TemporaryDirectory(
        prefix="v2ray-health-"
    ) as temp_dir:

        config_path = os.path.join(
            temp_dir,
            "config.json"
        )

        with open(
            config_path,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                config,
                file,
                ensure_ascii=False
            )

        # Start a separate sing-box process for this candidate.
        process = subprocess.Popen(
            [
                sing_box_bin,
                "run",
                "-c",
                config_path,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        try:
            # Check local core startup.
            if not _wait_for_port(
                local_port,
                process
            ):
                return False

            # Reuse one session for the retry.
            session = requests.Session()
            session.trust_env = False

            try:
                # First probe.
                if _check_http(
                    session,
                    local_port
                ):
                    return True

                # Retry only after a failure.
                time.sleep(RETRY_DELAY)

                return _check_http(
                    session,
                    local_port
                )

            finally:
                session.close()

        finally:
            # Always stop the temporary sing-box process.
            if process.poll() is None:
                process.terminate()

                try:
                    process.wait(timeout=2)

                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


def check_configs(
    configs: list[str]
) -> list[str]:
    sing_box_bin = _find_sing_box()

    working_configs: list[str] = []

    # Test several candidates in parallel.
    with ThreadPoolExecutor(
        max_workers=WORKERS
    ) as executor:

        futures = {
            executor.submit(
                check_config,
                config,
                sing_box_bin
            ): config
            for config in configs
        }

        for future in as_completed(futures):
            config = futures[future]

            try:
                if future.result():
                    working_configs.append(config)

            except Exception:
                continue

    return working_configs