# ShadowHalberd

![头图](./assets/social-preview.jpg)

[English](./README_en.md) | [文档](./docs.md)

ShadowHalberd（影戟）是一款现代化 Webshell 管理器，提供简洁直观的 Web 界面与丰富的协议支持，适用于渗透测试、红队评估与安全研究场景。

项目基于 B/S 架构构建，可直接部署在服务器或本地运行，通过浏览器访问即可管理目标会话，避免在本地机器上留存敏感工具痕迹。

## 核心特性

- **多协议 Webshell 支持**
  - 幽魂默认：PHP / JSP / ASPX
  - 冰蝎（Behinder）：PHP AES/XOR、JSP AES、JSPX AES、ASP XOR、ASPX AES
  - 哥斯拉（Godzilla）：PHP XOR、ASP XOR、ASPX AES、JSP AES、JSPX AES
  - Linux 命令 / 反弹 Shell

- **现代化 UI**
  - 新增「现代深色」主题：蓝紫渐变、毛玻璃卡片、动态背景
  - 多套预设主题：专业面板、命令终端、极光玻璃、赛博霓虹、纸面文书
  - 可自定义字体大小与背景图片

- **实用功能**
  - 存活探测、基本信息、命令执行、文件管理、文件上传下载
  - PHP 代码执行与 phpinfo 下载
  - TCP 正向代理与伪正向代理
  - 对接蚁剑（AntSword），共享插件生态
  - 反弹 Shell 监听与持久化连接

- **安全与隐私**
  - RSA2048 + AES256-CBC 强加密通信
  - 随机 User-Agent、HTTP 垃圾数据填充
  - 自定义 encoder / decoder，支持部分蚁剑 encoder 导入

## 快速开始

### 使用 pip 安装（推荐）

```shell
pip install ether-ghost
ether_ghost --host 127.0.0.1 --port 8022
```

### 源码运行

```shell
cd ShadowHalberd
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m ether_ghost --host 127.0.0.1 --port 8022
```

启动后打开浏览器访问 `http://127.0.0.1:8022` 即可使用。

### 常用参数

```text
--host          监听地址，默认 127.0.0.1
--port          监听端口，默认 8022
--no-browser    启动时不自动打开浏览器
--auth USER:PWD 为 API 开启基础认证
```

## 构建前端

前端源码位于 `frontend/`，使用 Vite 构建。修改前端后必须重新构建：

```shell
cd frontend
npm install
npm run build
cd ..
rm -rf ether_ghost/public
mv frontend/dist ether_ghost/public
```

或使用项目根目录的 `build.sh`：

```shell
bash build.sh
```

> 注意：构建产物 `ether_ghost/public/` 必须和前端源码修改一起提交，不要单独提交构建产物。

## 打包为独立可执行文件

### Linux

```shell
bash build.sh
pip install pyinstaller
python pyinstaller_package.bat  # 请根据实际环境修改脚本中的路径
```

### Windows

参考 [`pyinstaller_package.bat`](./pyinstaller_package.bat)，将虚拟环境路径替换为本地 `site-packages` 目录后执行。

## 开发说明

- 后端：Python + FastAPI + SQLAlchemy + Uvicorn
- 前端：Vue 3 + Vite
- 依赖管理：Poetry / pip
- 数据目录：
  - Linux: `~/.local/share/ShadowHalberd`
  - Windows: `~/AppData/Roaming/ShadowHalberd`
  - macOS: `~/Library/Application Support/ShadowHalberd`

## 支持的 Webshell 操作

| 操作 | PHP | JSP/JSPX | ASP | ASPX | Linux |
|---|---|---|---|---|---|
| 存活探测 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 基本信息 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 命令执行 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 文件列表 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 文件读写 | ✓ | ✓ | ✓ | ✓ | ✓ |
| PHP 代码执行 | ✓ | - | - | - | - |
| TCP 正向代理 | ✓ | - | - | - | - |

## 项目结构

```text
ShadowHalberd/
├── ether_ghost/          # 后端源码
│   ├── api/              # FastAPI 路由
│   ├── core/             # 核心协议与生成器
│   ├── sessions/         # 各类 webshell 会话实现
│   ├── wsm_payloads/     # 冰蝎 / 哥斯拉 payload
│   └── public/           # 前端构建产物
├── frontend/             # 前端源码
├── test_environment/     # 本地测试 webshell
├── tests/                # 测试用例
├── build.sh              # 前端构建脚本
└── pyproject.toml        # Poetry 配置
```

## 安全提示

本项目仅用于授权的安全测试、漏洞研究与教学目的。使用者应自行承担因未授权使用而造成的法律责任。

## 致谢

项目最初灵感来自蚁剑、冰蝎、哥斯拉等优秀工具，并参考了 kimi/wsm 等实现。
