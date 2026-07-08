# XuanLink

<p align="center">
  <img src="./assets/登录界面.png" alt="XuanLink Login Interface" width="80%">
</p>

<p align="center">
  <a href="./README.md">中文</a> |
  <a href="./docs.md">Documentation</a> |
  <a href="https://github.com/Alex-LILY/XuanLink">GitHub</a>
</p>

**XuanLink** is a modern webshell manager designed for authorized penetration testing, red teaming, and security research. Built with a B/S architecture, it can be deployed on a server or run locally, allowing you to manage target sessions entirely through a browser without leaving sensitive tooling on your local machine.

---

## Table of Contents

- [Features](#features)
- [Screenshots](#screenshots)
- [Quick Start](#quick-start)
- [User Guide](#user-guide)
- [Customization](#customization)
- [Development](#development)
- [Supported Operations](#supported-operations)
- [FAQ](#faq)
- [Disclaimer](#disclaimer)
- [License](#license)

---

## Features

### Multi-Protocol Webshell Support

| Protocol | Supported Types |
|----------|-----------------|
| **XuanLink Native** | PHP / JSP / ASPX |
| **Behinder** | PHP AES/XOR, JSP AES, JSPX AES, ASP XOR, ASPEX AES |
| **Godzilla** | PHP XOR, ASP XOR, ASPX AES, JSP AES, JSPX AES |
| **Linux Command** | Direct command execution |
| **Reverse Shell** | TCP listener with persistent connections |

### Modern UI

- Multiple themes: Pro Panel, Terminal, Glass, Cyber, Paper, Modern
- Customizable font size and background image
- Session list with tag-based grouping, sorting, search, and batch operations
- File management with modification time column and breadcrumb navigation

### Practical Features

- Alive probing and basic information collection
- Command execution and file management (browse, upload, download, edit)
- PHP code execution and `phpinfo` download
- TCP / HTTP / SOCKS5 forward proxy and proxy pool management
- Reverse shell listener with persistent connections
- Batch session import and batch tag assignment
- Mandatory password change on first login

### Security & Privacy

- RSA2048 + AES256 encrypted communication
- Random User-Agent and HTTP junk-data padding
- Custom encoders/decoders with partial AntSword plugin support
- Custom modules and AntSword encoders disabled by default

---

## Screenshots

<p align="center">
  <b>Main Interface</b><br>
  <img src="./assets/主界面.png" alt="Main Interface" width="90%">
</p>

<p align="center">
  <b>File Management</b><br>
  <img src="./assets/文件管理.png" alt="File Management" width="90%">
</p>

---

## Quick Start

### Install from pip

```shell
pip install ether-ghost
ether_ghost --host 127.0.0.1 --port 8022
```

### Run from source

```shell
git clone https://github.com/Alex-LILY/XuanLink.git
cd XuanLink
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m ether_ghost --host 127.0.0.1 --port 8022
```

### Run with Poetry

```shell
poetry install
poetry run ether_ghost
```

Then open `http://127.0.0.1:8022` in your browser.

> **Default credentials**: `admin` / `admin123`  
> You will be required to change the default password on first login.

### Common Options

| Option | Default | Description |
|--------|---------|-------------|
| `--host` | `0.0.0.0` | Bind address |
| `--port` | `8022` | Bind port |
| `--no-browser` | - | Do not open browser automatically |

---

## User Guide

### Creating a Session

1. Open the web UI and click "Add"
2. Select the webshell type (XuanLink / Behinder / Godzilla / Linux CMD)
3. Fill in the URL, password, and connection parameters, then save
4. Right-click the session and select "Probe cache" to test the connection

### File Management

Select the "Files" tab after entering a session to browse directories, upload/download files, edit text files online, and view modification times.

### Command Execution

Select the "Terminal" tab to execute system commands on the target host with an interactive command line and history support.

### Forward Proxy

- **Vessel Forward Proxy**: A persistent proxy implemented via a PHP memory shell
- **Pseudo-Forward Proxy**: Forwards traffic via the gopher protocol in an SSRF-like manner

### Reverse Shell

Create a TCP listener in "Connectors". Once the target connects, you get a persistent shell session.

---

## Customization

### Custom Encoder / Decoder

Find the configuration folder printed at startup, then create Python files under `modules/php_encoders` or `modules/php_decoders`. Restart to apply changes.

> Note: Custom modules are disabled by default. Set `SHADOWHALBERD_ENABLE_CUSTOM_MODULES=1` before starting.

### Import AntSword Plugins

Place `.js` plugin files into the `AntSwordEncoder` or `AntSwordDecoder` directory under the configuration folder, then set `SHADOWHALBERD_ENABLE_ANTSWORD_ENCODERS=1` and restart.

### Custom Wallpaper

Rename your wallpaper image to `bg.jpg`, `bg.png`, or `bg.webp`, place it in the configuration folder, then set the theme to "Glass" in settings.

---

## Development

### Building the Frontend

```shell
cd frontend
npm install
npm run build
cd ..
rm -rf ether_ghost/public
mv frontend/dist ether_ghost/public
```

Or simply run:

```shell
bash build.sh
```

### Project Structure

```text
XuanLink/
├── ether_ghost/          # Backend source (FastAPI)
│   ├── api/              # API routes
│   ├── core/             # Core protocols
│   ├── sessions/         # Webshell session implementations
│   ├── session_connectors/  # Reverse shell connectors
│   ├── wsm_payloads/     # Behinder / Godzilla payloads
│   └── public/           # Frontend build output
├── frontend/             # Frontend source (Vue 3 + Vite)
├── test_environment/     # Local test webshells
├── tests/                # Test cases
├── assets/               # Screenshots and assets
├── build.sh              # Build script
├── pyproject.toml        # Poetry configuration
├── requirements.txt      # pip dependencies
└── README.md             # Chinese README
```

---

## Supported Operations

| Operation | PHP | JSP/JSPX | ASP | ASPX | Linux |
|-----------|-----|----------|-----|------|-------|
| Alive probe | ✓ | ✓ | ✓ | ✓ | ✓ |
| Basic info | ✓ | ✓ | ✓ | ✓ | ✓ |
| Command exec | ✓ | ✓ | ✓ | ✓ | ✓ |
| File listing | ✓ | ✓ | ✓ | ✓ | ✓ |
| File R/W | ✓ | ✓ | ✓ | ✓ | ✓ |
| PHP eval | ✓ | - | - | - | - |
| TCP forward | ✓ | - | - | - | - |
| HTTP forward | ✓ | - | - | - | - |
| SOCKS5 forward | ✓ | - | - | - | - |

---

## FAQ

### Q: Why can't encoders and decoders be added from the web UI?

Encoders and decoders are loaded as code when the server starts. To prevent an attacker who gains access to your XuanLink instance from controlling the server by injecting malicious code, they must be configured via files rather than the web UI.

### Q: What is Vessel?

Vessel is a custom PHP memory shell developed for XuanLink. It supports both file-based and Session-based communication and is used to implement a stable forward proxy.

### Q: How is the XuanLink webshell different from traditional one-liner webshells?

Traditional one-liner webshells have obvious features and are easily detected. XuanLink webshell encrypts and obfuscates traffic, uses XOR encoding, and uses special 8-byte markers to locate the payload, allowing it to be embedded in arbitrary data and significantly reducing the chance of detection.

---

## Disclaimer

This project is intended only for **authorized security testing, vulnerability research, and educational purposes**. Users are solely responsible for any legal consequences arising from unauthorized use. Do not use this tool on systems without explicit authorization.

---

## License

This project is open-sourced under the [MIT License](./LICENSE).
