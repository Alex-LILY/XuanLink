"""WebShell 代码生成 API"""

import functools
import typing as t

from fastapi import APIRouter
from pydantic import BaseModel

from .. import core
from ..core import webshell_generator

router = APIRouter()


class GenerateWebshellRequest(BaseModel):
    webshell_type: str
    password: str
    key: t.Optional[str] = None


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
        except ValueError as exc:
            return {"code": -400, "msg": str(exc)}

    return _wraps


@router.post("/generate_webshell")
@catch_user_error
async def api_generate_webshell(request: GenerateWebshellRequest):
    """生成 WebShell 代码"""
    code = webshell_generator.generate_webshell(
        request.webshell_type, request.password, request.key
    )
    return {"code": 0, "data": code}


@router.get("/generate_webshell/types")
@catch_user_error
async def api_generate_webshell_types():
    """获取支持的 WebShell 生成类型"""
    return {
        "code": 0,
        "data": webshell_generator.WEBSHELL_GENERATOR_TYPES,
    }
