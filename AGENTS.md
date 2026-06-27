# AGENTS.md - ShadowHalberd 项目指南

## 项目简介

ShadowHalberd（幽魂）是一个新一代Webshell管理器，兼容蚁剑与冰蝎的PHP webshell，同时支持JSP和反弹Shell等多种连接方式。

## 依赖与Poetry

项目使用 [Poetry](https://python-poetry.org/) 管理依赖，配置文件为 `pyproject.toml`。

安装依赖：

```bash
poetry install
```

运行项目：

```bash
poetry run ether_ghost
```

核心运行时依赖：

| 包 | 用途 |
|---|---|
| pydantic | 数据模型（SessionInfo等） |
| fastapi | Web管理后端API |
| sqlalchemy | SQLite数据库ORM |
| uvicorn | ASGI服务器 |
| httpx | HTTP客户端（含SOCKS代理支持） |
| pycryptodome | PHP流量加解密 |
| python-multipart | 文件上传 |

开发依赖包含 mypy 用于静态类型检查。

## 项目打包

使用 poetry-core 构建：

```bash
poetry build
```

生成 sdist 和 wheel 包，入口点为 `ether_ghost.__main__:main`。

也支持 PyInstaller 打包为独立可执行文件，见 `build.sh`（Linux）和 `pyinstaller_package.bat`（Windows）。

## 前端构建

前端代码位于 `frontend/` 目录，使用 Vite 构建。构建产物为 `ether_ghost/public/` 目录下的静态文件。

**重要**：修改前端代码后，必须运行 `build.sh` 重新构建，并将构建产物（`ether_ghost/public/`）与前端源码的修改放在同一个 git commit 中提交。不要单独提交构建产物，也不要遗漏构建产物的提交。

## 主要功能

- **多协议Webshell管理**：PHP一句话、PHP原始、PHP冰蝎、PHP幽魂、JSP冰蝎、Linux CMD一句话
- **Session连接器**：TCP反弹Shell的持久化监听和自动重连
- **文件管理**：上传、下载、目录浏览、文件编辑
- **TCP代理**：通过Vessel正向代理（PHP内存马）和伪正向代理（gopher/SSRF）
- **自定义编码器/解码器**：支持Python编写的encoder/decoder，兼容蚁剑格式
- **Web管理界面**：FastAPI + 静态前端，支持多主题

## Webshell表示与连接逻辑

### 层级结构

```
SessionInfo (Pydantic Model, `./ether_ghost/session_types.py`)
  └── 存储session的元数据（名称、备注、连接配置JSON）
       ▼
SessionInterface (Protocol, `./ether_ghost/core/base.py`)
  └── 定义webshell的操作接口（execute_cmd, list_dir, upload/download等）
       ▼
具体实现类 (如 PHPWebshellOneliner, `./ether_ghost/sessions/php_oneliner.py`)
  └── 实现特定webshell类型的通信协议
```

### 连接逻辑涉及的类

1. **`SessionInfo`** (`./ether_ghost/session_types.py`) - Pydantic模型，保存session类型、名称、连接配置字典
2. **`SessionInterface`** (`./ether_ghost/core/base.py`) - 抽象接口，定义webshell的标准操作
3. **`PHPSessionInterface`** (`./ether_ghost/core/base.py`) - PHP专属扩展接口（eval, phpinfo等）
4. **`session_type_info`** (`./ether_ghost/core/base.py`) - 全局注册表，映射 `session_type` 字符串到构造函数
5. **`SessionConnector`** (`./ether_ghost/session_connector.py`) - 连接器协议，管理持久化连接（如反弹Shell监听端口）
6. **`session_manager`** (`./ether_ghost/session_manager.py`) - 统一管理SessionInfo的CRUD和Session对象的缓存（300秒TTL）
7. **`@register_session`** (`./ether_ghost/core/base.py`) - 装饰器，将session类注册到全局注册表
8. **`@register_connector`** (`./ether_ghost/session_connector.py`) - 装饰器，将connector类注册到全局注册表

### 连接流程

1. 用户通过API创建 `SessionInfo`，存入SQLite
2. 请求时 `session_manager.get_session_by_id()` 查询 `SessionInfo` 并用 `session_type_info` 构造对应的 `SessionInterface` 实例
3. 对于持久化连接（反弹Shell），`SessionConnector` 在后台运行并管理连接生命周期
4. Connector session也会注册到 `session_type_info`，通过 `connector.build_session()` 构造Session

## SQLite使用

数据存储在SQLite中，使用SQLAlchemy ORM。存储路径由 `./ether_ghost/utils/const.py` 中的 `STORE_URL` 确定：

```python
STORE_URL = "sqlite:///" + (DATA_FOLDER / "store.db").as_posix()
```

### 数据表

| 表名 | Model | 用途 |
|---|---|---|
| session_info | `SessionInfoModel` | 保存webshell连接信息 |
| session_connector | `SessionConnectorModel` | 保存持久连接器配置 |
| settings | `SettingsModel` | 保存系统设置（主题、代理等） |

所有数据库操作在 `./ether_ghost/utils/db.py` 中。

## 配置与环境变量

### 数据目录

`DATA_FOLDER` 根据操作系统自动选择：

| 系统 | 路径 |
|---|---|
| Linux | `~/.local/share/ShadowHalberd` |
| Windows | `~/AppData/Roaming/ShadowHalberd` |
| macOS | `~/Library/Application Support/ShadowHalberd` |

配置通过SQLite中的 `settings` 表管理：
- `theme`: 界面主题（默认 "green"）
- `proxy`: HTTP代理地址

### 启动参数

```bash
ether_ghost --host 127.0.0.1 --port 8022 --no-browser
```

| 参数 | 默认值 | 说明 |
|---|---|---|
| --host | 127.0.0.1 | 监听地址 |
| --port | 8022 | 监听端口 |
| --no-browser | false | 不自动打开浏览器 |

## 查看issue时

issue中的评论一般包含之前的经验总结。为了避免犯下同样的错误，你总是查看issue的评论。

你需要仔细分析issue中的每一个要点，并对于每个要点详细**设计**(DESIGN)如何解决

## 提交pr时

在pr中使用`resolve #xx`, `fix #xx`等语法关联对应issue

## 提交pr后

提交pr后，你应该先sleep十分钟等待CI运行，然后检查PR的CI是否通过，如果通过则进入等待循环，没通过则查看ci日志并修复

## 等待循环

你在工作基本完成后进入等待循环，每次都**重新规划**检查以下事项：

- pr详情：查看pr,检查是否可以合并，是否正在开启，是否有审核意见，是否有评论
- pr审核意见：当前最新的审核意见有几条，分别是什么，有没有被处理，应该检查什么
- pr是否有评论（用issue_read查看）
- **CI是否通过**：用给定方式重新找到当前的ci日志并重新读取日志本身

如果这几项都检查完毕，sleep 10~30分钟并**重新**规划检查

## pr被关闭时

如果你的pr被关闭，你总是检查：

- 审核意见
- ci是否通过
- 当前pr是否是空pr

在pr被关闭时，你**总是新建新pr**而非重新打开pr解决问题

## pr被合并时

等待issue被关闭，如果对应issue没被关闭，你添加评论并等待issue更新（被回复或者被关闭等）

## 查看CI

你提交pr之后，有一个CI job会被触发运行：CI test

### CI运行状态返回空列表

CI运行状态为空，可能是因为

1. CI job还没有运行
2. 前面的CI job失败而跳过
3. 本地commit没有push

【重要】如果CI run列表一直为空，重新检查本地和远程的head sha是否一致，head sha对应的所有CI run查看是否有其他CI失败

【重要】如果CI run列表一直为空，重新检查本地和远程的head sha是否一致，head sha对应的所有CI run查看是否有其他CI失败

【重要】如果CI run列表一直为空，重新检查本地和远程的head sha是否一致，head sha对应的所有CI run查看是否有其他CI失败

### CI因为网络失败

如果CI因为网络失败，最快的解决方法是提交一个空commit并push，以触发CI重新运行

或者: 在PR中添加一条评论请求管理者重新运行CI，然后循环等待检查CI是否被重新运行和评论回复，每次sleep 10-30分钟

## 注意

你**永远**耐心等待ci, **永远**不做pr轰炸，打开下一个pr前**总是**关闭上一个pr
