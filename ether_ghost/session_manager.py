"""
Session统一管理模块

负责管理两种核心对象：
1. SessionInfo - 存储session的元数据(名称、备注)和连接配置
2. Session - 实现SessionInterface的实际操作对象，由SessionInfo构造

主要功能：
- SessionInfo的CRUD操作
- Session对象的缓存和生命周期管理
- 两种对象的转换
"""

import datetime
import time
import typing as t
from uuid import UUID

from .utils import db
from . import core, session_connector
from .core.base import session_type_info
from .session_types import (
    SessionInfo,
)

SESSION_CACHE_TIMEOUT = 300
session_store: t.Dict[UUID, t.Tuple[int, core.SessionInterface]] = {}
location_readable = {"US": "🇺🇸"}


def session_info_to_session(session_info: SessionInfo) -> core.SessionInterface:
    """将session info转成session对象

    Args:
        session_info (SessionInfo): session info

    Returns:
        session.Session: session对象
    """
    if session_info.session_type not in session_type_info:
        raise core.UserError(f"Session类型{session_info.session_type}不存在")
    constructor = session_type_info[session_info.session_type]["constructor"]
    return constructor(session_info.connection)


def get_session_info_by_id(
    session_id: t.Union[str, UUID],
) -> t.Union[None, SessionInfo]:
    """根据id返回session info

    Args:
        session_id (t.Union[str, UUID]): session id

    Returns:
        t.Union[None, SessionInfo]: session info，找不到时返回None
    """
    if isinstance(session_id, str):
        session_id = UUID(session_id)
    result = db.get_session_info_by_id(session_id)
    if result is not None:
        return result
    return session_connector.get_session(session_id)


def get_session_by_id(session_id: t.Union[str, UUID]) -> core.SessionInterface:
    """根据id返回session对象，优先返回缓存的对象

    Args:
        session_id (t.Union[str, UUID]): session id

    Returns:
        t.Union[None, session.Session]: session对象，找不到时返回None
    """
    if isinstance(session_id, str):
        session_id = UUID(session_id)
    cache_timeout_sessions = [
        uuid
        for uuid, (timestamp, _) in session_store.items()
        if timestamp + SESSION_CACHE_TIMEOUT < time.time()
    ]
    for uuid in cache_timeout_sessions:
        del session_store[uuid]
    if session_id in session_store:
        _, session = session_store[session_id]
        session_store[session_id] = (int(time.time()), session)
        return session

    session_info = get_session_info_by_id(session_id)
    if session_info is None:
        raise core.UserError("没有这个UUID对应的Session!")
    session = session_info_to_session(session_info)
    session_store[session_id] = (int(time.time()), session)
    return session


def clear_session_cache():
    session_store.clear()


def _get_url_or_host(sess: SessionInfo) -> str:
    """从 connection 中提取 URL 或主机地址"""
    connection = sess.connection or {}
    if "url" in connection:
        return connection["url"] or "-"
    if "host" in connection:
        port = connection.get("port")
        if port:
            return f"{connection['host']}:{port}"
        return connection["host"] or "-"
    return "-"


def _get_encryption_method(sess: SessionInfo) -> str:
    """根据 session_type 和 connection 推导加密方式"""
    connection = sess.connection or {}
    session_type = sess.session_type

    if session_type == "BEHINDER_PHP_AES":
        return "AES"
    if session_type == "BEHINDER_PHP_XOR":
        return "XOR"
    if session_type == "SSH":
        return "SSH"
    if session_type == "ONELINE_PHP":
        encryption = connection.get("encryption")
        if encryption:
            return "RSA+AES"
        antsword_encoder = connection.get("antsword_encoder")
        if antsword_encoder and antsword_encoder != "none":
            return f"蚁剑/{antsword_encoder}"
        encoder = connection.get("encoder")
        if encoder and encoder != "raw":
            return encoder
        return "明文"
    if session_type == "PHP_RAW":
        encoder = connection.get("encoder")
        if encoder and encoder != "raw":
            return encoder
        return "明文"
    return "-"


def _format_datetime(value: t.Optional[datetime.datetime]) -> str:
    """格式化日期时间，空值返回 -"""
    if value is None:
        return "-"
    return value.strftime("%Y-%m-%d %H:%M:%S")


def session_to_readable(sess: SessionInfo) -> t.Dict[str, t.Any]:
    """将SessionInfo对象转换为可读的字典"""
    return {
        "type": sess.session_type,
        "readable_type": session_type_info[sess.session_type]["readable_name"],
        "id": sess.session_id,
        "name": sess.name,
        "note": sess.note or "-",
        "location": location_readable.get(sess.location, "未知位置"),
        "tags": sess.tags or [],
        "os": sess.os or "-",
        "internal_ip": sess.internal_ip or "-",
        "username": sess.username or "-",
        "url": _get_url_or_host(sess),
        "encryption_method": _get_encryption_method(sess),
        "last_connected_at": _format_datetime(sess.last_connected_at),
        "status": sess.status or "unknown",
    }


def list_sessions_db_readable() -> t.List[t.Dict[str, t.Any]]:
    """列出所有的session info（可读格式）"""
    return [session_to_readable(sess) for sess in db.list_sessions()]


def add_session_info(info: SessionInfo):
    """将session info添加到数据库"""
    db.add_session_info(info)


async def delete_session_info_by_id(session_id: UUID):
    """根据session id删除某个session
    如果是Connector的session则通知connector关闭，否则从数据库中删除"""
    if connector := session_connector.get_connector_of_session(session_id):
        session_info = get_session_info_by_id(session_id)
        assert (
            session_info is not None
        ), "Internal error: we should get session info when finding its connector"
        await connector.close_session(session_info.connection)
    db.delete_session_info_by_id(session_id)
