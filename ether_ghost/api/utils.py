"""Utils相关API路由"""

import importlib.metadata
import re
from pathlib import PurePath, PurePosixPath, PureWindowsPath
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from ..utils import const
from ..auth import require_auth

from .base import temp_files

router = APIRouter()


def remote_path(filepath: str) -> PurePath:
    """自动猜测传入文件路径的类型为unix/windows, 并实例化成Path对象"""
    if re.match(r"^[a-zA-Z]:[/\\]", filepath):
        return PureWindowsPath(filepath)
    return PurePosixPath(filepath)


# Utils相关路由
@router.get("/utils/version")
async def version():
    """获取当前版本"""
    current_version = importlib.metadata.version("ether_ghost")
    return {"code": 0, "data": current_version}


@router.get("/utils/background_image")
async def background_image():
    """获取背景图片"""
    for ext in ["png", "jpg", "webp"]:
        filepath = const.DATA_FOLDER / f"bg.{ext}"
        if filepath.exists():
            return FileResponse(path=filepath)
    raise HTTPException(status_code=404, detail="Image not found")


@router.get("/utils/fetch_downloaded_file/{file_id}")
async def fetch_downloaded_file(file_id: UUID):
    """获取下载的文件"""
    if file_id not in temp_files:
        raise HTTPException(status_code=404, detail="File not found")
    (filename, filepath) = temp_files[file_id]
    return FileResponse(path=filepath, filename=filename)


@router.get("/utils/join_path")
async def join_path(folder: str, entry: str):
    """拼接路径"""
    result = None
    if entry == "..":
        result = remote_path(folder).parent
    elif entry == ".":
        result = remote_path(folder)
    else:
        result = remote_path(folder) / entry
    return {"code": 0, "data": result}


@router.get("/utils/test_proxy", dependencies=[Depends(require_auth)])
async def test_proxy(proxy: str, site: str, timeout: int = 10):
    """测试代理"""
    sites = {
        "google": "http://www.gstatic.com/generate_204",
        "cloudflare": "http://cp.cloudflare.com/",
        "microsoft": "http://www.msftconnecttest.com/connecttest.txt",
        "apple": "http://www.apple.com/library/test/success.html",
        "huawei": "http://connectivitycheck.platform.hicloud.com/generate_204",
        "xiaomi": "http://connect.rom.miui.com/generate_204",
    }
    if site not in sites:
        return {"code": -400, "msg": f"指定的服务器{site}未收录"}
    try:
        async with httpx.AsyncClient(proxy=proxy) as client:
            resp = await client.get(sites[site], timeout=timeout)
            return {"code": 0, "data": resp.status_code < 300}
    except Exception:
        return {"code": -500, "msg": f"代理{repr(proxy)}无法连接{site}服务器"}
