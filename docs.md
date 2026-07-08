# XuanLink 技术文档

本文档面向希望深入了解玄联内部机制、进行二次开发或贡献代码的用户。

---

## 1. 玄联 Webshell 设计

### 1.1 背景

传统一句话 Webshell 特征明显，易被查杀。冰蝎、哥斯拉等工具通过 AES 等算法加密流量，解决了中间人直接读取 payload 的问题，但加密流量本身仍存在固定长度、固定后缀等可识别特征。

玄联 Webshell 的设计目标是将加密数据进一步隐藏在看似随机的数据中（如图片），降低被流量分析识别的概率。

### 1.2 流量结构

玄联 Webshell 在传输层同时做加密与混淆。一个数据包结构如下：

| 开头标记 | XOR 密钥 | 加密层数据 | 结尾标记 |
|---------|---------|-----------|---------|
| 8B      | 8B      | xB        | 8B      |

- 开头与结尾标记由 Webshell 密码派生，用于在任意流量中定位 payload。
- XOR 密钥用于混淆加密层数据。
- 加密层内部结构：

| action | RSA 加密 AES 密钥 / AES 加密 PHP 代码 |
|--------|--------------------------------------|
| 1B     | xB                                   |

### 1.3 连接流程

1. 控制端向被控端请求 AES 密钥，同时发送 RSA 公钥（可选）。
2. 被控端生成 AES 密钥，保存于 Session 中，用 RSA 公钥加密后返回。
3. 控制端用 RSA 私钥解密得到 AES 密钥。
4. 后续通信均使用 AES 加密 PHP 代码并执行。

### 1.4 优缺点

**优点**：

- 流量可隐藏于任意随机数据中，降低特征检测概率。
- 加密 + 混淆双重防护。

**缺点**：

- Webshell 体积较大。
- 首次发送 RSA 公钥时仍存在一定流量特征。
- 未做专门免杀处理。

---

## 2. 自定义扩展

### 2.1 自定义 Encoder

在玄联配置文件夹中找到 `modules/php_encoders`，新建 Python 文件，例如 `example.py`：

```python
import base64

def encode(code: str):
    return f"eval(base64_decode({base64.b64encode(code.encode()).decode()!r}));"
```

重启玄联后，该 Encoder 会出现在 Webshell 编辑页面。

**注意**：

- `encode` 返回值可以是 `str` 或 `bytes`，代表需要执行的 PHP 代码。
- 自定义模块默认关闭，需设置环境变量 `SHADOWHALBERD_ENABLE_CUSTOM_MODULES=1`。

### 2.2 自定义 Decoder

在 `modules/php_decoders` 下新建 Python 文件，例如 `example.py`：

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

### 2.3 导入蚁剑插件

将蚁剑的 `.js` 文件放入配置文件夹的 `AntSwordEncoder` 或 `AntSwordDecoder` 目录，设置环境变量 `SHADOWHALBERD_ENABLE_ANTSWORD_ENCODERS=1` 后重启。

示例 `AntSwordEncoder/example-base64.js`：

```js
module.exports = (pwd, data, ext={}) => {
    let randomID = `_0x${Math.random().toString(16).substr(2)}`;
    data[randomID] = Buffer.from(data['_']).toString('base64');
    data[pwd] = `eval(base64_decode($_POST[${randomID}]));`;
    delete data['_'];
    return data;
}
```

注意：玄联不支持和蚁剑内部设计高度相关的某些环境变量，部分插件可能需要修改后才能使用。

---

## 3. 正向代理

### 3.1 Vessel 正向代理

Vessel 是玄联自研的 PHP 持久化内存马，支持通过文件和 Session 两种方式通信：

- **文件通信**：控制端与被控端通过约定文件交换数据。
- **Session 通信**：利用 PHP Session 机制在内存中交换数据，隐蔽性更高。

Vessel 主要用于内网渗透场景，功能基本可用，但速度可能不及 Neo-reGeorg 等专门工具。

### 3.2 伪正向代理

伪正向代理通过 gopher 协议以 SSRF 方式发送流量。由于本质是 SSRF，因此主要适用于 HTTP 类协议。

---

## 4. 开发说明

### 4.1 项目结构

```text
ether_ghost/
├── api/              # FastAPI 路由
├── core/             # 核心协议、加密、生成器
├── sessions/         # 各类 Webshell 会话实现
├── session_connectors/  # 反弹 Shell 等连接器
├── utils/            # 数据库、常量、工具函数
├── wsm_payloads/     # 冰蝎 / 哥斯拉 payload
└── public/           # 前端构建产物

frontend/
├── src/              # Vue 3 源码
│   ├── components/   # 组件
│   ├── assets/       # 样式与工具
│   └── i18n/         # 国际化
└── vite.config.js    # Vite 配置
```

### 4.2 构建前端

```shell
cd frontend
npm install
npm run build
cd ..
rm -rf ether_ghost/public
mv frontend/dist ether_ghost/public
```

或使用根目录脚本：

```shell
bash build.sh
```

### 4.3 打包可执行文件

#### Linux

```shell
bash build.sh
pip install pyinstaller
python pyinstaller_package.bat  # 根据实际环境修改脚本路径
```

#### Windows

参考 [`pyinstaller_package.bat`](./pyinstaller_package.bat)，将虚拟环境路径替换为本地 `site-packages` 目录后执行。

---

## 5. 安全设计

### 5.1 为什么不支持网页端添加 Encoder / Decoder？

Encoder / Decoder 会在服务端启动时作为代码加载。如果攻击者登录了玄联实例，可以通过添加恶意 Encoder 的方式控制服务器，造成服务端 RCE。因此玄联只允许通过文件方式配置，默认情况下还需手动开启环境变量才会启用自定义模块。

### 5.2 认证与会话

- 默认账号 `admin` / `admin123`。
- 首次登录强制修改密码。
- 登录成功后通过 HttpOnly Cookie 下发会话 token。
- 修改密码时若为临时改密 token，改密成功后自动转为正式会话。

### 5.3 敏感数据保护

- OTP Secret 等敏感字段默认使用 AES-256-GCM 加密存储。
- 主密钥首次启动时自动生成于配置目录的 `.secret_key` 文件，也可通过环境变量 `SHADOWHALBERD_SECRET_KEY` 指定。

---

## 6. 常见问题

### Q: 自定义模块或蚁剑 Encoder 找不到？

检查是否已设置对应环境变量并重启：

```shell
export SHADOWHALBERD_ENABLE_CUSTOM_MODULES=1
export SHADOWHALBERD_ENABLE_ANTSWORD_ENCODERS=1
```

### Q: 前端修改后没有生效？

前端修改后必须重新构建，产物位于 `ether_ghost/public/`。

### Q: 如何查看配置目录？

启动时控制台会打印：`从此文件夹加载配置: /path/to/ShadowHalberd`。
