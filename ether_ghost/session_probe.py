"""Session 探测与心跳模块

负责周期性探测 webshell 的在线状态、系统、IP、主机名、用户名等信息，
并将结果缓存到数据库，供主页列表展示。
"""

import asyncio
import datetime
import logging
import typing as t
from uuid import UUID

from . import session_manager
from .core import base as core_base
from .utils import db

logger = logging.getLogger("main.session_probe")


def _parse_basicinfo(entries: t.List[core_base.BasicInfoEntry]) -> t.Dict[str, str]:
    """将 BasicInfoEntry 列表转为 key->value 字典"""
    return {entry.key: entry.value for entry in entries}


async def _run_cmd(session, cmd: str) -> str:
    """在 session 上执行命令，失败返回空字符串"""
    try:
        return (await session.execute_cmd(cmd)).strip()
    except Exception as exc:
        logger.debug("probe command failed: %s - %s", cmd, exc)
        return ""


async def probe_session(session_id: t.Union[str, UUID]) -> t.Dict[str, t.Any]:
    """探测单个 session，返回要写入缓存的字段字典

    返回字段包含：status、last_connected_at、os、internal_ip、username。
    """
    try:
        session = session_manager.get_session_by_id(session_id)
    except Exception as exc:
        logger.warning("probe_session: cannot get session %s: %s", session_id, exc)
        return {"status": "offline"}

    try:
        is_online = await session.test_usablility()
    except Exception as exc:
        logger.debug("test_usablility failed for %s: %s", session_id, exc)
        is_online = False

    if not is_online:
        return {"status": "offline"}

    result: t.Dict[str, t.Any] = {
        "status": "online",
        "last_connected_at": datetime.datetime.now(),
    }

    # 获取基础信息
    basicinfo: t.Dict[str, str] = {}
    try:
        entries = await session.get_basicinfo()
        basicinfo = _parse_basicinfo(entries)
    except Exception as exc:
        logger.debug("get_basicinfo failed for %s: %s", session_id, exc)

    # 提取操作系统
    os_value = ""
    if "OS" in basicinfo:
        os_value = basicinfo["OS"]
    elif "System Info" in basicinfo:
        os_value = basicinfo["System Info"]
    elif "OsInfo" in basicinfo:
        os_value = basicinfo["OsInfo"]
    elif "System Version" in basicinfo:
        os_value = basicinfo["System Version"]
    elif "uname -a" in basicinfo:
        parts = basicinfo["uname -a"].strip().split()
        if parts:
            os_value = parts[0]
    result["os"] = os_value

    # 提取内网 IP
    internal_ip = ""
    if "Server Address" in basicinfo:
        internal_ip = basicinfo["Server Address"]
    elif "IPList" in basicinfo:
        # Godzilla IP list — pick first non-127 IPv4
        for part in basicinfo["IPList"].replace(";", ",").split(","):
            ip = part.strip()
            if ip and not ip.startswith("127.") and "." in ip:
                internal_ip = ip
                break
    result["internal_ip"] = internal_ip

    # 提取用户名
    username = ""
    if "Server User" in basicinfo:
        username = basicinfo["Server User"]
    elif "Current User" in basicinfo:
        username = basicinfo["Current User"]
    elif "CurrentUser" in basicinfo:
        username = basicinfo["CurrentUser"]
    elif "whoami" in basicinfo:
        username = basicinfo["whoami"]
    result["username"] = username

    # 根据系统类型补充缺失的信息
    session_type = getattr(session, "session_type", "")
    os_lower = os_value.lower()
    is_windows = "windows" in os_lower or "winnt" in os_lower
    is_linux_like = session_type in ("SSH",)
    # PHP/PHP_RAW 运行在 Linux 服务器上时也尝试补充
    if session_type in ("ONELINE_PHP", "PHP_RAW", "GHOST_PHP"):
        if "linux" in os_lower or "unix" in os_lower:
            is_linux_like = True
    # ASP/ASPX 以及明确返回 Windows 信息的按 Windows 处理
    if not is_windows and (
        "ASP" in session_type or "ASPX" in session_type or "BEHINDER" in session_type or "GODZILLA" in session_type
    ):
        is_windows = True

    if is_windows:
        # Windows 下 whoami / ipconfig 最直接可靠，优先使用
        whoami_out = (await _run_cmd(session, "whoami")).strip()
        if whoami_out:
            # IIS 应用池身份显示为 "iis apppool\apppoolname"，去掉前缀更直观
            lower = whoami_out.lower()
            if lower.startswith("iis apppool\\"):
                username = whoami_out.split("\\", 1)[1]
            else:
                username = whoami_out
        if not internal_ip:
            ipconfig_out = await _run_cmd(session, 'ipconfig | findstr /i "IPv4"')
            for line in ipconfig_out.splitlines():
                if ":" in line:
                    ip = line.split(":", 1)[1].strip()
                    if ip and not ip.startswith("127."):
                        internal_ip = ip
                        break
    elif is_linux_like or not internal_ip:
        if not internal_ip:
            internal_ip = await _run_cmd(
                session, "hostname -I 2>/dev/null | awk '{print $1}'"
            )
        if not internal_ip:
            internal_ip = await _run_cmd(
                session,
                "ip route get 1.1.1.1 2>/dev/null | grep -oP 'src \\K[^ ]+'",
            )
        if not internal_ip:
            internal_ip = await _run_cmd(
                session,
                "ifconfig 2>/dev/null | grep -oP 'inet \\K[0-9.]+' | head -1",
            )

    result["internal_ip"] = internal_ip or result.get("internal_ip", "")
    result["username"] = username or result.get("username", "")

    return result


async def update_session_cache(session_id: t.Union[str, UUID]) -> bool:
    """探测单个 session 并将结果写入数据库缓存"""
    data = await probe_session(session_id)
    return db.update_session_info_cache(session_id, data)


async def probe_all_sessions(max_concurrency: int = 20):
    """探测所有数据库中的 session 并更新缓存

    Args:
        max_concurrency: 最大并发探测数，默认 20
    """
    sessions = session_manager.list_sessions_db_readable()
    semaphore = asyncio.Semaphore(max_concurrency)

    async def _probe_one(session_dict: dict):
        async with semaphore:
            try:
                await update_session_cache(session_dict["id"])
            except Exception as exc:
                logger.warning(
                    "probe_all_sessions: failed for %s: %s",
                    session_dict.get("id"),
                    exc,
                )

    await asyncio.gather(*[_probe_one(s) for s in sessions])


async def heartbeat_loop(interval: int = 7200):
    """后台心跳循环，每隔 interval 秒探测所有 session 一次"""
    while True:
        try:
            await probe_all_sessions()
        except Exception as exc:
            logger.warning("heartbeat_loop error: %s", exc)
        await asyncio.sleep(interval)
