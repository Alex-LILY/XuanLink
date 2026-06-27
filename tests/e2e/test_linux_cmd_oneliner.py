import base64
import os
import shutil
import subprocess
import sys
import time
import uuid
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import httpx
import pytest

BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 18024
PHP_HOST = "127.0.0.1"
PHP_PORT = 19998
BACKEND_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"
PHP_URL = f"http://{PHP_HOST}:{PHP_PORT}"
TEST_ENV_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "test_environment")
)

TARGET_HOST = "127.0.0.1"
TARGET_PORT = 18097
TARGET_URL = f"http://{TARGET_HOST}:{TARGET_PORT}"
TARGET_RESPONSE_BODY = "hello from target server"


class TargetHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("X-Test-Header", "test-value")
        self.end_headers()
        self.wfile.write(TARGET_RESPONSE_BODY.encode())

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b""
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


@pytest.fixture(scope="module")
def php_server():
    assert shutil.which("php") is not None, "PHP is required for e2e tests"
    proc = subprocess.Popen(
        ["php", "-S", f"{PHP_HOST}:{PHP_PORT}", "-t", TEST_ENV_DIR],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "LC_ALL": "C", "LANG": "C"},
    )
    started = False
    for _ in range(50):
        time.sleep(0.1)
        try:
            resp = httpx.post(f"{PHP_URL}/cmd.php", data={"data": "echo test"})
            if resp.status_code == 200:
                started = True
                break
        except httpx.ConnectError:
            continue
    if not started:
        proc.terminate()
        proc.wait()
        pytest.fail("PHP server failed to start")
    yield proc
    proc.terminate()
    proc.wait()


@pytest.fixture(scope="module")
def backend_server():
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "ether_ghost",
            "--host",
            BACKEND_HOST,
            "--port",
            str(BACKEND_PORT),
            "--no-browser",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    started = False
    for _ in range(100):
        time.sleep(0.1)
        try:
            resp = httpx.get(f"{BACKEND_URL}/session")
            if resp.status_code == 200:
                started = True
                break
        except httpx.ConnectError:
            continue
    if not started:
        stdout = proc.stdout.read() if proc.stdout else b""
        stderr = proc.stderr.read() if proc.stderr else b""
        proc.terminate()
        proc.wait()
        pytest.fail(
            f"Backend failed to start.\nstdout: {stdout.decode()}\nstderr: {stderr.decode()}"
        )
    yield proc
    proc.terminate()
    proc.wait()


@pytest.fixture(scope="module")
def target_server():
    server = HTTPServer((TARGET_HOST, TARGET_PORT), TargetHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()


@pytest.fixture(scope="module")
def session_id(php_server, backend_server):
    sid = str(uuid.uuid4())
    resp = httpx.post(
        f"{BACKEND_URL}/update_webshell",
        json={
            "session_type": "LINUX_CMD_ONELINER",
            "name": "e2e_linux_cmd_test",
            "connection": {
                "url": f"{PHP_URL}/cmd.php",
                "password": "data",
                "password_method": "POST",
            },
            "session_id": sid,
            "note": "e2e linux cmd test",
            "location": "",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["code"] == 0
    yield sid
    httpx.delete(f"{BACKEND_URL}/session/{sid}")


@pytest.fixture(scope="module")
def test_dir():
    path = f"/tmp/eg_e2e_linux_{uuid.uuid4().hex[:8]}"
    os.makedirs(path)
    yield path
    shutil.rmtree(path, ignore_errors=True)


def test_cmd_oneliner_usability(session_id):
    resp = httpx.post(
        f"{BACKEND_URL}/test_webshell",
        json={
            "session_type": "LINUX_CMD_ONELINER",
            "name": "e2e_linux_cmd_test",
            "connection": {
                "url": f"{PHP_URL}/cmd.php",
                "password": "data",
                "password_method": "POST",
            },
            "session_id": session_id,
            "note": "",
            "location": "",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["success"] is True


def test_execute_cmd(session_id):
    resp = httpx.get(
        f"{BACKEND_URL}/session/{session_id}/execute_cmd",
        params={"cmd": "echo hello_world"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert "hello_world" in data["data"]


def test_get_pwd(session_id):
    resp = httpx.get(f"{BACKEND_URL}/session/{session_id}/get_pwd")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert isinstance(data["data"], str)
    assert len(data["data"]) > 0


def test_list_dir(session_id, test_dir):
    marker_file = f"{test_dir}/list_marker.txt"
    with open(marker_file, "w") as f:
        f.write("list test")

    resp = httpx.get(
        f"{BACKEND_URL}/session/{session_id}/list_dir",
        params={"current_dir": test_dir},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    entries = data["data"]
    assert isinstance(entries, list)
    assert len(entries) > 0
    assert all("name" in e and "permission" in e for e in entries)


def test_mkdir(session_id, test_dir):
    new_dir = f"{test_dir}/subdir_mkdir"
    resp = httpx.get(
        f"{BACKEND_URL}/session/{session_id}/mkdir",
        params={"dirpath": new_dir},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert os.path.isdir(new_dir)


def test_put_and_get_file_contents(session_id, test_dir):
    content = f"hello e2e linux {uuid.uuid4().hex[:8]}"
    put_resp = httpx.post(
        f"{BACKEND_URL}/session/{session_id}/put_file_contents",
        json={
            "current_dir": test_dir,
            "filename": "test_rw.txt",
            "text": content,
            "encoding": "utf-8",
        },
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["code"] == 0

    get_resp = httpx.get(
        f"{BACKEND_URL}/session/{session_id}/get_file_contents",
        params={"current_dir": test_dir, "filename": "test_rw.txt"},
    )
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["code"] == 0
    assert data["data"]["text"] == content


def test_delete_file(session_id, test_dir):
    filepath = f"{test_dir}/test_delete.txt"
    with open(filepath, "w") as f:
        f.write("to be deleted")
    assert os.path.exists(filepath)

    resp = httpx.get(
        f"{BACKEND_URL}/session/{session_id}/delete_file",
        params={"current_dir": test_dir, "filename": "test_delete.txt"},
    )
    assert resp.status_code == 200
    assert resp.json()["code"] == 0
    assert not os.path.exists(filepath)


def test_move_file(session_id, test_dir):
    src = f"{test_dir}/test_move_src.txt"
    dst = f"{test_dir}/test_move_dst.txt"
    with open(src, "w") as f:
        f.write("move me")

    resp = httpx.get(
        f"{BACKEND_URL}/session/{session_id}/move_file",
        params={"filepath": src, "new_filepath": dst},
    )
    assert resp.status_code == 200
    assert resp.json()["code"] == 0
    assert not os.path.exists(src)
    assert os.path.exists(dst)
    with open(dst) as f:
        assert f.read() == "move me"


def test_copy_file(session_id, test_dir):
    src = f"{test_dir}/test_copy_src.txt"
    dst = f"{test_dir}/test_copy_dst.txt"
    content = "copy me"
    with open(src, "w") as f:
        f.write(content)

    resp = httpx.get(
        f"{BACKEND_URL}/session/{session_id}/copy_file",
        params={"filepath": src, "new_filepath": dst},
    )
    assert resp.status_code == 200
    assert resp.json()["code"] == 0
    assert os.path.exists(src)
    assert os.path.exists(dst)
    with open(dst) as f:
        assert f.read() == content


def test_upload_file(session_id, test_dir):
    content = f"upload test {uuid.uuid4().hex[:8]}"
    resp = httpx.post(
        f"{BACKEND_URL}/session/{session_id}/upload_file",
        files={"file": ("test_upload.txt", content.encode(), "text/plain")},
        data={"folder": test_dir},
    )
    assert resp.status_code == 200
    assert resp.json()["code"] == 0
    uploaded_path = f"{test_dir}/test_upload.txt"
    assert os.path.exists(uploaded_path)
    with open(uploaded_path) as f:
        assert f.read() == content


def test_download_file(session_id, test_dir):
    content = f"download test {uuid.uuid4().hex[:8]}"
    filepath = f"{test_dir}/test_download.txt"
    with open(filepath, "w") as f:
        f.write(content)

    resp = httpx.get(
        f"{BACKEND_URL}/session/{session_id}/download_file",
        params={"folder": test_dir, "filename": "test_download.txt"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert "file_id" in data["data"]


def test_get_basicinfo(session_id):
    resp = httpx.get(f"{BACKEND_URL}/session/{session_id}/basicinfo")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    infos = data["data"]
    assert isinstance(infos, list)
    assert len(infos) > 0
    keys = [info["key"] for info in infos]
    assert "whoami" in keys


def test_send_http_request_get(session_id, target_server):
    send_resp = httpx.post(
        f"{BACKEND_URL}/session/{session_id}/send_http_request",
        json={
            "url": TARGET_URL,
            "method": "GET",
        },
        timeout=30,
    )
    assert send_resp.status_code == 200
    result = send_resp.json()
    assert result["code"] == 0, f"send_http_request GET failed: {result}"


def test_send_http_request_post(session_id, target_server):
    post_body = "test_post_data"
    send_resp = httpx.post(
        f"{BACKEND_URL}/session/{session_id}/send_http_request",
        json={
            "url": TARGET_URL,
            "method": "POST",
            "data": post_body,
        },
        timeout=30,
    )
    assert send_resp.status_code == 200
    result = send_resp.json()
    assert result["code"] == 0, f"send_http_request POST failed: {result}"


def test_create_process_and_interact(session_id):
    resp = httpx.post(
        f"{BACKEND_URL}/session/{session_id}/process",
        json={"argv": ["bash", "--norc", "--noprofile"]},
        timeout=60,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0, f"create_process failed: {data}"
    process_id = data["data"]["process_id"]

    time.sleep(0.5)

    write_resp = httpx.post(
        f"{BACKEND_URL}/process/{process_id}/write_stdin",
        json={"data_b64": base64.b64encode(b"echo hello_from_bash\n").decode()},
        timeout=30,
    )
    assert write_resp.status_code == 200
    assert write_resp.json()["code"] == 0

    time.sleep(1.0)

    read_resp = httpx.get(
        f"{BACKEND_URL}/process/{process_id}/read_stdout_stderr",
        timeout=30,
    )
    assert read_resp.status_code == 200
    read_data = read_resp.json()
    assert read_data["code"] == 0, f"read failed: {read_data}"
    stdout = base64.b64decode(read_data["data"]["stdout"])
    assert b"hello_from_bash" in stdout, f"stdout: {stdout!r}"

    exit_resp = httpx.post(
        f"{BACKEND_URL}/process/{process_id}/write_stdin",
        json={"data_b64": base64.b64encode(b"exit 42\n").decode()},
        timeout=30,
    )
    assert exit_resp.status_code == 200

    wait_resp = httpx.get(
        f"{BACKEND_URL}/process/{process_id}/wait",
        params={"timeout": 10},
        timeout=30,
    )
    assert wait_resp.status_code == 200
    wait_data = wait_resp.json()
    assert wait_data["code"] == 0, f"wait failed: {wait_data}"
    assert wait_data["data"]["returncode"] == 42


@pytest.fixture(scope="module")
def install_tcp_tools(session_id):
    resp = httpx.get(
        f"{BACKEND_URL}/session/{session_id}/execute_cmd",
        params={"cmd": "apt-get update -qq && apt-get install -y -qq netcat-openbsd"},
        timeout=120,
    )
    assert resp.status_code == 200
    yield


def test_get_send_tcp_support_methods(session_id, install_tcp_tools):
    resp = httpx.get(f"{BACKEND_URL}/session/{session_id}/supported_send_tcp_methods")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0, f"get_send_tcp_support_methods failed: {data}"
    methods = data["data"]
    assert isinstance(methods, list)
    assert len(methods) > 0, "Expected at least one TCP method (socat or nc)"


def test_send_bytes_over_tcp(session_id, target_server, install_tcp_tools):
    methods_resp = httpx.get(
        f"{BACKEND_URL}/session/{session_id}/supported_send_tcp_methods"
    )
    methods = methods_resp.json()["data"]
    assert len(methods) > 0

    http_request = (
        f"GET / HTTP/1.0\r\n" f"Host: {TARGET_HOST}:{TARGET_PORT}\r\n" f"\r\n"
    ).encode()
    content_b64 = base64.b64encode(http_request).decode()

    resp = httpx.post(
        f"{BACKEND_URL}/session/{session_id}/send_bytes_tcp",
        json={
            "host": TARGET_HOST,
            "port": TARGET_PORT,
            "content_b64": content_b64,
            "send_method": methods[0],
        },
        timeout=30,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0, f"send_bytes_tcp failed: {data}"
    response_bytes = base64.b64decode(data["data"])
    assert TARGET_RESPONSE_BODY.encode() in response_bytes
