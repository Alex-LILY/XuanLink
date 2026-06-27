import asyncio
import typing as t
import logging
import uuid
import os
import tempfile
import shlex
import base64
from urllib.parse import urlencode

from ..core import exceptions

from ..core.base import (
    register_session,
    Option,
    OptionGroup,
    HttpResponseDict,
)

from .linux_cmd_process import LinuxCmdProcess
from .linux_shell_helper import LinuxShellHelper, shell_command

logger = logging.getLogger("core.sessions.ssh")

SSH_SESSION_TYPE = "SSH"


@register_session
class SSHSession:
    session_type = SSH_SESSION_TYPE
    readable_name = "SSH"
    conn_options: t.List[OptionGroup] = [
        {
            "name": "Connection Config",
            "options": [
                Option(
                    id="host",
                    name="Host",
                    type="text",
                    placeholder="SSH host address",
                    default_value=None,
                    alternatives=None,
                ),
                Option(
                    id="port",
                    name="Port",
                    type="text",
                    placeholder="22",
                    default_value="22",
                    alternatives=None,
                ),
                Option(
                    id="username",
                    name="Username",
                    type="text",
                    placeholder="SSH username",
                    default_value=None,
                    alternatives=None,
                ),
                Option(
                    id="password",
                    name="Password",
                    type="text",
                    placeholder="SSH password",
                    default_value=None,
                    alternatives=None,
                ),
            ],
        },
        {
            "name": "Advanced Connection Config",
            "options": [
                Option(
                    id="chunk_size",
                    name="Upload/Download Chunk Size",
                    type="text",
                    placeholder="Chunk size in bytes, recommended 1KB-1024KB",
                    default_value="1024",
                    alternatives=None,
                ),
                Option(
                    id="encoder",
                    name="Command Encoder",
                    type="select",
                    placeholder="raw",
                    default_value="raw",
                    alternatives=[
                        {"name": "raw", "value": "raw"},
                        {"name": "base64_quote", "value": "base64_quote"},
                        {"name": "base64_ifs", "value": "base64_ifs"},
                    ],
                ),
                Option(
                    id="decoder",
                    name="Decoder",
                    type="select",
                    placeholder="raw",
                    default_value="raw",
                    alternatives=[
                        {"name": "raw", "value": "raw"},
                        {"name": "base64", "value": "base64"},
                    ],
                ),
            ],
        },
    ]

    def __init__(self, config: dict):
        self.host = str(config["host"])
        self.port = int(config.get("port", 22))
        self.username = str(config["username"])
        self.password = str(config["password"])
        self.encoder = str(config.get("encoder", "raw"))
        self.decoder = str(config.get("decoder", "raw"))
        self.chunk_size = int(config.get("chunk_size", 1024))

        self._proc: t.Union[asyncio.subprocess.Process, None] = None
        self._askpass_path: t.Union[str, None] = None
        self.lock = asyncio.Lock()

        self._shell = LinuxShellHelper(
            transport_fn=self._transport,
            encoder=self.encoder,
            decoder=self.decoder,
            chunk_size=self.chunk_size,
            max_coro=None,
        )

    async def _ensure_connected(self):
        if self._proc is not None:
            if self._proc.returncode is not None:
                raise exceptions.NetworkError("SSH连接已断开")
            return

        askpass_fd, askpass_path = tempfile.mkstemp(suffix="_askpass.sh")
        with os.fdopen(askpass_fd, "w") as f:
            f.write(f"#!/bin/sh\necho {shlex.quote(self.password)}\n")
        os.chmod(askpass_path, 0o755)
        self._askpass_path = askpass_path

        env = os.environ.copy()
        env["SSH_ASKPASS"] = askpass_path
        env["SSH_ASKPASS_REQUIRE"] = "force"
        env["DISPLAY"] = ":0"

        self._proc = await asyncio.create_subprocess_exec(
            "ssh",
            "-T",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-o",
            "LogLevel=ERROR",
            "-p",
            str(self.port),
            f"{self.username}@{self.host}",
            "bash",
            "--norc",
            "--noprofile",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            env=env,
            start_new_session=True,
        )

    async def submit_ssh(self, payload: t.Union[str, bytes]) -> str:
        await self._ensure_connected()
        command_end_marker = str(uuid.uuid4())
        async with self.lock:
            if (
                self._proc is None
                or self._proc.stdin is None
                or self._proc.stdout is None
            ):
                raise exceptions.NetworkError("SSH连接不可用")
            if isinstance(payload, str):
                payload = payload.encode()
            self._proc.stdin.write(payload + b"\n")
            self._proc.stdin.write(f"echo {command_end_marker}\n".encode())
            await self._proc.stdin.drain()
            data = await self._proc.stdout.readuntil(
                separator=command_end_marker.encode()
            )
            return data.decode()

    async def _transport(self, code: str) -> str:
        return await self.submit_ssh(code)

    async def execute_cmd(self, cmd: str):
        return await self._shell.execute_cmd(cmd)

    async def test_usablility(self):
        return await self._shell.test_usablility()

    async def get_pwd(self):
        return await self._shell.get_pwd()

    async def list_dir(self, dir_path: str):
        return await self._shell.list_dir(dir_path)

    async def mkdir(self, dir_path: str):
        return await self._shell.mkdir(dir_path)

    async def get_file_contents(self, filepath: str, max_size: int = 1024 * 200):
        return await self._shell.get_file_contents(filepath, max_size)

    async def put_file_contents(self, filepath: str, content: bytes):
        return await self._shell.put_file_contents(filepath, content)

    async def modify_file(
        self,
        filepath: str,
        old_str: str,
        new_str: str,
        replace_strategy: t.Union[str, None] = None,
    ) -> None:
        return await self._shell.modify_file(
            filepath, old_str, new_str, replace_strategy
        )

    async def delete_file(self, filepath: str):
        return await self._shell.delete_file(filepath)

    async def move_file(self, filepath: str, new_filepath: str):
        return await self._shell.move_file(filepath, new_filepath)

    async def copy_file(self, filepath: str, new_filepath: str):
        return await self._shell.copy_file(filepath, new_filepath)

    async def chmod(self, filepath: str, mode: str):
        return await self._shell.chmod(filepath, mode)

    async def upload_file(
        self, filepath: str, content: bytes, callback: t.Union[t.Callable, None] = None
    ) -> bool:
        return await self._shell.upload_file(filepath, content, callback)

    async def download_file(self, filepath: str, callback=None):
        return await self._shell.download_file(filepath, callback)

    async def create_process(
        self,
        argv: t.List[str],
        overrides_env: t.Union[t.Dict[str, str], None] = None,
    ) -> LinuxCmdProcess:
        proc_dir = (await self._shell.submit("mktemp -d")).strip()
        await self._shell.submit(f"mkfifo {shlex.quote(proc_dir + '/stdin')}")

        env_prefix = ""
        if overrides_env:
            env_parts = ["env"] + [
                f"{shlex.quote(k)}={shlex.quote(v)}" for k, v in overrides_env.items()
            ]
            env_prefix = " ".join(env_parts) + " "

        cmd = shell_command(argv)
        stdin_path = shlex.quote(f"{proc_dir}/stdin")
        stdout_path = shlex.quote(f"{proc_dir}/stdout")
        stderr_path = shlex.quote(f"{proc_dir}/stderr")
        rc_path = shlex.quote(f"{proc_dir}/rc")

        setup_cmd = (
            f"(exec 0<>{stdin_path}; exec 1>{stdout_path}; "
            f"exec 2>{stderr_path}; {env_prefix}{cmd}; "
            f"echo $? > {rc_path}) & echo $!"
        )

        output = (await self._shell.submit(setup_cmd)).strip()
        pid = output.strip()

        return LinuxCmdProcess(pid=pid, proc_dir=proc_dir, submit_fn=self._shell.submit)

    async def send_bytes_over_tcp(
        self,
        host: str,
        port: int,
        content: bytes,
        send_method: t.Union[str, None] = None,
    ) -> t.Union[bytes, None]:
        return await self._shell.send_bytes_over_tcp(host, port, content, send_method)

    async def get_send_tcp_support_methods(self) -> t.List[str]:
        return await self._shell.get_send_tcp_support_methods()

    async def get_basicinfo(self):
        return await self._shell.get_basicinfo()

    async def send_http_request(
        self,
        url: str,
        method: str = "GET",
        headers: t.Optional[t.Dict[str, str]] = None,
        params: t.Optional[t.Dict[str, t.Any]] = None,
        data: t.Optional[t.Union[str, bytes]] = None,
    ) -> HttpResponseDict:
        curl_check = await self._shell.submit("which curl")
        if not curl_check.strip():
            raise exceptions.TargetError("目标系统未安装curl命令")

        cmd_parts = ["curl", "-s", "-i"]
        cmd_parts.extend(["-X", method])

        if headers:
            for key, value in headers.items():
                cmd_parts.extend(["-H", f"{key}: {value}"])

        full_url = url
        if params:
            full_url = f"{url}?{urlencode(params)}"

        if data is not None:
            if isinstance(data, bytes):
                data_str = base64.b64encode(data).decode()
                cmd_parts.extend(["--data", data_str])
            else:
                cmd_parts.extend(["--data", data])

        cmd_parts.append(full_url)
        cmd_str = " ".join(shlex.quote(part) for part in cmd_parts)
        output = await self._shell.submit(cmd_str)

        lines = output.splitlines()
        if not lines:
            raise exceptions.NetworkError("HTTP请求无响应")

        status_line = lines[0]
        if not status_line.startswith("HTTP/"):
            raise exceptions.NetworkError(f"无效的HTTP响应: {status_line}")
        status_parts = status_line.split()
        if len(status_parts) < 2:
            raise exceptions.NetworkError(f"无法解析状态码: {status_line}")
        status_code = int(status_parts[1])

        headers_dict: t.Dict[str, str] = {}
        body_lines: t.List[str] = []
        in_body = False
        for line in lines[1:]:
            if not in_body:
                if line.strip() == "":
                    in_body = True
                    continue
                if ":" in line:
                    key, value = line.split(":", 1)
                    headers_dict[key.strip()] = value.strip()
            else:
                body_lines.append(line)

        body = "\n".join(body_lines)
        return HttpResponseDict(
            status_code=status_code,
            headers=headers_dict,
            body=body.encode() if body else b"",
        )
