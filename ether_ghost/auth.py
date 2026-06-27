import hashlib
import secrets
import time
import typing as t

from fastapi import Depends, HTTPException, Request

from .utils import db

_active_tokens: t.Dict[str, float] = {}
TOKEN_TTL = 86400  # 24 hours


def hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000).hex()


def verify_password(password: str, salt: str, stored_hash: str) -> bool:
    return secrets.compare_digest(hash_password(password, salt), stored_hash)


def create_token() -> str:
    token = secrets.token_hex(32)
    _active_tokens[token] = time.time() + TOKEN_TTL
    return token


def revoke_token(token: str):
    _active_tokens.pop(token, None)


def validate_token(token: str) -> bool:
    expiry = _active_tokens.get(token)
    if expiry is None:
        return False
    if time.time() > expiry:
        _active_tokens.pop(token, None)
        return False
    return True


def _extract_token(request: Request) -> t.Optional[str]:
    """Extract token from cookie or Authorization header."""
    token = request.cookies.get("ghost_token")
    if token:
        return token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    return None


async def require_auth(request: Request):
    token = _extract_token(request)
    if token and validate_token(token):
        return
    raise HTTPException(status_code=401, detail="Unauthorized")
