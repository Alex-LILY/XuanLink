# ShadowHalberd

![Header Image](./assets/social-preview.jpg)

[中文](./README.md) | [Documentation](./docs.md)

ShadowHalberd is a modern webshell manager with a clean web UI and broad protocol support, designed for authorized penetration testing, red teaming, and security research.

It runs as a B/S application: deploy it on a server or run it locally, then manage target sessions entirely through your browser, avoiding the need to keep sensitive tooling on your local machine.

## Highlights

- **Multi-Protocol Webshell Support**
  - ShadowHalberd native: PHP / JSP / ASPX
  - Behinder: PHP AES/XOR, JSP AES, JSPX AES, ASP XOR, ASPX AES
  - Godzilla: PHP XOR, ASP XOR, ASPX AES, JSP AES, JSPX AES
  - Linux command / reverse shell

- **Modern UI**
  - New "Modern Dark" theme with blue-purple gradients, glassmorphism cards, and animated background
  - Additional built-in themes: Pro Panel, Terminal, Aurora Glass, Cyber Neon, Parchment
  - Customizable font size and background image

- **Practical Features**
  - Alive probing, basic info, command execution, file management, upload/download
  - PHP code execution and phpinfo download
  - TCP forward proxy and pseudo-forward proxy
  - AntSword integration to leverage its plugin ecosystem
  - Reverse shell listener with persistent connections

- **Security & Privacy**
  - RSA2048 + AES256-CBC encrypted communication
  - Random User-Agent and HTTP junk-data padding
  - Custom encoders/decoders with partial AntSword encoder support

## Quick Start

### Install from pip

```shell
pip install ether-ghost
ether_ghost --host 127.0.0.1 --port 8022
```

### Run from source

```shell
cd ShadowHalberd
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m ether_ghost --host 127.0.0.1 --port 8022
```

Open `http://127.0.0.1:8022` in your browser.

### Common options

```text
--host          Bind address, default 127.0.0.1
--port          Bind port, default 8022
--no-browser    Do not open the browser automatically
--auth USER:PWD Enable basic auth for the API
```

## Building the Frontend

The frontend lives in `frontend/` and is built with Vite. After any frontend change you must rebuild:

```shell
cd frontend
npm install
npm run build
cd ..
rm -rf ether_ghost/public
mv frontend/dist ether_ghost/public
```

Or use the root script:

```shell
bash build.sh
```

> Note: The build output in `ether_ghost/public/` should be committed together with the source changes, never on its own.

## Packaging as a Standalone Executable

### Linux

```shell
bash build.sh
pip install pyinstaller
python pyinstaller_package.bat  # Adjust paths inside the script first
```

### Windows

See [`pyinstaller_package.bat`](./pyinstaller_package.bat), replace the virtual-environment path with your local `site-packages` directory, then run it.

## Development Notes

- Backend: Python + FastAPI + SQLAlchemy + Uvicorn
- Frontend: Vue 3 + Vite
- Dependency management: Poetry / pip
- Data directories:
  - Linux: `~/.local/share/ShadowHalberd`
  - Windows: `~/AppData/Roaming/ShadowHalberd`
  - macOS: `~/Library/Application Support/ShadowHalberd`

## Supported Operations

| Operation     | PHP | JSP/JSPX | ASP | ASPX | Linux |
|---------------|-----|----------|-----|------|-------|
| Alive probe   | ✓   | ✓        | ✓   | ✓    | ✓     |
| Basic info    | ✓   | ✓        | ✓   | ✓    | ✓     |
| Command exec  | ✓   | ✓        | ✓   | ✓    | ✓     |
| File listing  | ✓   | ✓        | ✓   | ✓    | ✓     |
| File R/W      | ✓   | ✓        | ✓   | ✓    | ✓     |
| PHP eval      | ✓   | -        | -   | -    | -     |
| TCP forward   | ✓   | -        | -   | -    | -     |

## Project Structure

```text
ShadowHalberd/
├── ether_ghost/          # Backend source
│   ├── api/              # FastAPI routes
│   ├── core/             # Core protocols and generators
│   ├── sessions/         # Webshell session implementations
│   ├── wsm_payloads/     # Behinder / Godzilla payloads
│   └── public/           # Frontend build output
├── frontend/             # Frontend source
├── test_environment/     # Local test webshells
├── tests/                # Test cases
├── build.sh              # Frontend build script
└── pyproject.toml        # Poetry configuration
```

## Disclaimer

This project is intended only for authorized security testing, vulnerability research, and educational purposes. Users are solely responsible for any legal consequences arising from unauthorized use.

## Acknowledgements

Inspired by excellent tools such as AntSword, Behinder, and Godzilla, with reference to implementations like kimi/wsm.
