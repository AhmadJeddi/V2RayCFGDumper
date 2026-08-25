import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlsplit
from datetime import datetime, timezone

from health_checker import check_configs

addresses = [

    # 1 - 10
    "https://telegram.me/s/filembad",
    "https://telegram.me/s/blackRay",
    "https://telegram.me/s/Config_magazine",
    "https://telegram.me/s/WedBazGap",
    "https://telegram.me/s/VPNnobody",
    "https://telegram.me/s/Ciurou",
    "https://telegram.me/s/NetMeli9",
    "https://telegram.me/s/ProxyMtpVPN",
    "https://telegram.me/s/NormanV2ray",
    "https://telegram.me/s/canfingV2rayNG",


    # 11 - 20
    "https://telegram.me/s/LoopLine_Ir",
    "https://telegram.me/s/CMLiussss",
    "https://telegram.me/s/Azadi_az_inja_migzare",
    "https://telegram.me/s/AzadNet",
    "https://telegram.me/s/Ln2Ray",
    "https://telegram.me/s/DeamNet",
    "https://telegram.me/s/FREE2CONFIG",
    "https://telegram.me/s/gheychiamoozesh",
    "https://telegram.me/s/KevinZakarian",
    "https://telegram.me/s/ProxyDaemi",


    # 21 - 30
    "https://telegram.me/s/IranRamona",
    "https://telegram.me/s/v2ray_configs_pool",
    "https://telegram.me/s/FreeV2rays",
    "https://telegram.me/s/V2rayCollector",
    "https://telegram.me/s/v2rayNG_Matsuri",
    "https://telegram.me/s/v2ray_configs",
    "https://telegram.me/s/V2rayN",
    "https://telegram.me/s/V2rayTz",
    "https://telegram.me/s/ShadowSocks",
    "https://telegram.me/s/FreeProxyIR",


    # 31 - 40
    "https://telegram.me/s/ProxyMTProto",
    "https://telegram.me/s/v2rayfree",
    "https://telegram.me/s/vmess_vless_configs",
    "https://telegram.me/s/FreeV2ray",
    "https://telegram.me/s/V2rayConfig",
    "https://telegram.me/s/v2ray_vmess",
    "https://telegram.me/s/free4allVPN",
    "https://telegram.me/s/v2ray_free_configs",
    "https://telegram.me/s/v2rayngfree",
    "https://telegram.me/s/ConfigsHub",


    # 41 - 50
    "https://telegram.me/s/V2rayShare",
    "https://telegram.me/s/free_vpn_configs",
    "https://telegram.me/s/Shadowrocket",
    "https://telegram.me/s/SSRfree",
    "https://telegram.me/s/V2raySub",
    "https://telegram.me/s/V2raySubscribe",
    "https://telegram.me/s/FreeNet",
    "https://telegram.me/s/FreeProxy",
    "https://telegram.me/s/VlessConfig",
    "https://telegram.me/s/ProxyConfig"

]


# Supported proxy protocols.
SUPPORTED_PROTOCOLS = (
    "vless://",
    "vmess://",
    "ss://",
    "trojan://"
)

PROXY_PATTERN = re.compile(
    r"(?:vless|vmess|ss|trojan)://[^\s]+?"
    r"(?=(?:vless|vmess|ss|trojan)://|\s|$)",
    re.IGNORECASE
)


def is_supported_protocol(config):
    return config.lower().startswith(SUPPORTED_PROTOCOLS)


def is_valid_config(config):
    if not config:
        return False

    config = config.strip()

    if not is_supported_protocol(config):
        return False

    try:
        parsed = urlsplit(config)

        # Validate the URI scheme.
        if parsed.scheme.lower() not in {
            "vless",
            "vmess",
            "ss",
            "trojan"
        }:
            return False

        # Reject empty URIs such as vless://.
        remainder = config.split("://", 1)[1]
        return bool(remainder.strip())

    except ValueError:
        return False


def remove_duplicates(input_list):
    # Remove duplicates while preserving order.
    seen = set()
    result = []

    for item in input_list:
        if item not in seen:
            seen.add(item)
            result.append(item)

    return result


def extract_configs(text):
    # Extract all supported proxy URIs.
    return [
        match.group(0).strip()
        for match in PROXY_PATTERN.finditer(text)
    ]


# Fetch Telegram channel pages.
html_pages = []

for url in addresses:
    try:
        response = requests.get(url, timeout=12)
        response.raise_for_status()
        html_pages.append(response.text)

    except requests.RequestException as error:
        print(f"[WARNING] Failed to fetch {url}: {error}")


# Extract raw proxy URIs from code blocks.
raw_codes = []
raw_blocks = []

for page in html_pages:
    soup = BeautifulSoup(page, "html.parser")
    code_tags = soup.find_all("code")

    for code_tag in code_tags:
        code_content = code_tag.text.strip()

        if not code_content:
            continue

        raw_blocks.append(code_content)

        extracted = extract_configs(code_content)

        if extracted:
            raw_codes.extend(extracted)


# Apply quality filtering.
codes = []

for code in raw_codes:
    if (
        is_supported_protocol(code)
        and is_valid_config(code)
    ):
        codes.append(code)

candidate_count_before_duplicates = len(codes)

# Remove exact duplicates.
codes = remove_duplicates(codes)

duplicates_removed = (
    candidate_count_before_duplicates - len(codes)
)


# Get current date and time.
current_date_time = datetime.now(
    timezone.utc
)

current_month = current_date_time.strftime("%b")
current_day = current_date_time.strftime("%d")
updated_hour = current_date_time.strftime("%H")
updated_minute = current_date_time.strftime("%M")

final_string = (
    f"{current_month}-{current_day} | "
    f"{updated_hour}:{updated_minute}"
)

final_others_string = f"{current_month}-{current_day}"


# Normalize configs and remove fragments.
processed_codes = []

for code in codes:
    processed_part = code.split("#")[0].strip()

    if is_valid_config(processed_part):
        processed_codes.append(processed_part)


processed_codes = remove_duplicates(processed_codes)


# Final validation.
new_processed_codes = []

for code in processed_codes:
    if is_valid_config(code):
        new_processed_codes.append(code)


final_count_before_duplicates = len(new_processed_codes)

new_processed_codes = remove_duplicates(new_processed_codes)

# Check candidate configs.
working_configs = check_configs(new_processed_codes)

final_duplicates_removed = (
    final_count_before_duplicates
    - len(new_processed_codes)
)


# Write the final subscription file.
with open("sub.txt", "w", encoding="utf-8") as file:
    for index, code in enumerate(working_configs):
        if index == 0:
            config_string = (
                "#🌐 Updated on "
                + final_string
                + " | Working configs every 15 minutes"
            )
        else:
            config_string = (
                "#🌐 Server "
                + str(index)
                + " | "
                + final_others_string
                + " | MTSRVRS"
            )

        config_final = code + config_string
        file.write(config_final + "\n")


# Print collection statistics.
print(f"[INFO] Channels configured: {len(addresses)}")
print(f"[INFO] Channel pages fetched: {len(html_pages)}")
print(f"[INFO] Raw code blocks: {len(raw_blocks)}")
print(f"[INFO] Config URIs extracted: {len(raw_codes)}")
print(f"[INFO] Valid candidates: {candidate_count_before_duplicates}")
print(f"[INFO] Unique candidates: {len(codes)}")
print(f"[INFO] Duplicates removed: {duplicates_removed}")
print(f"[INFO] Final configs: {len(new_processed_codes)}")
print(f"[INFO] Working configs: {len(working_configs)}")