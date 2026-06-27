import asyncio
import base64
import pytest

from ether_ghost.sessions.linux_shell_helper import (
    LinuxShellHelper,
    shell_command,
    parse_file_permission,
    reverse_shell_payload,
    WRAPPER_CODE,
)


class TestShellCommand:
    def test_simple_args(self):
        assert shell_command(["echo", "hello"]) == "echo hello"

    def test_args_with_spaces(self):
        assert shell_command(["echo", "hello world"]) == "echo 'hello world'"

    def test_args_with_quotes(self):
        result = shell_command(["echo", "it's a test"])
        assert "echo" in result
        assert "test" in result

    def test_empty_list(self):
        assert shell_command([]) == ""

    def test_special_characters(self):
        result = shell_command(["sh", "-c", "echo hello && echo world"])
        assert "sh" in result
        assert "-c" in result


class TestParseFilePermission:
    def test_all_permissions(self):
        assert parse_file_permission("rwxrwxrwx") == "777"
        assert parse_file_permission("rwxr-xr-x") == "755"
        assert parse_file_permission("rw-r--r--") == "644"

    def test_no_permissions(self):
        assert parse_file_permission("---------") == "000"

    def test_mixed_permissions(self):
        assert parse_file_permission("r-xr--rwx") == "547"
        assert parse_file_permission("--x-w-r--") == "124"

    def test_read_only(self):
        assert parse_file_permission("r--r--r--") == "444"


class TestReverseShellPayload:
    def test_contains_host_and_port(self):
        payload = reverse_shell_payload("127.0.0.1", 4444)
        assert "127.0.0.1" not in payload
        decoded = base64.b64decode(payload.split()[1]).decode()
        assert "127.0.0.1" in decoded
        assert "4444" in decoded

    def test_is_base64_encoded(self):
        payload = reverse_shell_payload("10.0.0.1", 9999)
        parts = payload.split()
        assert parts[0] == "echo"
        base64.b64decode(parts[1])


class FakeTransport:
    def __init__(self, responses=None):
        self.calls = []
        self.responses = responses or {}

    async def __call__(self, code: str) -> str:
        self.calls.append(code)
        for key, value in self.responses.items():
            if key in code:
                return value
        return ""


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _make_echo_transport(echo_marker="MARKER"):
    async def transport(code: str) -> str:
        return f"\n{echo_marker}\n{echo_marker}\nfinished\nSTOPSTOPSTOPSTOP"

    return transport


class TestLinuxShellHelperSubmit:
    def test_submit_extracts_output(self):
        async def transport(code: str) -> str:
            start1 = ""
            start2 = ""
            stop = ""
            lines = code.strip().split("\n")
            for line in lines:
                if "echo -n" in line and '""' not in line:
                    parts = line.split('"')
                    if len(parts) >= 5:
                        start1 = parts[1]
                        start2 = parts[3]
                if line.strip().startswith("echo ") and '""' not in line:
                    last_quote = line.rfind('"')
                    if last_quote > 0:
                        second_last = line[:last_quote].rfind('"')
                        if second_last > 0:
                            stop = line[second_last + 1 : last_quote]

            return f"some noise\n{start1}{start2}hello world\n{stop}\nmore noise"

        helper = LinuxShellHelper(transport_fn=transport)
        result = run_async(helper.submit("echo hello world"))
        assert result == "hello world"

    def test_submit_with_list_payload(self):
        received_code = []

        async def transport(code: str) -> str:
            received_code.append(code)
            lines = code.strip().split("\n")
            start = ""
            stop = ""
            for line in lines:
                if "echo -n" in line:
                    parts = line.split('"')
                    if len(parts) >= 5:
                        start = parts[1] + parts[3]
                if line.strip().startswith("echo ") and stop == "":
                    parts = line.split('"')
                    if len(parts) >= 2:
                        stop = parts[-2]
            return f"{start}result data\n{stop}"

        helper = LinuxShellHelper(transport_fn=transport)
        result = run_async(helper.submit(["echo", "test"]))
        assert "result data" in result

    def test_submit_raises_on_missing_start_marker(self):
        from ether_ghost.core.exceptions import PayloadOutputError

        async def transport(code: str) -> str:
            return "no markers here"

        helper = LinuxShellHelper(transport_fn=transport)
        with pytest.raises(PayloadOutputError):
            run_async(helper.submit("echo test"))

    def test_submit_raises_on_missing_stop_marker(self):
        from ether_ghost.core.exceptions import PayloadOutputError

        async def transport(code: str) -> str:
            lines = code.strip().split("\n")
            start = ""
            for line in lines:
                if "echo -n" in line:
                    parts = line.split('"')
                    if len(parts) >= 5:
                        start = parts[1] + parts[3]
            return f"{start}some output without stop"

        helper = LinuxShellHelper(transport_fn=transport)
        with pytest.raises(PayloadOutputError):
            run_async(helper.submit("echo test"))


class TestLinuxShellHelperMethods:
    def test_execute_cmd(self):
        async def transport(code: str) -> str:
            lines = code.strip().split("\n")
            start = stop = ""
            for line in lines:
                if "echo -n" in line:
                    parts = line.split('"')
                    if len(parts) >= 5:
                        start = parts[1] + parts[3]
                if line.strip().startswith("echo ") and not stop:
                    parts = line.split('"')
                    if len(parts) >= 2:
                        stop = parts[-2]
            return f"{start}command output\n{stop}"

        helper = LinuxShellHelper(transport_fn=transport)
        result = run_async(helper.execute_cmd("ls"))
        assert "command output" in result

    def test_test_usablility_true(self):
        async def transport(code: str) -> str:
            lines = code.strip().split("\n")
            start = stop = ""
            for line in lines:
                if "echo -n" in line:
                    parts = line.split('"')
                    if len(parts) >= 5:
                        start = parts[1] + parts[3]
                if line.strip().startswith("echo ") and not stop:
                    parts = line.split('"')
                    if len(parts) >= 2:
                        stop = parts[-2]
            toprint = ""
            for part in code.split():
                if len(part) == 12 and part.isalnum():
                    toprint = part
                    break
            return f"{start}{toprint}\n{stop}"

        helper = LinuxShellHelper(transport_fn=transport)
        assert run_async(helper.test_usablility()) is True

    def test_get_pwd(self):
        async def transport(code: str) -> str:
            lines = code.strip().split("\n")
            start = stop = ""
            for line in lines:
                if "echo -n" in line:
                    parts = line.split('"')
                    if len(parts) >= 5:
                        start = parts[1] + parts[3]
                if line.strip().startswith("echo ") and not stop:
                    parts = line.split('"')
                    if len(parts) >= 2:
                        stop = parts[-2]
            return f"{start}/home/user\n{stop}"

        helper = LinuxShellHelper(transport_fn=transport)
        assert run_async(helper.get_pwd()) == "/home/user"

    def test_delete_file_success(self):
        async def transport(code: str) -> str:
            lines = code.strip().split("\n")
            start = stop = ""
            for line in lines:
                if "echo -n" in line:
                    parts = line.split('"')
                    if len(parts) >= 5:
                        start = parts[1] + parts[3]
                if line.strip().startswith("echo ") and not stop:
                    parts = line.split('"')
                    if len(parts) >= 2:
                        stop = parts[-2]
            if "finished" in code:
                return f"{start}finished\n{stop}"
            return f"{start}something\n{stop}"

        helper = LinuxShellHelper(transport_fn=transport)
        assert run_async(helper.delete_file("/tmp/test")) is True

    def test_list_dir_fallback(self):
        async def transport(code: str) -> str:
            lines = code.strip().split("\n")
            start = stop = ""
            for line in lines:
                if "echo -n" in line:
                    parts = line.split('"')
                    if len(parts) >= 5:
                        start = parts[1] + parts[3]
                if line.strip().startswith("echo ") and not stop:
                    parts = line.split('"')
                    if len(parts) >= 2:
                        stop = parts[-2]
            return f"{start}no finished marker\n{stop}"

        helper = LinuxShellHelper(transport_fn=transport)
        result = run_async(helper.list_dir("/tmp"))
        assert len(result) == 1
        assert result[0].name == ".."


class TestLinuxShellHelperEncoder:
    def test_base64_quote_encoder(self):
        async def transport(code: str) -> str:
            lines = code.strip().split("\n")
            start = stop = ""
            for line in lines:
                if "echo -n" in line:
                    parts = line.split('"')
                    if len(parts) >= 5:
                        start = parts[1] + parts[3]
                if line.strip().startswith("echo ") and not stop:
                    parts = line.split('"')
                    if len(parts) >= 2:
                        stop = parts[-2]
            return f"{start}encoded output\n{stop}"

        helper = LinuxShellHelper(transport_fn=transport, encoder="base64_quote")
        result = run_async(helper.submit("echo test"))
        assert "encoded output" in result

    def test_invalid_encoder_raises(self):
        from ether_ghost.core.exceptions import UserError

        async def transport(code: str) -> str:
            return ""

        helper = LinuxShellHelper(transport_fn=transport, encoder="invalid")
        with pytest.raises(UserError, match="未知encoder"):
            run_async(helper.submit("echo test"))


class TestLinuxShellHelperDecoder:
    def test_base64_decoder(self):
        async def transport(code: str) -> str:
            lines = code.strip().split("\n")
            start = stop = ""
            for line in lines:
                if "echo -n" in line:
                    parts = line.split('"')
                    if len(parts) >= 5:
                        start = parts[1] + parts[3]
                if line.strip().startswith("echo ") and not stop:
                    parts = line.split('"')
                    if len(parts) >= 2:
                        stop = parts[-2]
            output = base64.b64encode(b"decoded text").decode()
            return f"{start}{output}\n{stop}"

        helper = LinuxShellHelper(transport_fn=transport, decoder="base64")
        result = run_async(helper.submit("echo test"))
        assert result == "decoded text"

    def test_invalid_decoder_raises(self):
        from ether_ghost.core.exceptions import UserError

        async def transport(code: str) -> str:
            lines = code.strip().split("\n")
            start = stop = ""
            for line in lines:
                if "echo -n" in line:
                    parts = line.split('"')
                    if len(parts) >= 5:
                        start = parts[1] + parts[3]
                if line.strip().startswith("echo ") and not stop:
                    parts = line.split('"')
                    if len(parts) >= 2:
                        stop = parts[-2]
            return f"{start}data\n{stop}"

        helper = LinuxShellHelper(transport_fn=transport, decoder="invalid")
        with pytest.raises(UserError, match="未知Decoder"):
            run_async(helper.submit("echo test"))
