"""
主API服务模块

提供Web管理界面后台API，包括：
- Session管理
- 文件传输操作
- TCP代理服务
- PHP相关功能
- 系统设置管理
"""

import asyncio
import functools
import logging
import mimetypes
import re
import secrets
import tempfile
import typing as t

from contextlib import asynccontextmanager
from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath
from uuid import UUID, uuid4

from fastapi import (
    Depends,
    FastAPI,
    Request,
    Response,
)
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .utils import db

from . import (
    session_manager,
    session_types,
    session_connector,
    core,
    session_probe,
)
from .api.auth import router as auth_router
from .api.connector import router as connector_router
from .api.forward_proxy import router as forward_proxy_router, tcp_forward_proxies
from .api.http_proxies import router as http_proxies_router
from .api.session import router as session_router
from .api.sessiontype import router as sessiontype_router
from .api.settings import router as settings_router
from .api.utils import router as utils_router
from .api.webshell_generator import router as webshell_generator_router
from .auth import require_auth, validate_token

from .utils import const

token = secrets.token_bytes(16).hex()
logger = logging.getLogger("main")

# uuid: (filename, blob_path)

VERSION = "0.3.1"


class FileContentRequest(BaseModel):
    current_dir: str
    filename: str
    text: str
    encoding: str


class PhpCodeRequest(BaseModel):
    code: str


temp_dir = Path(tempfile.gettempdir())
temp_files: t.Dict[UUID, t.Tuple[str, Path]] = {}


# TODO: 启动时同时启动所有需要启动的connector


@asynccontextmanager
async def lifespan(api: FastAPI):
    # logger.warning("Your token is %s", token)
    db.ensure_settings()
    db.ensure_auth_config()
    logger.warning("从此文件夹加载配置: %s", const.DATA_FOLDER.as_posix())

    await session_connector.autostart_connectors()

    # 启动后台心跳任务，每 2 小时探测一次所有 session
    heartbeat_task = asyncio.create_task(session_probe.heartbeat_loop(interval=7200))

    yield

    heartbeat_task.cancel()
    try:
        await heartbeat_task
    except asyncio.exceptions.CancelledError:
        pass

    for _, filepath in temp_files.values():
        if filepath.exists():
            filepath.unlink()
    temp_files.clear()
    for tpl in tcp_forward_proxies.values():
        server = tpl[-1]
        try:
            server.cancel()
        except asyncio.exceptions.CancelledError:
            pass
    tcp_forward_proxies.clear()


DIR = Path(__file__).parent
app = FastAPI(lifespan=lifespan)
app.mount("/public", StaticFiles(directory=DIR / "public"), name="public")
app.mount("/assets", StaticFiles(directory=DIR / "public" / "assets"), name="assets")
app.include_router(auth_router)
app.include_router(connector_router, dependencies=[Depends(require_auth)])
app.include_router(forward_proxy_router, dependencies=[Depends(require_auth)])
app.include_router(http_proxies_router, dependencies=[Depends(require_auth)])
app.include_router(session_router, dependencies=[Depends(require_auth)])
app.include_router(sessiontype_router, dependencies=[Depends(require_auth)])
app.include_router(settings_router, dependencies=[Depends(require_auth)])
app.include_router(webshell_generator_router, dependencies=[Depends(require_auth)])
app.include_router(utils_router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许的源，这里设置为所有
    allow_credentials=True,  # 是否允许携带凭据
    allow_methods=["*"],  # 允许的 HTTP 方法
    allow_headers=["*"],  # 允许的头部信息
)

# Public paths that never require authentication
_PUBLIC_PATHS = frozenset({
    "/login.html",
    "/api/auth/login",
    "/api/auth/status",
    "/api/auth/logout",
    "/favicon.ico",
})

mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")


def write_temp_blob(filename: str, blob: bytes):
    filepath = temp_dir / f"{str(uuid4())}.blob"
    filepath.write_bytes(blob)
    file_id = uuid4()
    temp_files[file_id] = (filename, filepath)
    return file_id


def remote_path(filepath: str) -> PurePath:
    """自动猜测传入文件路径的类型为unix/windows, 并实例化成PurePath对象"""
    if re.match(r"^[a-zA-Z]:[/\\]", filepath):
        return PureWindowsPath(filepath)
    return PurePosixPath(filepath)


@app.middleware("http")
async def auth_guard(request: Request, call_next) -> Response:
    """Redirect unauthenticated browser requests to /login.html."""
    path = request.url.path

    # Always allow public paths and CORS preflight
    if path in _PUBLIC_PATHS or request.method == "OPTIONS":
        return await call_next(request)

    # Extract token from cookie or Bearer header
    token = request.cookies.get("ghost_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if token and validate_token(token):
        # Redirect away from login page if already authenticated
        if path == "/login.html":
            return RedirectResponse("/", status_code=302)
        return await call_next(request)

    # Not authenticated.
    # XHR/fetch requests get 401 JSON; browser navigation gets a redirect.
    is_xhr = (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or "application/json" in request.headers.get("Accept", "")
        or path.startswith("/api/")
    )
    if is_xhr:
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)
    return RedirectResponse("/login.html", status_code=302)


@app.middleware("http")
async def set_no_cache(request, call_next) -> Response:
    """让浏览器不要缓存文件"""
    response: Response = await call_next(request)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


def catch_user_error(fn):
    @functools.wraps(fn)
    async def _wraps(*args, **kwargs):
        try:
            return await fn(*args, **kwargs)
        except core.SessionException as exc:
            return {
                "code": getattr(type(exc), "code", -500),
                "msg": f"{type(exc).__doc__}: {str(exc)}",
            }

    return _wraps


async def list_sessions_readable():
    result = session_manager.list_sessions_db_readable() + [
        session_manager.session_to_readable(session)
        for session in session_connector.list_sessions()
    ]
    return result


async def get_session(session_id: UUID):
    session: t.Union[session_types.SessionInfo, None] = (
        session_manager.get_session_info_by_id(session_id)
    )
    if not session:
        raise core.UserError("没有这个session")
    return session


@app.get("/login.html", include_in_schema=False)
async def login_page():
    """Serve the standalone login page."""
    return HTMLResponse((DIR / "login.html").read_text(encoding="utf-8"))


@app.get("/", dependencies=[Depends(require_auth)])
async def hello_world():
    """转到主页"""
    return RedirectResponse("/public/index.html")
