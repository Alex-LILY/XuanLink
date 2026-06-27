import asyncio
import base64
import shlex
import typing as t


class LinuxCmdProcess:
    """通过 Linux Shell 模拟的异步进程对象

    配合 LinuxShellHelper 使用，目标系统通过命名管道（fifo）和临时目录
    实现 stdin/stdout/stderr 的读写以及退出码获取。
    """

    def __init__(
        self,
        pid: t.Union[int, str],
        proc_dir: str,
        submit_fn: t.Callable[[str], t.Awaitable[str]],
    ):
        self._pid = pid
        self._proc_dir = proc_dir
        self._submit_fn = submit_fn

    @property
    def pid(self) -> t.Union[int, str]:
        return self._pid

    async def send_signal(self, sig: int) -> None:
        """向进程发送信号"""
        await self._submit_fn(f"kill -{sig} {self._pid}")

    async def write_stdin(self, data: bytes) -> None:
        """向进程标准输入写入数据"""
        data_b64 = base64.b64encode(data).decode()
        stdin_path = shlex.quote(f"{self._proc_dir}/stdin")
        await self._submit_fn(
            f"printf '%s' {data_b64} | base64 -d > {stdin_path}"
        )

    async def read_stdout_stderr(self) -> t.Tuple[bytes, bytes]:
        """读取进程的 stdout 和 stderr"""
        stdout_path = shlex.quote(f"{self._proc_dir}/stdout")
        stderr_path = shlex.quote(f"{self._proc_dir}/stderr")
        stdout_b64 = await self._submit_fn(f"cat {stdout_path} | base64 -w0")
        stderr_b64 = await self._submit_fn(f"cat {stderr_path} | base64 -w0")
        return base64.b64decode(stdout_b64), base64.b64decode(stderr_b64)

    async def wait(self, timeout: float) -> t.Union[int, None]:
        """等待进程结束，超时返回 None"""
        rc_path = shlex.quote(f"{self._proc_dir}/rc")

        async def _poll() -> int:
            while True:
                rc = (
                    await self._submit_fn(
                        f"test -f {rc_path} && cat {rc_path} || echo ''"
                    )
                ).strip()
                if rc:
                    return int(rc)
                await asyncio.sleep(0.2)

        try:
            return await asyncio.wait_for(_poll(), timeout=timeout)
        except asyncio.TimeoutError:
            return None
