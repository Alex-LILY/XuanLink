import asyncio
import unittest

from ether_ghost.core.base import ProcessProtocol, SessionInterface


class FakeSession(SessionInterface):
    def __init__(self):
        self._pwd = "/tmp"

    async def execute_cmd(self, cmd: str, timeout: float = 5) -> str:
        return ""

    async def list_dir(self, path: str) -> str:
        return ""

    async def download_file(self, remote_path: str, local_path: str) -> None:
        pass

    async def upload_file(self, local_path: str, remote_path: str) -> None:
        pass

    async def get_pwd(self) -> str:
        return self._pwd


class TestProcessProtocol(unittest.TestCase):
    def test_protocol_has_pid(self):
        self.assertTrue(hasattr(ProcessProtocol, "pid"))

    def test_protocol_has_send_signal(self):
        self.assertTrue(hasattr(ProcessProtocol, "send_signal"))

    def test_protocol_has_write_stdin(self):
        self.assertTrue(hasattr(ProcessProtocol, "write_stdin"))

    def test_protocol_has_read_stdout_stderr(self):
        self.assertTrue(hasattr(ProcessProtocol, "read_stdout_stderr"))

    def test_protocol_has_wait(self):
        self.assertTrue(hasattr(ProcessProtocol, "wait"))


class TestSessionInterfaceCreateProcess(unittest.TestCase):
    def test_create_process_default_raises(self):
        session = FakeSession()
        with self.assertRaises(NotImplementedError):
            asyncio.get_event_loop().run_until_complete(session.create_process(["ls"]))

    def test_create_process_accepts_overrides_env(self):
        session = FakeSession()
        with self.assertRaises(NotImplementedError):
            asyncio.get_event_loop().run_until_complete(
                session.create_process(["ls"], {"PATH": "/usr/bin"})
            )


class TestLinuxCmdCreateProcess(unittest.TestCase):
    def test_linux_cmd_process_implements_protocol(self):
        from ether_ghost.sessions.linux_cmd_oneliner import LinuxCmdProcess

        process = LinuxCmdProcess(pid="1", proc_dir="/tmp", submit_fn=lambda: None)
        self.assertIsInstance(process.pid, str)
        self.assertTrue(callable(process.send_signal))
        self.assertTrue(callable(process.write_stdin))
        self.assertTrue(callable(process.read_stdout_stderr))
        self.assertTrue(callable(process.wait))


class TestJSPCreateProcess(unittest.TestCase):
    def test_jsp_create_process_not_implemented(self):
        from ether_ghost.sessions.jsp_behinder import JSPWebshellBehinderAES

        jsp = JSPWebshellBehinderAES.__new__(JSPWebshellBehinderAES)
        with self.assertRaises(NotImplementedError) as ctx:
            asyncio.get_event_loop().run_until_complete(jsp.create_process(["ls"]))
        self.assertIn("JSP", str(ctx.exception))


class TestReverseShellCreateProcess(unittest.TestCase):
    def test_reverse_shell_create_process_not_implemented(self):
        from ether_ghost.sessions.reverse_shell import ReverseShellSession

        rs = ReverseShellSession.__new__(ReverseShellSession)
        with self.assertRaises(NotImplementedError) as ctx:
            asyncio.get_event_loop().run_until_complete(rs.create_process(["ls"]))
        self.assertIn("反弹Shell", str(ctx.exception))
