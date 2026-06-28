# ShadowHalberd（影戟）

<p align="center">
  <img src="./assets/preview-homepage.png" alt="ShadowHalberd 主界面" width="80%">
</p>

<p align="center">
  <a href="./README_en.md">English</a> |
  <a href="./docs.md">文档</a> |
  <a href="https://github.com/Alex-LILY/XuanLink">GitHub</a>
</p>

**ShadowHalberd（影戟）** 是一款现代化 Webshell 管理器，提供简洁直观的 Web 界面与丰富的协议支持，适用于授权渗透测试、红队评估与安全研究场景。

项目基于 B/S 架构构建，可直接部署在服务器或本地运行，通过浏览器即可管理目标会话，避免在本地机器上留存敏感工具痕迹。

---

## 目录

- [功能特性](#功能特性)
- [界面预览](#界面预览)
- [快速开始](#快速开始)
  - [pip 安装（推荐）](#pip-安装推荐)
  - [源码运行](#源码运行)
  - [Poetry 运行](#poetry-运行)
  - [常用参数](#常用参数)
- [使用指南](#使用指南)
  - [创建会话](#创建会话)
  - [文件管理](#文件管理)
  - [命令执行](#命令执行)
  - [正向代理](#正向代理)
  - [反弹 Shell](#反弹-shell)
- [自定义扩展](#自定义扩展)
  - [自定义 Encoder](#自定义-encoder)
  - [自定义 Decoder](#自定义-decoder)
  - [导入蚁剑插件](#导入蚁剑插件)
  - [自定义壁纸](#自定义壁纸)
- [开发说明](#开发说明)
  - [构建前端](#构建前端)
  - [打包可执行文件](#打包可执行文件)
  - [项目结构](#项目结构)
- [支持的操作矩阵](#支持的操作矩阵)
- [常见问题](#常见问题)
- [安全提示](#安全提示)
- [许可证](#许可证)
- [致谢](#致谢)

---

## 功能特性

### 多协议 Webshell 支持

| 协议 | 支持类型 |
|------|---------|
| **影戟默认** | PHP / JSP / ASPX |
| **冰蝎（Behinder）** | PHP AES/XOR、JSP AES、JSPX AES、ASP XOR、ASPX AES |
| **哥斯拉（Godzilla）** | PHP XOR、ASP XOR、ASPX AES、JSP AES、JSPX AES |
| **Linux 命令** | 直接命令执行 |
| **反弹 Shell** | TCP 反弹 Shell 监听与持久化连接 |

### 现代化 UI

- **全新现代深色主题**：蓝紫渐变、毛玻璃卡片、动态背景
- **多套预设主题**：专业面板、命令终端、极光玻璃、赛博霓虹、纸面文书
- **自定义字体大小与背景图片**，满足个性化需求

### 实用功能

- 存活探测、基本信息采集、命令执行
- 文件管理：目录浏览、文件读写、上传、下载
- PHP 代码执行与 `phpinfo` 下载
- TCP 正向代理与伪正向代理（gopher/SSRF）
- 对接蚁剑（AntSword），共享部分插件生态
- 反弹 Shell 监听与持久化连接

### 安全与隐私

- **RSA2048 + AES256-CBC** 强加密通信
- 随机 User-Agent、HTTP 垃圾数据填充
- 自定义 encoder / decoder，支持部分蚁剑 encoder 导入
- 幽魂 Webshell 采用加密 + 混淆双重防护，将流量隐藏在随机数据中

---

## 界面预览

<p align="center">
  <b>主界面</b><br>
  <img src="./assets/preview-homepage.png" alt="主界面" width="90%">
</p>

<p align="center">
  <b>文件管理</b><br>
  <img src="./assets/preview-files.png" alt="文件管理" width="90%">
</p>

<p align="center">
  <b>命令终端</b><br>
  <img src="./assets/preview-terminal.png" alt="命令终端" width="90%">
</p>

---

## 快速开始

### pip 安装（推荐）

```shell
pip install ether-ghost
ether_ghost --host 127.0.0.1 --port 8022
```

### 源码运行

```shell
git clone https://github.com/Alex-LILY/XuanLink.git
cd XuanLink
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m ether_ghost --host 127.0.0.1 --port 8022
```

### Poetry 运行

项目使用 [Poetry](https://python-poetry.org/) 管理依赖：

```shell
poetry install
poetry run ether_ghost
```

启动后打开浏览器访问 `http://127.0.0.1:8022` 即可使用。

### 常用参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--host` | `127.0.0.1` | 监听地址 |
| `--port` | `8022` | 监听端口 |
| `--no-browser` | `false` | 启动时不自动打开浏览器 |
| `--auth USER:PWD` | - | 为 API 开启基础认证 |

---

## 使用指南

### 创建会话

1. 打开 Web 界面，点击「新建会话」
2. 选择 Webshell 类型（影戟 / 冰蝎 / 哥斯拉 / Linux CMD）
3. 填写 URL、密码、连接参数等
4. 保存后点击「连接」进行测试

### 文件管理

进入会话后选择「文件」标签，即可：

- 浏览目标主机目录结构
- 上传、下载、删除、重命名文件
- 在线编辑文本文件

### 命令执行

进入「终端」标签，即可在目标主机上执行系统命令，支持：

- 交互式命令行
- 命令历史记录
- 实时输出显示

### 正向代理

影戟支持两种正向代理：

- **Vessel 正向代理**：通过 PHP 内存马实现的持久化代理，支持文件和 Session 两种通信方式
- **伪正向代理**：通过 gopher 协议以 SSRF 方式转发流量，适合 HTTP 类协议

### 反弹 Shell

在「连接器」中创建 TCP 监听，目标主机连接后即可获得持久化 Shell 会话。

---

## 自定义扩展

### 自定义 Encoder

根据启动时打印的配置路径，打开影戟配置文件夹，找到 `modules/php_encoders` 目录，新建 Python 文件：

```python
import base64

def encode(code: str):
    return f"eval(base64_decode({base64.b64encode(code.encode()).decode()!r}));"
```

重启影戟后即可在 Webshell 编辑页面看到该 encoder。

### 自定义 Decoder

在 `modules/php_decoders` 目录下新建 Python 文件：

```python
import base64

phpcode = """
function decoder_echo_raw($s) {
    echo base64_encode($s);
}
"""

def decode(s: str) -> str:
    return base64.b64decode(s).decode()
```

重启后生效。

### 导入蚁剑插件

在配置文件夹中找到 `AntSwordEncoder` 或 `AntSwordDecoder` 目录，放入对应的 `.js` 文件并重启。

例如 `AntSwordEncoder/example-base64.js`：

```js
module.exports = (pwd, data, ext={}) => {
    let randomID = `_0x${Math.random().toString(16).substr(2)}`;
    data[randomID] = Buffer.from(data['_']).toString('base64');
    data[pwd] = `eval(base64_decode($_POST[${randomID}]));`;
    delete data['_'];
    return data;
}
```

> 注意：影戟不支持和蚁剑内部设计高度相关的某些环境变量，部分插件可能需要修改后使用。

### 自定义壁纸

将壁纸图片重命名为 `bg.jpg`、`bg.png` 或 `bg.webp`，放入影戟配置文件夹，然后在设置页面将主题改为「玻璃」即可生效。

---

## 开发说明

### 构建前端

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

### 打包可执行文件

#### Linux

```shell
bash build.sh
pip install pyinstaller
python pyinstaller_package.bat  # 请根据实际环境修改脚本中的路径
```

#### Windows

参考 [`pyinstaller_package.bat`](./pyinstaller_package.bat)，将虚拟环境路径替换为本地 `site-packages` 目录后执行。

### 项目结构

```text
ShadowHalberd/
├── ether_ghost/          # 后端源码
│   ├── api/              # FastAPI 路由
│   ├── core/             # 核心协议与生成器
│   ├── sessions/         # 各类 webshell 会话实现
│   ├── session_connectors/  # 反弹 Shell 等持久连接器
│   ├── wsm_payloads/     # 冰蝎 / 哥斯拉 payload
│   └── public/           # 前端构建产物
├── frontend/             # 前端源码（Vue 3 + Vite）
├── test_environment/     # 本地测试 webshell
├── tests/                # 测试用例
├── assets/               # 项目预览图与资源
├── build.sh              # 前端构建脚本
├── pyproject.toml        # Poetry 配置
├── requirements.txt      # pip 依赖
└── README.md             # 本文件
```

---

## 支持的操作矩阵

| 操作 | PHP | JSP/JSPX | ASP | ASPX | Linux |
|------|-----|----------|-----|------|-------|
| 存活探测 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 基本信息 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 命令执行 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 文件列表 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 文件读写 | ✓ | ✓ | ✓ | ✓ | ✓ |
| PHP 代码执行 | ✓ | - | - | - | - |
| TCP 正向代理 | ✓ | - | - | - | - |

---

## 常见问题

### Q: 为什么不支持在网页端添加 encoder 和 decoder？

Encoder 和 Decoder 会在服务端启动时作为代码被加载。如果攻击者登录了你的影戟实例，可以通过添加 Encoder 的方式控制服务器。因此为了防止 RCE 漏洞，影戟不支持在网页端添加 encoder 和 decoder。

### Q: Vessel 是什么？为什么正向代理有 Vessel 和伪正向两种？

Vessel 是影戟自研的 PHP 持久化内存马，可以通过文件和 Session 两种方式通信。伪正向代理则是通过 gopher 协议以类似 SSRF 的方式发送流量，基本上只支持 HTTP 类协议。

### Q: 影戟 Webshell 与传统一句话木马有什么区别？

传统一句话木马特征明显、易被查杀。影戟 Webshell 同时加密和混淆流量，使用异或编码和特殊的 8 字节标记定位 payload，可以将流量拼接在图片等任意数据中，显著降低被检测的概率。

---

## 安全提示

本项目仅用于**授权的安全测试、漏洞研究与教学目的**。使用者应自行承担因未授权使用而造成的法律责任。请勿在未经授权的系统上使用本工具。

---

## 许可证

本项目基于 [MIT License](./LICENSE) 开源。

---

## 致谢

项目最初灵感来自蚁剑、冰蝎、哥斯拉等优秀工具，并参考 [EtherGhost](https://github.com/Marven11/EtherGhost) 与 [wsm](https://github.com/xiecat/wsm) 等实现进行开发。
