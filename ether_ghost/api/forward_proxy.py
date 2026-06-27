from uuid import UUID
import asyncio
import functools
import typing as t

from fastapi import APIRouter
from pydantic import BaseModel


from .. import session_manager, core


from ..tcp_proxies import (
    start_psudo_tcp_proxy,
    start_vessel_forward_tcp,
    start_vessel_http_proxy,
    start_vessel_socks5_proxy,
)
from ..core import SessionInterface, PHPSessionInterface
from ..vessel_php.main import start_vessel_server


class ProxyRequest(BaseModel):
    type: t.Literal[
        "psudo_forward_proxy",
        "vessel_forward_tcp",
        "vessel_http_proxy",
        "vessel_socks5_proxy",
    ]
    session_id: UUID
    listen_host: t.Union[str, None]
    listen_port: int
    host: t.Union[str, None] = None
    port: t.Union[int, None] = None
    send_method: t.Union[str, None] = None


router = APIRouter()
tcp_forward_proxies: t.Dict[int, t.Tuple[ProxyRequest, asyncio.Task]] = {}
# 每个session复用同一个Vessel服务器，减少受控端PHP工作进程占用
vessel_servers: t.Dict[UUID, t.Tuple[str, asyncio.Task, int]] = {}


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


@router.get("/forward_proxy/list")
@catch_user_error
async def forward_proxy_list():
    def get_session_name(sess_id):
        sess_info = session_manager.get_session_info_by_id(sess_id)
        if not sess_info:
            return "未知Session"
        return sess_info.name

    return {
        "code": 0,
        "data": [
            {
                "type": proxy_request.type,
                "session_id": proxy_request.session_id,
                "session_name": get_session_name(proxy_request.session_id),
                "listen_host": proxy_request.listen_host,
                "listen_port": proxy_request.listen_port,
                "host": proxy_request.host,
                "port": proxy_request.port,
                "send_method": proxy_request.send_method,
            }
            for proxy_request, _ in tcp_forward_proxies.values()
        ],
    }


async def _get_vessel_client_code(
    session: PHPSessionInterface, session_id: UUID
) -> str:
    entry = vessel_servers.get(session_id)
    if entry is not None:
        load_code, task, ref = entry
        vessel_servers[session_id] = (load_code, task, ref + 1)
        return load_code
    load_code, server_task = await start_vessel_server(session)
    vessel_servers[session_id] = (load_code, server_task, 1)
    return load_code


def _release_vessel_client_code(session_id: UUID):
    entry = vessel_servers.get(session_id)
    if entry is None:
        return
    load_code, server_task, ref = entry
    ref -= 1
    if ref <= 0:
        try:
            server_task.cancel()
        except asyncio.exceptions.CancelledError:
            pass
        vessel_servers.pop(session_id, None)
    else:
        vessel_servers[session_id] = (load_code, server_task, ref)


@router.post("/forward_proxy/create_psudo_proxy")
@catch_user_error
async def forward_proxy_create_psudo_proxy(request: ProxyRequest):
    if request.listen_port in tcp_forward_proxies:
        return {"code": -400, "msg": "端口已占用"}
    if request.listen_host is None:
        request.listen_host = "0.0.0.0"
    session: SessionInterface = session_manager.get_session_by_id(request.session_id)
    if request.type == "psudo_forward_proxy":
        server_task = await start_psudo_tcp_proxy(
            session,
            request.listen_host,
            request.listen_port,
            request.host,
            request.port,
            request.send_method,
        )
        tcp_forward_proxies[request.listen_port] = (request, server_task)
        return {"code": 0, "data": True}

    if not isinstance(session, PHPSessionInterface):
        return {"code": -400, "msg": "Vessel当前只支持PHP webshell"}

    if request.type == "vessel_forward_tcp":
        client_code = await _get_vessel_client_code(session, request.session_id)
        server_task = await start_vessel_forward_tcp(
            session=session,
            load_vessel_client_code=client_code,
            listen_host=request.listen_host,
            listen_port=request.listen_port,
            host=request.host,
            port=request.port,
        )
    elif request.type == "vessel_http_proxy":
        server_task = await start_vessel_http_proxy(
            session=session,
            listen_host=request.listen_host,
            listen_port=request.listen_port,
        )
    elif request.type == "vessel_socks5_proxy":
        server_task = await start_vessel_socks5_proxy(
            session=session,
            listen_host=request.listen_host,
            listen_port=request.listen_port,
        )
    else:
        return {"code": -400, "msg": f"不支持的代理类型：{request.type}"}

    tcp_forward_proxies[request.listen_port] = (request, server_task)
    return {"code": 0, "data": True}


@router.delete("/forward_proxy/{listen_port}/")
@catch_user_error
async def forward_proxy_delete(listen_port: int):
    entry = tcp_forward_proxies.pop(listen_port, None)
    if entry is None:
        return {"code": -404, "msg": "代理不存在或已关闭"}
    proxy_request, server_task = entry
    try:
        server_task.cancel()
    except asyncio.exceptions.CancelledError:
        pass
    if proxy_request.type == "vessel_forward_tcp":
        _release_vessel_client_code(proxy_request.session_id)
    return {"code": 0, "data": True}
