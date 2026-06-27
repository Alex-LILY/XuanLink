import base64
import hashlib
import hmac as _hmac
import secrets
import struct
import time
import typing as t
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from .. import auth
from ..utils import db

router = APIRouter(prefix="/api/auth")


# ── TOTP (no external deps) ──────────────────────────────────────────────────

def _b32_decode(secret: str) -> bytes:
    pad = (8 - len(secret) % 8) % 8
    return base64.b32decode(secret.upper() + "=" * pad)


def generate_otp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def verify_totp(secret: str, code: str, window: int = 1) -> bool:
    try:
        key = _b32_decode(secret)
    except Exception:
        return False
    current = int(time.time()) // 30
    for delta in range(-window, window + 1):
        msg = struct.pack(">Q", current + delta)
        h = _hmac.new(key, msg, hashlib.sha1).digest()
        offset = h[-1] & 0x0F
        val = struct.unpack(">I", h[offset:offset + 4])[0] & 0x7FFFFFFF
        expected = str(val % 1_000_000).zfill(6)
        if secrets.compare_digest(code.strip(), expected):
            return True
    return False


def get_totp_uri(secret: str) -> str:
    return (
        f"otpauth://totp/{quote('EtherGhost')}:admin"
        f"?secret={secret}&issuer={quote('EtherGhost')}&algorithm=SHA1&digits=6&period=30"
    )


# ── Pydantic models ───────────────────────────────────────────────────────────

class LoginReq(BaseModel):
    username: str
    password: str
    otp_code: t.Optional[str] = None


class ChangePasswordReq(BaseModel):
    old_password: str
    new_password: str


class OtpEnableReq(BaseModel):
    secret: str
    otp_code: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _require_token(request: Request) -> str:
    # Check cookie first, then Bearer header
    token = request.cookies.get("ghost_token")
    if not token:
        h = request.headers.get("Authorization", "")
        if h.startswith("Bearer "):
            token = h[7:]
    if token and auth.validate_token(token):
        return token
    raise HTTPException(status_code=401, detail="Unauthorized")


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/status")
async def get_status():
    """Public endpoint – used by login page to know if OTP is required."""
    cfg = db.get_auth_config()
    return {
        "code": 0,
        "data": {
            "otp_enabled": cfg["otp_enabled"] if cfg else False,
            "needs_password_change": cfg["needs_password_change"] if cfg else False,
        },
    }


@router.post("/login")
async def login(req: LoginReq, response: Response):
    cfg = db.get_auth_config()
    if cfg is None:
        raise HTTPException(400, "Auth not configured")

    if req.username != "admin":
        raise HTTPException(401, "用户名或密码错误")

    if not auth.verify_password(req.password, cfg["salt"], cfg["password_hash"]):
        raise HTTPException(401, "用户名或密码错误")

    if cfg["otp_enabled"] and cfg["otp_secret"]:
        if not req.otp_code:
            raise HTTPException(422, "需要OTP验证码")
        if not verify_totp(cfg["otp_secret"], req.otp_code):
            raise HTTPException(401, "OTP验证码错误")

    token = auth.create_token()
    response.set_cookie(
        key="ghost_token",
        value=token,
        max_age=auth.TOKEN_TTL,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return {
        "code": 0,
        "data": {
            "token": token,
            "needs_password_change": cfg["needs_password_change"],
        },
    }


@router.post("/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get("ghost_token")
    if not token:
        h = request.headers.get("Authorization", "")
        if h.startswith("Bearer "):
            token = h[7:]
    if token:
        auth.revoke_token(token)
    response.delete_cookie("ghost_token", path="/")
    return {"code": 0, "data": True}


@router.post("/change_password")
async def change_password(req: ChangePasswordReq, request: Request):
    _require_token(request)
    cfg = db.get_auth_config()
    if not auth.verify_password(req.old_password, cfg["salt"], cfg["password_hash"]):
        raise HTTPException(401, "原密码错误")
    if len(req.new_password) < 6:
        raise HTTPException(400, "新密码至少需要6位")
    new_salt = secrets.token_hex(16)
    new_hash = auth.hash_password(req.new_password, new_salt)
    db.set_auth_config(
        password_hash=new_hash,
        salt=new_salt,
        needs_password_change=False,
        otp_enabled=cfg["otp_enabled"],
        otp_secret=cfg["otp_secret"],
    )
    return {"code": 0, "data": True}


@router.get("/otp_setup")
async def get_otp_setup(request: Request):
    _require_token(request)
    cfg = db.get_auth_config()
    secret = cfg["otp_secret"] or generate_otp_secret()
    # Always persist the (possibly freshly generated) secret so it survives page reload
    if not cfg["otp_secret"]:
        db.set_auth_config(
            password_hash=cfg["password_hash"],
            salt=cfg["salt"],
            needs_password_change=cfg["needs_password_change"],
            otp_enabled=cfg["otp_enabled"],
            otp_secret=secret,
        )
    return {
        "code": 0,
        "data": {
            "secret": secret,
            "uri": get_totp_uri(secret),
            "otp_enabled": cfg["otp_enabled"],
        },
    }


@router.post("/otp_enable")
async def otp_enable(req: OtpEnableReq, request: Request):
    _require_token(request)
    cfg = db.get_auth_config()
    if not verify_totp(req.secret, req.otp_code):
        raise HTTPException(401, "OTP验证码错误，请确认已添加到验证器应用")
    db.set_auth_config(
        password_hash=cfg["password_hash"],
        salt=cfg["salt"],
        needs_password_change=cfg["needs_password_change"],
        otp_enabled=True,
        otp_secret=req.secret,
    )
    return {"code": 0, "data": True}


@router.post("/otp_disable")
async def otp_disable(request: Request):
    _require_token(request)
    cfg = db.get_auth_config()
    db.set_auth_config(
        password_hash=cfg["password_hash"],
        salt=cfg["salt"],
        needs_password_change=cfg["needs_password_change"],
        otp_enabled=False,
        otp_secret=cfg["otp_secret"],
    )
    return {"code": 0, "data": True}
