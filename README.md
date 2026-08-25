# V2RayCFGDumper 🚀

An automated V2Ray configuration collector, validator, and health checker built with Python and GitHub Actions.

This project collects publicly available VLESS, VMess, Trojan, and Shadowsocks configurations, validates them, removes duplicates, checks their availability, and generates a clean subscription file automatically.

The generated subscription is updated periodically through GitHub Actions.

---

# ✨ Features

- 🔎 Collect configurations from multiple Telegram sources
- 🧩 Support for:
  - VLESS
  - VMess
  - Trojan
  - Shadowsocks
- ✅ Configuration validation
- ♻️ Duplicate removal
- 🩺 Health checking with `sing-box`
- 🌐 HTTP connectivity verification
- 🔁 Stability check with retry mechanism
- ⚡ Parallel configuration testing
- 🤖 Automated subscription updates

---

# 🏗️ How It Works

The project uses a two-stage pipeline:

## 1. Configuration Collection

```text
Telegram Sources
        ↓
Extract Config URIs
        ↓
Validate Protocols
        ↓
Remove Duplicates
        ↓
Candidate Configs
```

## 2. Health Check

```text
Candidate Configs
        ↓
sing-box Test
        ↓
Connection Check
        ↓
HTTP Probe
        ↓
Stability Verification
        ↓
Working Configs
        ↓
sub.txt
```

Only configurations that successfully pass the health check are included in the final subscription.

---

## 🚀 Usage

Add the subscription URL to your V2Ray client:

```text
https://raw.githubusercontent.com/AhmadJeddi/V2RayCFGDumper/main/sub.txt
```

Or scan the QR Code below:

![Subscription QR Code](images/subscription-qrcode.png)

Compatible clients:

- V2RayNG (Android)
- NekoBox (Android / PC)
- Nekoray
- V2RayN (Windows)

Update the subscription in your client periodically to receive the latest available configurations.

---

# 📦 Supported Protocols

| Protocol | Status |
|----------|--------|
| VLESS | ✅ |
| VMess | ✅ |
| Trojan | ✅ |
| Shadowsocks | ✅ |

---

# 📁 Project Structure

```text
V2RayCFGDumper
│
├── config.py              # Configuration collector and generator
├── health_checker.py      # Proxy availability checker
├── requirements.txt       # Project dependencies
├── sub.txt                # Generated subscription file
│
├── .github
│   └── workflows
│       └── run-config.yml # Automated workflow
│
├── .gitignore
├── .gitattributes
└── README.md
```

---

# 🔄 Automation

The project uses GitHub Actions to automatically:

- Collect new configurations
- Validate and test them
- Generate updated `sub.txt`
- Commit changes when needed

The workflow runs periodically every 15 minutes.

---

# 📊 Example Statistics

Example execution:

```text
[INFO] Channels configured: 31
[INFO] Channel pages fetched: 31
[INFO] Raw code blocks: 237
[INFO] Config URIs extracted: 563
[INFO] Valid candidates: 563
[INFO] Unique candidates: 509
[INFO] Duplicates removed: 54
[INFO] Final configs: 493
[INFO] Working configs: 35
```

---

# 📌 Notes

- Public proxy configurations are unstable and may expire at any time.
- The number of working configurations changes depending on availability.
- A configuration working from GitHub Actions infrastructure may not work on every network or country.
- This project only collects and validates publicly available configurations and does not create or provide proxy servers.

---

## 📜 License

This project is based on the original work:

**Milad Tahanian - V2RayCFGDumper**

Original repository:

https://github.com/miladtahanian/V2RayCFGDumper

This version is a modified and extended implementation with:

- Automated configuration validation pipeline
- Health checking system using `sing-box`
- GitHub Actions automation
- Improved configuration filtering
- Automatic subscription generation
- Parallel health checking workflow

---

# 👤 Author

**Ahmad JeddiZahed**

GitHub:

https://github.com/AhmadJeddi

Project:

https://github.com/AhmadJeddi/V2RayCFGDumper
