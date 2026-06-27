import asyncio
import base64
import time
import typing as t

from ..core.base import ProcessProtocol


class VesselProcess(ProcessProtocol):
    def __init__(
        self,
        vessel_call: t.Callable[..., t.Coroutine[t.Any, t.Any, t.Any]],
        shell_key: int,
    ):
        self._vessel_call = vessel_call
        self._shell_key = shell_key
        self._exitcode: t.Union[int, None] = None

    @property
    def pid(self) -> t.Union[int, str]:
        return self._shell_key

    async def send_signal(self, sig: int) -> None:
        await self._vessel_call(
            "child_shell_send_signal", self._shell_key, sig, timeout=5
        )

    async def write_stdin(self, data: bytes) -> None:
        await self._vessel_call(
            "child_shell_write_stdin",
            self._shell_key,
            base64.b64encode(data).decode(),
            timeout=5,
        )

    async def read_stdout_stderr(self) -> t.Tuple[bytes, bytes]:
        stdout_b64 = await self._vessel_call(
            "child_shell_read_stdout", self._shell_key, 1024 * 128, timeout=5
        )
        stderr_b64 = await self._vessel_call(
            "child_shell_read_stderr", self._shell_key, 1024 * 128, timeout=5
        )
        stdout = base64.b64decode(stdout_b64) if stdout_b64 else b""
        stderr = base64.b64decode(stderr_b64) if stderr_b64 else b""
        return stdout, stderr

    async def wait(self, timeout: float) -> t.Union[int, None]:
        if self._exitcode is not None:
            return self._exitcode
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            status = await self._vessel_call(
                "child_shell_get_status", self._shell_key, timeout=5
            )
            if not status.get("running", True):
                self._exitcode = status.get("exitcode", -1)
                await self._vessel_call("child_shell_exit", self._shell_key, timeout=5)
                return self._exitcode
            await asyncio.sleep(0.1)
        return None
