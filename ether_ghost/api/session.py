"""Session相关API路由"""

import asyncio
from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath
from uuid import UUID, uuid4
from functools import wraps
import tempfile

import base64
import logging
import typing as t

import re
import chardet
from fastapi import APIRouter, Body, File, Form, Request, UploadFile
from fastapi.responses import Response

from urllib.parse import urlparse

from .. import core, session_manager, session_types, session_connector
from ..core import SessionInterface, PHPSessionInterface, ProcessProtocol
from ..utils import db
from ..core import SessionException, UserError
from .. import file_transfer_status, session_probe

from pydantic import BaseModel
from ..vessel_php.main import start_vessel_server

from .base import write_temp_blob

logger = logging.getLogger("main")
router = APIRouter()

processes: t.Dict[UUID, ProcessProtocol] = {}


def remote_path(filepath: str) -> PurePath:
    """自动猜测传入文件路径的类型为unix/windows, 并实例化成PurePath对象"""
    if re.match(r"^[a-zA-Z]:[/\\]", filepath):
        return PureWindowsPath(filepath)
    return PurePosixPath(filepath)


class FileContentRequest(BaseModel):
    current_dir: str
    filename: str
    text: str
    encoding: str


class ModifyFileRequest(BaseModel):
    filepath: str
    old_str: str
    new_str: str
    replace_strategy: t.Union[str, None] = None


class PhpCodeRequest(BaseModel):
    code: str


def catch_user_error(fn):
    @wraps(fn)
    async def _wraps(*args, **kwargs):
        try:
            return await fn(*args, **kwargs)
        except SessionException as exc:
            return {
                "code": getattr(type(exc), "code", -500),
                "msg": f"{type(exc).__doc__}: {str(exc)}",
            }

    return _wraps


async def get_session(session_id: UUID):
    session: t.Union[session_types.SessionInfo, None] = (
        session_manager.get_session_info_by_id(session_id)
    )
    if not session:
        raise UserError("没有这个session")
    return session


async def list_sessions_readable():
    result = session_manager.list_sessions_db_readable() + [
        session_manager.session_to_readable(session)
        for session in session_connector.list_sessions()
    ]
    return result


@router.post("/test_webshell")
@catch_user_error
async def test_webshell(session_info: session_types.SessionInfo):
    """测试webshell"""
    try:
        session = session_manager.session_info_to_session(session_info)
        result = await session.test_usablility()
    except Exception as exc:
        logger.exception("测试webshell失败: %s", session_info.session_id)
        return {
            "code": 0,
            "data": {"success": False, "msg": f"测试失败：{exc}"},
        }
    if not result:
        return {"code": 0, "data": {"success": False, "msg": "Webshell无法使用"}}
    return {"code": 0, "data": {"success": True, "msg": "Webshell可以使用"}}


@router.post("/update_webshell")
async def update_webshell(session_info: session_types.SessionInfo):
    """添加或更新webshell"""
    if db.get_session_info_by_id(session_info.session_id):
        db.delete_session_info_by_id(session_info.session_id)
    db.add_session_info(session_info)
    session_manager.clear_session_cache()
    # 异步触发一次探测，立即更新主页的 OS/内网IP/用户名等缓存字段
    asyncio.create_task(session_probe.update_session_cache(session_info.session_id))
    return {"code": 0, "data": session_info.session_id}


class BatchImportWebshellRequest(BaseModel):
    """批量导入 WebShell 请求"""

    content: str
    session_type: str = "ONELINE_PHP"
    delimiter: str = "|"


class BatchImportResult(BaseModel):
    """批量导入 WebShell 结果"""

    created: int
    skipped: int
    failed: t.List[t.Dict[str, str]]
    session_ids: t.List[UUID]


def _get_default_connection(session_type: str) -> t.Dict[str, t.Any]:
    """根据 session_type 获取连接选项默认值"""
    if session_type not in core.session_type_info:
        raise core.UserError(f"Session类型{session_type}不存在")
    connection: t.Dict[str, t.Any] = {}
    for group in core.session_type_info[session_type]["options"]:
        for option in group["options"]:
            if option["default_value"] is not None:
                connection[option["id"]] = option["default_value"]
    return connection


@router.post("/batch_import_webshells")
@catch_user_error
async def batch_import_webshells(request: BatchImportWebshellRequest):
    """批量导入 webshell，格式：URL|密码，每行一个"""
    session_type = request.session_type
    if session_type not in core.session_type_info:
        raise core.UserError(f"Session类型{session_type}不存在")

    default_connection = _get_default_connection(session_type)
    created_session_ids: t.List[UUID] = []
    failed: t.List[t.Dict[str, str]] = []
    sessions_to_add: t.List[session_types.SessionInfo] = []
    skipped = 0

    # 收集已有的 URL 集合，用于去重
    existing_urls: t.Set[str] = set()
    for s in db.list_sessions():
        url = s.connection.get("url", "")
        if url:
            existing_urls.add(url.strip())
    # 当前批次内的 URL 集合，防止同一批里也出现重复
    batch_urls: t.Set[str] = set()

    lines = request.content.splitlines()
    for idx, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line:
            continue

        # 支持 \| 转义分隔符
        parts = line.split(request.delimiter)
        # 处理转义：把被 \ 转义的 | 重新合并
        merged: t.List[str] = []
        current = ""
        for part in parts:
            if current.endswith("\\"):
                current = current[:-1] + request.delimiter + part
            else:
                if current:
                    merged.append(current)
                current = part
        merged.append(current)

        if len(merged) < 2:
            failed.append({"line": str(idx), "reason": "格式错误，需要 URL|密码"})
            continue
        url = merged[0].strip()
        password = merged[1].strip()
        if not url:
            failed.append({"line": str(idx), "reason": "URL 为空"})
            continue
        if not password:
            failed.append({"line": str(idx), "reason": "密码为空"})
            continue

        if url in existing_urls or url in batch_urls:
            skipped += 1
            continue
        batch_urls.add(url)

        connection = {**default_connection, "url": url, "password": password}
        # 自动生成名称：使用 URL 最后一段路径
        parsed = urlparse(url)
        path_name = parsed.path.split("/")[-1] or "shell"
        name = path_name

        session_info = session_types.SessionInfo(
            session_type=session_type,
            name=name,
            note="批量导入",
            connection=connection,
        )
        sessions_to_add.append(session_info)

    if sessions_to_add:
        db.add_session_infos(sessions_to_add)
        session_manager.clear_session_cache()
        for session_info in sessions_to_add:
            created_session_ids.append(session_info.session_id)
            asyncio.create_task(session_probe.update_session_cache(session_info.session_id))

    result = BatchImportResult(
        created=len(sessions_to_add),
        skipped=skipped,
        failed=failed,
        session_ids=created_session_ids,
    )
    return {"code": 0, "data": result.model_dump()}


@router.get("/session")
@catch_user_error
async def api_list_sessions(session_id: t.Union[UUID, None] = None):
    """列出所有的session或者查找session"""
    if session_id is None:
        return {"code": 0, "data": await list_sessions_readable()}
    return {"code": 0, "data": await get_session(session_id)}


@router.get("/session/tags")
@catch_user_error
async def get_all_tags():
    """获取系统中所有 session 的去重标签列表"""
    sessions = db.list_sessions()
    tags = sorted({tag for session in sessions for tag in (session.tags or [])})
    return {"code": 0, "data": tags}


class SetTagsRequest(BaseModel):
    tags: t.List[str]


@router.post("/session/{session_id}/set_tags")
@catch_user_error
async def set_session_tags(session_id: UUID, request: SetTagsRequest):
    """更新 session 的分组标签"""
    success = db.update_session_info_cache(str(session_id), {"tags": request.tags})
    if not success:
        raise UserError("没有这个session")
    return {"code": 0, "data": True}


@router.get("/session/{session_id}")
@catch_user_error
async def api_get_session(session_id: UUID):
    """查找session"""
    return {"code": 0, "data": await get_session(session_id)}


@router.post("/session/{session_id}/probe")
@catch_user_error
async def api_probe_session(session_id: UUID):
    """手动探测单个session，更新缓存"""
    success = await session_probe.update_session_cache(session_id)
    if not success:
        return {"code": -400, "msg": "更新缓存失败：找不到对应的session"}
    return {"code": 0, "data": True}


@router.post("/session/probe_all")
@catch_user_error
async def api_probe_all_sessions():
    """手动触发全部session探测，使用 20 并发"""
    await session_probe.probe_all_sessions(max_concurrency=20)
    return {"code": 0, "data": True}


@router.get("/session/{session_id}/execute_cmd")
@catch_user_error
async def session_execute_cmd(session_id: UUID, cmd: str):
    """使用session执行shell命令"""
    session: SessionInterface = session_manager.get_session_by_id(session_id)
    result = await session.execute_cmd(cmd)
    return {"code": 0, "data": result}


@router.get("/session/{session_id}/get_pwd")
@catch_user_error
async def session_get_pwd(session_id: UUID):
    """获取session的pwd"""
    session: SessionInterface = session_manager.get_session_by_id(session_id)
    result = await session.get_pwd()
    return {"code": 0, "data": result}


@router.get("/session/{session_id}/list_dir")
@catch_user_error
async def session_list_dir(session_id: UUID, current_dir: str):
    """使用session列出某个目录"""
    session: SessionInterface = session_manager.get_session_by_id(session_id)
    result = await session.list_dir(current_dir)
    return {"code": 0, "data": result}


@router.get("/session/{session_id}/mkdir")
@catch_user_error
async def session_mkdir(session_id: UUID, dirpath: str):
    """使用session创建某个目录"""
    session: SessionInterface = session_manager.get_session_by_id(session_id)
    await session.mkdir(dirpath)
    return {"code": 0, "data": True}


@router.get("/session/{session_id}/move_file")
@catch_user_error
async def session_move_file(session_id: UUID, filepath: str, new_filepath):
    """使用session移动某个文件"""
    session: SessionInterface = session_manager.get_session_by_id(session_id)
    await session.move_file(filepath, new_filepath)
    return {"code": 0, "data": True}


@router.get("/session/{session_id}/copy_file")
@catch_user_error
async def session_copy_file(session_id: UUID, filepath: str, new_filepath):
    """使用session复制某个文件"""
    session: SessionInterface = session_manager.get_session_by_id(session_id)
    await session.copy_file(filepath, new_filepath)
    return {"code": 0, "data": True}


@router.get("/session/{session_id}/get_file_contents")
@catch_user_error
async def session_get_file_contents(session_id: UUID, current_dir: str, filename: str):
    """使用session获取文件内容"""
    session: SessionInterface = session_manager.get_session_by_id(session_id)
    content, detected_encoding = None, None
    path = remote_path(current_dir) / filename
    content = await session.get_file_contents(str(path))
    try:
        detected_encoding = chardet.detect(content)["encoding"]
        if detected_encoding is None or detected_encoding == "ascii":
            detected_encoding = "utf-8" if current_dir.startswith("/") else "gbk"
        text = content.decode(detected_encoding)
        return {"code": 0, "data": {"text": text, "encoding": detected_encoding}}
    except UnicodeDecodeError as exc:
        return {
            "code": -500,
            "msg": f"编码错误：检测出编码为{detected_encoding}，但是解码失败："
            + str(exc),
        }


@router.post("/session/{session_id}/put_file_contents")
@catch_user_error
async def session_put_file_contents(session_id: UUID, request: FileContentRequest):
    """使用session写入文件内容"""
    session: SessionInterface = session_manager.get_session_by_id(session_id)
    path = remote_path(request.current_dir) / request.filename
    content = request.text.encode(request.encoding)
    success = await session.put_file_contents(str(path), content)
    return {"code": 0, "data": success}


class TouchLikeRequest(BaseModel):
    filepath: str
    current_dir: str


@router.post("/session/{session_id}/touch_like")
@catch_user_error
async def session_touch_like(session_id: UUID, request: TouchLikeRequest):
    """保存后从当前目录随机选一个文件，将其 mtime 复制给目标文件"""
    import random as _random
    session: SessionInterface = session_manager.get_session_by_id(session_id)
    try:
        entries = await session.list_dir(request.current_dir)
        candidates = [
            e for e in entries
            if e.entry_type in ("file", "link-file")
            and e.name not in (".", "..")
            and str(remote_path(request.current_dir) / e.name) != request.filepath
            and e.mtime > 0
        ]
        if not candidates:
            return {"code": 0, "data": False}
        source = _random.choice(candidates)
        source_path = str(remote_path(request.current_dir) / source.name)
        success = await session.touch_like(request.filepath, source_path)
        return {"code": 0, "data": success}
    except Exception:
        return {"code": 0, "data": False}


@router.post("/session/{session_id}/modify_file")
@catch_user_error
async def session_modify_file(session_id: UUID, request: ModifyFileRequest):
    """使用session修改文件内容"""
    session: SessionInterface = session_manager.get_session_by_id(session_id)
    await session.modify_file(
        request.filepath,
        request.old_str,
        request.new_str,
        request.replace_strategy,
    )
    return {"code": 0, "data": True}


@router.post("/session/{session_id}/upload_file")
@catch_user_error
async def session_upload_file(
    session_id: UUID,
    file: UploadFile = File(),
    folder: str = Form(),
):
    """使用session写入文件内容"""
    session: SessionInterface = session_manager.get_session_by_id(session_id)
    filename = file.filename
    content = await file.read()
    if filename is None:
        return {"code": -400, "msg": "错误: 没有文件名"}
    path = remote_path(folder) / filename
    with file_transfer_status.record_upload_file(
        session_id, folder, filename
    ) as status_changer:
        success = await session.upload_file(str(path), content, callback=status_changer)
    return {"code": 0, "data": success}


@router.get("/session/{session_id}/download_file")
@catch_user_error
async def session_download_file(
    session_id: UUID,
    folder: str,
    filename: str,
):
    """使用session写入文件内容"""
    # 一个文件最多只有几十兆，浏览器应该可以轻松处理
    # 如果用户想要用webshell下载几百兆的文件。。。那应该是用户自己的问题
    filepath = remote_path(folder) / filename
    session: SessionInterface = session_manager.get_session_by_id(session_id)
    with file_transfer_status.record_download_file(
        session_id, folder, filename
    ) as status_changer:
        content = await session.download_file(str(filepath), callback=status_changer)
    file_id = write_temp_blob(filename, content)
    return {
        "code": 0,
        "data": {
            "file_id": file_id,
        },
    }


@router.get("/session/{session_id}/delete_file")
@catch_user_error
async def session_delete_file(session_id: UUID, current_dir: str, filename: str):
    """使用session删除文件内容"""
    # TODO: 让所有webshell支持删除文件夹
    session: SessionInterface = session_manager.get_session_by_id(session_id)
    path = remote_path(current_dir) / filename
    result = await session.delete_file(str(path))
    return {"code": 0, "data": result}


@router.get("/session/{session_id}/chmod")
@catch_user_error
async def session_chmod(session_id: UUID, filepath: str, mode: str):
    """使用session修改文件或目录权限"""
    session: SessionInterface = session_manager.get_session_by_id(session_id)
    await session.chmod(filepath, mode)
    return {"code": 0, "data": True}


@router.get("/session/{session_id}/supported_send_tcp_methods")
@catch_user_error
async def session_supported_send_tcp_methods(
    session_id: UUID,
):
    """使用session发送一段字节到某个TCP端口"""
    session: SessionInterface = session_manager.get_session_by_id(session_id)
    result = await session.get_send_tcp_support_methods()
    return {
        "code": 0,
        "data": result,
    }


@router.post("/session/{session_id}/send_bytes_tcp")
@catch_user_error
async def session_send_bytes_tcp(
    session_id: UUID,
    host: str = Body(),
    port: int = Body(),
    content_b64: str = Body(),
    send_method: t.Union[str, None] = Body(),
):
    """使用session发送一段字节到某个TCP端口"""
    session: SessionInterface = session_manager.get_session_by_id(session_id)
    result = await session.send_bytes_over_tcp(
        host, port, base64.b64decode(content_b64), send_method
    )
    if result is None:
        return {"code": -600, "msg": "受控端发送TCP失败"}
    return {
        "code": 0,
        "data": base64.b64encode(result),
    }


@router.get("/session/{session_id}/file_upload_status")
@catch_user_error
async def session_get_file_upload_status(session_id: UUID):
    """读取session正在上传的文件"""
    result = file_transfer_status.get_session_uploading_file(session_id)
    return {"code": 0, "data": result}


@router.get("/session/{session_id}/file_download_status")
@catch_user_error
async def session_get_file_download_status(session_id: UUID):
    """读取session正在下载的文件"""
    result = file_transfer_status.get_session_downloading_file(session_id)
    return {"code": 0, "data": result}


@router.get("/session/{session_id}/basicinfo")
@catch_user_error
async def session_get_basicinfo(session_id: UUID):
    """读取session的相关信息"""
    session: SessionInterface = session_manager.get_session_by_id(session_id)
    result = await session.get_basicinfo()
    return {"code": 0, "data": result}


@router.get("/session/{session_id}/download_phpinfo")
@catch_user_error
async def session_download_phpinfo(session_id: UUID):
    """下载phpinfo"""
    session: SessionInterface = session_manager.get_session_by_id(session_id)
    if not isinstance(session, PHPSessionInterface):
        return {"code": -400, "msg": "指定的session不是PHP Session"}
    content = await session.download_phpinfo()

    headers = {"Content-Disposition": "attachment; filename=phpinfo.html"}  # 设置文件名
    return Response(content=content, media_type="text/html", headers=headers)


@router.post("/session/{session_id}/php_eval")
@catch_user_error
async def session_php_eval(session_id: UUID, req: PhpCodeRequest):
    """eval对应代码"""
    session: SessionInterface = session_manager.get_session_by_id(session_id)
    if not isinstance(session, PHPSessionInterface):
        return {"code": -400, "msg": "指定的session不是PHP Session"}
    result = await session.php_eval(req.code)
    return {"code": 0, "data": result}


class SendHttpRequestRequest(BaseModel):
    url: str
    method: str = "GET"
    headers: t.Union[t.Dict[str, str], None] = None
    params: t.Union[t.Dict[str, t.Any], None] = None
    data: t.Union[str, None] = None
    data_b64: t.Union[str, None] = None


class CreateProcessRequest(BaseModel):
    argv: t.List[str]
    overrides_env: t.Union[t.Dict[str, str], None] = None


class SendSignalRequest(BaseModel):
    signal: int


class WriteStdinRequest(BaseModel):
    data_b64: str


@router.post("/session/{session_id}/send_http_request")
@catch_user_error
async def session_send_http_request(
    session_id: UUID,
    req: SendHttpRequestRequest,
):
    """通过受控端发送HTTP请求"""
    session: SessionInterface = session_manager.get_session_by_id(session_id)
    data: t.Union[str, bytes, None] = None
    if req.data_b64 is not None:
        data = base64.b64decode(req.data_b64)
    elif req.data is not None:
        data = req.data
    result = await session.send_http_request(
        url=req.url,
        method=req.method,
        headers=req.headers,
        params=req.params,
        data=data,
    )
    return {
        "code": 0,
        "data": {
            "status_code": result["status_code"],
            "headers": result["headers"],
            "body": base64.b64encode(result["body"]).decode(),
        },
    }


@router.get("/session/{session_id}/deploy_vessel")
@catch_user_error
async def session_deploy_vessel(session_id: UUID):
    """部署vessel server"""
    session: SessionInterface = session_manager.get_session_by_id(session_id)
    if not isinstance(session, PHPSessionInterface):
        return {"code": -400, "msg": "指定的session不是PHP Session"}
    client_code, _ = await start_vessel_server(session)
    return {"code": 0, "data": client_code}


@router.post("/session/{session_id}/emulated_antsword")
@catch_user_error
async def session_emulated_antsword(session_id: UUID, request: Request):
    """对接蚁剑"""
    session: SessionInterface = session_manager.get_session_by_id(session_id)
    if not isinstance(session, PHPSessionInterface):
        return {"code": -400, "msg": "指定的session不是PHP Session"}
    body: bytes = await request.body()
    status_code, content = await session.emulated_antsword(body)
    return Response(status_code=status_code, content=content)


@router.delete("/session/{session_id}")
async def delete_session(session_id: UUID):
    """删除session"""
    session: t.Union[session_types.SessionInfo, None] = (
        session_manager.get_session_info_by_id(session_id)
    )
    if session is None:
        return {"code": -400, "msg": "没有这个session"}
    await session_manager.delete_session_info_by_id(session_id)
    return {"code": 0, "data": True}


class BatchDeleteRequest(BaseModel):
    """批量删除 WebShell 请求"""

    session_ids: t.List[UUID]


@router.post("/batch_delete_sessions")
@catch_user_error
async def batch_delete_sessions(request: BatchDeleteRequest):
    """批量删除 session"""
    deleted = 0
    failed: t.List[t.Dict[str, str]] = []
    for session_id in request.session_ids:
        session = session_manager.get_session_info_by_id(session_id)
        if session is None:
            failed.append({"session_id": str(session_id), "reason": "没有这个session"})
            continue
        try:
            await session_manager.delete_session_info_by_id(session_id)
            deleted += 1
        except Exception as exc:
            logger.exception("批量删除 session 失败: %s", session_id)
            failed.append({"session_id": str(session_id), "reason": f"删除失败：{exc}"})
    session_manager.clear_session_cache()
    return {"code": 0, "data": {"deleted": deleted, "failed": failed}}


@router.post("/clear_all_sessions")
@catch_user_error
async def clear_all_sessions():
    """清空所有 session"""
    deleted = db.delete_all_sessions()
    session_manager.clear_session_cache()
    return {"code": 0, "data": {"deleted": deleted}}


def _get_process(process_id: UUID) -> ProcessProtocol:
    process = processes.get(process_id)
    if process is None:
        raise UserError("没有这个进程")
    return process


@router.post("/session/{session_id}/process")
@catch_user_error
async def create_process(session_id: UUID, req: CreateProcessRequest):
    """创建进程"""
    session: SessionInterface = session_manager.get_session_by_id(session_id)
    process = await session.create_process(req.argv, req.overrides_env)
    process_id = uuid4()
    processes[process_id] = process
    return {
        "code": 0,
        "data": {
            "process_id": process_id,
            "pid": process.pid,
        },
    }


@router.post("/process/{process_id}/send_signal")
@catch_user_error
async def process_send_signal(process_id: UUID, req: SendSignalRequest):
    """向进程发送信号"""
    process = _get_process(process_id)
    await process.send_signal(req.signal)
    return {"code": 0, "data": True}


@router.post("/process/{process_id}/write_stdin")
@catch_user_error
async def process_write_stdin(process_id: UUID, req: WriteStdinRequest):
    """向进程标准输入写入数据"""
    process = _get_process(process_id)
    await process.write_stdin(base64.b64decode(req.data_b64))
    return {"code": 0, "data": True}


@router.get("/process/{process_id}/read_stdout_stderr")
@catch_user_error
async def process_read_stdout_stderr(process_id: UUID):
    """读取进程的stdout和stderr"""
    process = _get_process(process_id)
    stdout, stderr = await process.read_stdout_stderr()
    return {
        "code": 0,
        "data": {
            "stdout": base64.b64encode(stdout).decode(),
            "stderr": base64.b64encode(stderr).decode(),
        },
    }


@router.get("/process/{process_id}/wait")
@catch_user_error
async def process_wait(process_id: UUID, timeout: float):
    """等待进程结束"""
    process = _get_process(process_id)
    returncode = await process.wait(timeout)
    return {"code": 0, "data": {"returncode": returncode}}
