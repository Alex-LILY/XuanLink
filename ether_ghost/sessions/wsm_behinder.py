import base64
import typing as t
import logging

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
from ..wsm_behinder_core import BehinderClient

logger = logging.getLogger("core.sessions.wsm_behinder")


def _common_options() -> t.List[OptionGroup]:
    return [
        {
            "name": "Basic Connection Config",
            "options": [
                Option(
                    id="url",
                    name="URL",
                    type="text",
                    placeholder="http://xxx.com/shell.jsp",
                    default_value=None,
                    alternatives=None,
                ),
                Option(
                    id="password",
                    name="Password",
                    type="text",
                    placeholder="rebeyond",
                    default_value="rebeyond",
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


class BehinderSessionBase(SessionInterface):
    script: t.ClassVar[str]
    mode: t.ClassVar[int]

    def __init__(self, session_conn: dict):
        self.url = session_conn["url"]
        self.password = session_conn.get("password", "rebeyond")
        self.proxy = session_conn.get("proxy") or None
        self.verify = session_conn.get("https_verify", False)
        self.client = BehinderClient(
            url=self.url,
            password=self.password,
            script=self.script,
            mode=self.mode,
            proxy=self.proxy,
            verify=self.verify,
        )

    async def test_usablility(self) -> bool:
        try:
            return await self.client.ping()
        except Exception as exc:
            logger.debug("Behinder ping failed: %s", exc)
            return False

    async def get_basicinfo(self) -> t.List[BasicInfoEntry]:
        info = await self.client.basicinfo()
        mapping = {
            "Current Directory": "currentPath",
            "Drive List": "driveList",
            "System Info": "osInfo",
            "Arch": "arch",
            "Basic Info": "basicInfo",
        }
        # 优先显示已知字段，再追加其它字段
        result: t.List[BasicInfoEntry] = []
        for label, key in mapping.items():
            if key in info:
                result.append(BasicInfoEntry(key=label, value=info[key]))
        for key, value in info.items():
            if key not in mapping.values() and key != "raw":
                result.append(BasicInfoEntry(key=key, value=value))
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
            return mapping[head_lower] + tail
        return cmd

    async def execute_cmd(self, cmd: str) -> str:
        return await self.client.exec_command(self._translate_cmd(cmd))

    async def list_dir(self, dir_path: str) -> t.List[DirectoryEntry]:
        result = await self.client.list_dir(dir_path)
        raw = result.get("msg", "")
        entries: t.List[DirectoryEntry] = []
        try:
            import json

            for item in json.loads(raw):
                name = base64.b64decode(item["name"]).decode("utf-8", errors="replace")
                entry_type = base64.b64decode(item["type"]).decode("utf-8", errors="replace")
                size = base64.b64decode(item.get("size", "MA==")).decode("utf-8", errors="replace")
                perm = base64.b64decode(item.get("perm", "")).decode("utf-8", errors="replace")
                entries.append(
                    DirectoryEntry(
                        name=name,
                        entry_type="dir" if entry_type == "directory" else "file",  # type: ignore
                        filesize=int(size or 0),
                        permission=perm,
                    )
                )
        except Exception as exc:
            logger.debug("Behinder list_dir parse failed: %s", exc)
        return entries

    async def get_file_contents(self, filepath: str, max_size: int = 1024 * 200) -> bytes:
        data = await self.client.read_file(filepath)
        if isinstance(data, dict):
            data = data.get("msg", "").encode("utf-8", errors="replace")
        if len(data) > max_size:
            raise exceptions.UserError("文件超过最大读取大小")
        return data

    async def put_file_contents(self, filepath: str, content: bytes) -> bool:
        return await self.client.write_file(filepath, content)

    async def delete_file(self, filepath: str) -> bool:
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
        return await self.put_file_contents(filepath, content)

    async def download_file(
        self, filepath: str, callback: t.Union[t.Callable, None] = None
    ) -> bytes:
        return await self.get_file_contents(filepath)

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
        info = await self.client.basicinfo()
        return info.get("currentDir", "")

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


@register_session
class JSPWebshellBehinderAES(BehinderSessionBase):
    session_type = "BEHINDER_JSP_AES"
    readable_name = "Behinder JSP AES"
    script = "jsp"
    mode = 0
    conn_options = _common_options()


@register_session
class JSPXWebshellBehinderAES(BehinderSessionBase):
    session_type = "BEHINDER_JSPX_AES"
    readable_name = "Behinder JSPX AES"
    script = "jspx"
    mode = 0
    conn_options = _common_options()


@register_session
class ASPWebshellBehinderXor(BehinderSessionBase):
    session_type = "BEHINDER_ASP_XOR"
    readable_name = "Behinder ASP XOR"
    script = "asp"
    mode = 1
    conn_options = _common_options()


@register_session
class ASPXWebshellBehinderAES(BehinderSessionBase):
    session_type = "BEHINDER_ASPX_AES"
    readable_name = "Behinder ASPX AES"
    script = "aspx"
    mode = 0
    conn_options = _common_options()
