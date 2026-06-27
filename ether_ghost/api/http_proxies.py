"""HTTP代理列表相关API路由"""

import asyncio
import datetime
import re
import time
import typing as t
from uuid import UUID

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..core import ServerError
from ..utils import db

router = APIRouter()

_TEST_URL = "http://www.google.com/generate_204"
_TEST_TIMEOUT = 10.0

_PROXY_URL_RE = re.compile(
    r"^(?:(?P<scheme>[a-zA-Z][a-zA-Z0-9+.-]*)://)?"
    r"(?:(?P<user>[^:@]+)(?::(?P<passwd>[^@]*))?@)?"
    r"(?P<host>[^:@/\s]+)"
    r":(?P<port>\d{1,5})$"
)


class HttpProxyAddRequest(BaseModel):
    url: str
    note: str = ""


class HttpProxyBatchAddRequest(BaseModel):
    urls: t.List[str]
    scheme: str = "http"


class HttpProxyTestRequest(BaseModel):
    url: str


class HttpProxySpeedTestResult(BaseModel):
    proxy_id: str
    url: str
    latency_ms: t.Optional[float]
    status: str


def normalize_proxy_url(raw: str, default_scheme: str = "http") -> t.Optional[str]:
    """把 user:pass@host:port 或 host:port 统一转换成 scheme://..."""
    raw = raw.strip()
    if not raw:
        return None
    # 已经是完整URL
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", raw):
        return raw
    match = _PROXY_URL_RE.match(raw)
    if not match:
        return None
    scheme = match.group("scheme") or default_scheme
    user = match.group("user") or ""
    passwd = match.group("passwd") or ""
    host = match.group("host")
    port = match.group("port")
    if user:
        auth = f"{user}:{passwd}@" if passwd else f"{user}@"
    else:
        auth = ""
    return f"{scheme}://{auth}{host}:{port}"


async def test_proxy_speed(url: str) -> t.Tuple[bool, t.Optional[float]]:
    """测试单个HTTP代理速度，返回 (是否成功, 延迟ms)"""
    start = time.time()
    try:
        async with httpx.AsyncClient(proxy=url) as client:
            resp = await client.get(_TEST_URL, timeout=_TEST_TIMEOUT)
        if resp.status_code < 300:
            return True, round((time.time() - start) * 1000, 2)
    except Exception:
        pass
    return False, None


@router.get("/http_proxies")
async def list_http_proxies():
    """列出所有HTTP代理"""
    return {"code": 0, "data": db.list_http_proxies()}


@router.post("/http_proxies")
async def add_http_proxy(request: HttpProxyAddRequest):
    """添加单个HTTP代理"""
    url = normalize_proxy_url(request.url)
    if url is None:
        return {"code": -400, "msg": "代理地址格式不正确"}
    return {"code": 0, "data": db.add_http_proxy(url, request.note)}


@router.post("/http_proxies/batch")
async def batch_add_http_proxies(request: HttpProxyBatchAddRequest):
    """批量添加HTTP代理"""
    scheme = request.scheme if request.scheme in ("http", "https", "socks5") else "http"
    normalized = []
    for raw in request.urls:
        url = normalize_proxy_url(raw, default_scheme=scheme)
        if url:
            normalized.append(url)
    if not normalized:
        return {"code": -400, "msg": "没有解析到有效的代理地址"}
    return {"code": 0, "data": db.add_http_proxies(normalized)}


@router.post("/http_proxies/test")
async def test_http_proxy_url(request: HttpProxyTestRequest):
    """测试任意代理地址（不保存）"""
    url = normalize_proxy_url(request.url)
    if url is None:
        return {"code": -400, "msg": "代理地址格式不正确"}
    success, latency = await test_proxy_speed(url)
    status = "ok" if success else "fail"
    return {
        "code": 0,
        "data": {
            "url": url,
            "latency_ms": latency,
            "status": status,
        },
    }


@router.delete("/http_proxies/{proxy_id}")
async def delete_http_proxy(proxy_id: UUID):
    """删除HTTP代理"""
    if db.delete_http_proxy_by_id(proxy_id):
        return {"code": 0, "data": True}
    raise HTTPException(status_code=404, detail="代理不存在")


@router.post("/http_proxies/{proxy_id}/test_speed")
async def test_http_proxy_speed(proxy_id: UUID):
    """测试单个HTTP代理速度"""
    model = db.get_http_proxy_by_id(proxy_id)
    if model is None:
        raise HTTPException(status_code=404, detail="代理不存在")
    success, latency = await test_proxy_speed(model.url)
    status = "ok" if success else "fail"
    db.update_http_proxy_status(proxy_id, latency, status)
    return {
        "code": 0,
        "data": {
            "proxy_id": str(model.proxy_id),
            "url": model.url,
            "latency_ms": latency,
            "status": status,
        },
    }


@router.post("/http_proxies/test_all")
async def test_all_http_proxies():
    """一键测试所有HTTP代理速度"""
    proxies = db.list_http_proxies()

    async def _test_one(proxy: dict) -> HttpProxySpeedTestResult:
        success, latency = await test_proxy_speed(proxy["url"])
        status = "ok" if success else "fail"
        db.update_http_proxy_status(proxy["proxy_id"], latency, status)
        return HttpProxySpeedTestResult(
            proxy_id=proxy["proxy_id"],
            url=proxy["url"],
            latency_ms=latency,
            status=status,
        )

    results = await asyncio.gather(*[_test_one(p) for p in proxies])
    return {
        "code": 0,
        "data": [r.model_dump() for r in results],
    }
