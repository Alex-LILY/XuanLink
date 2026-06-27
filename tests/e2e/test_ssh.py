import base64
import hashlib
import os
import pwd
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler

import httpx
import pytest

BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 18025
BACKEND_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"

SSH_HOST = "127.0.0.1"
SSH_PORT = 22
SSH_USER = "testssh"
SSH_PASS = "testssh123"

TARGET_HOST = "127.0.0.1"
TARGET_PORT = 18096
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


def test_ssh_askpass_file_owner():
    askpass_fd, askpass_path = tempfile.mkstemp(suffix=".sh")
    with os.fdopen(askpass_fd, "w") as f:
        f.write("#!/bin/sh\necho testssh123\n")
    os.chmod(askpass_path, 0o755)

    test_file = "/tmp/ssh_test_file.txt"
    env = os.environ.copy()
    env["SSH_ASKPASS"] = askpass_path
    env["SSH_ASKPASS_REQUIRE"] = "force"
    env["DISPLAY"] = ":0"

    result = subprocess.run(
        [
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "testssh@127.0.0.1",
            f"touch {test_file}",
        ],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"SSH failed: {result.stderr}"

    stat_info = os.stat(test_file)
    owner = pwd.getpwuid(stat_info.st_uid).pw_name
    assert owner == "testssh", f"Expected owner testssh, got {owner}"

    os.unlink(askpass_path)
    os.unlink(test_file)


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
def session_id(backend_server):
    sid = str(uuid.uuid4())
    resp = httpx.post(
        f"{BACKEND_URL}/update_webshell",
        json={
            "session_type": "SSH",
            "name": "e2e_ssh_test",
            "connection": {
                "host": SSH_HOST,
                "port": SSH_PORT,
                "username": SSH_USER,
                "password": SSH_PASS,
            },
            "session_id": sid,
            "note": "e2e SSH test",
            "location": "",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["code"] == 0
    yield sid
    httpx.delete(f"{BACKEND_URL}/session/{sid}")


@pytest.fixture(scope="module")
def test_dir():
    path = f"/tmp/eg_e2e_ssh_{uuid.uuid4().hex[:8]}"
    os.makedirs(path)
    os.chmod(path, 0o777)
    yield path
    shutil.rmtree(path, ignore_errors=True)


def test_ssh_usability(session_id):
    resp = httpx.post(
        f"{BACKEND_URL}/test_webshell",
        json={
            "session_type": "SSH",
            "name": "e2e_ssh_test",
            "connection": {
                "host": SSH_HOST,
                "port": SSH_PORT,
                "username": SSH_USER,
                "password": SSH_PASS,
            },
            "session_id": session_id,
            "note": "",
            "location": "",
        },
        timeout=30,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["success"] is True


def test_ssh_execute_cmd(session_id):
    resp = httpx.get(
        f"{BACKEND_URL}/session/{session_id}/execute_cmd",
        params={"cmd": "echo hello_ssh_world"},
        timeout=30,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert "hello_ssh_world" in data["data"]


def test_ssh_get_pwd(session_id):
    resp = httpx.get(f"{BACKEND_URL}/session/{session_id}/get_pwd", timeout=30)
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert isinstance(data["data"], str)
    assert len(data["data"]) > 0


def test_ssh_list_dir(session_id, test_dir):
    marker_file = f"{test_dir}/list_marker.txt"
    with open(marker_file, "w") as f:
        f.write("list test")

    resp = httpx.get(
        f"{BACKEND_URL}/session/{session_id}/list_dir",
        params={"current_dir": test_dir},
        timeout=30,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    entries = data["data"]
    assert isinstance(entries, list)
    assert any(e["name"] == "list_marker.txt" for e in entries)


def test_ssh_mkdir(session_id, test_dir):
    new_dir = f"{test_dir}/subdir_mkdir"
    resp = httpx.get(
        f"{BACKEND_URL}/session/{session_id}/mkdir",
        params={"dirpath": new_dir},
        timeout=30,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert os.path.isdir(new_dir)


def test_ssh_put_and_get_file_contents(session_id, test_dir):
    content = f"hello e2e ssh {uuid.uuid4().hex[:8]}"
    put_resp = httpx.post(
        f"{BACKEND_URL}/session/{session_id}/put_file_contents",
        json={
            "current_dir": test_dir,
            "filename": "test_rw.txt",
            "text": content,
            "encoding": "utf-8",
        },
        timeout=30,
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["code"] == 0

    get_resp = httpx.get(
        f"{BACKEND_URL}/session/{session_id}/get_file_contents",
        params={"current_dir": test_dir, "filename": "test_rw.txt"},
        timeout=30,
    )
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["code"] == 0
    assert data["data"]["text"] == content


def test_ssh_delete_file(session_id, test_dir):
    filepath = f"{test_dir}/test_delete.txt"
    with open(filepath, "w") as f:
        f.write("to be deleted")
    assert os.path.exists(filepath)

    resp = httpx.get(
        f"{BACKEND_URL}/session/{session_id}/delete_file",
        params={"current_dir": test_dir, "filename": "test_delete.txt"},
        timeout=30,
    )
    assert resp.status_code == 200
    assert resp.json()["code"] == 0
    assert not os.path.exists(filepath)


def test_ssh_move_file(session_id, test_dir):
    src = f"{test_dir}/test_move_src.txt"
    dst = f"{test_dir}/test_move_dst.txt"
    with open(src, "w") as f:
        f.write("move me")

    resp = httpx.get(
        f"{BACKEND_URL}/session/{session_id}/move_file",
        params={"filepath": src, "new_filepath": dst},
        timeout=30,
    )
    assert resp.status_code == 200
    assert resp.json()["code"] == 0
    assert not os.path.exists(src)
    assert os.path.exists(dst)
    with open(dst) as f:
        assert f.read() == "move me"


def test_ssh_copy_file(session_id, test_dir):
    src = f"{test_dir}/test_copy_src.txt"
    dst = f"{test_dir}/test_copy_dst.txt"
    content = "copy me"
    with open(src, "w") as f:
        f.write(content)

    resp = httpx.get(
        f"{BACKEND_URL}/session/{session_id}/copy_file",
        params={"filepath": src, "new_filepath": dst},
        timeout=30,
    )
    assert resp.status_code == 200
    assert resp.json()["code"] == 0
    assert os.path.exists(src)
    assert os.path.exists(dst)
    with open(dst) as f:
        assert f.read() == content


def test_ssh_modify_file_once(session_id, test_dir):
    content = "line1\noldline\nline3\noldline\nline5"
    filepath = f"{test_dir}/test_modify_once.txt"
    with open(filepath, "w") as f:
        f.write(content)
    os.chmod(filepath, 0o666)

    resp = httpx.post(
        f"{BACKEND_URL}/session/{session_id}/modify_file",
        json={
            "filepath": filepath,
            "old_str": "oldline",
            "new_str": "newline",
            "replace_strategy": "once",
        },
        timeout=30,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0

    with open(filepath) as f:
        result = f.read()
    assert result == "line1\nnewline\nline3\noldline\nline5"


def test_ssh_modify_file_all(session_id, test_dir):
    content = "line1\noldline\nline3\noldline\nline5"
    filepath = f"{test_dir}/test_modify_all.txt"
    with open(filepath, "w") as f:
        f.write(content)
    os.chmod(filepath, 0o666)

    resp = httpx.post(
        f"{BACKEND_URL}/session/{session_id}/modify_file",
        json={
            "filepath": filepath,
            "old_str": "oldline",
            "new_str": "newline",
            "replace_strategy": "all",
        },
        timeout=30,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0

    with open(filepath) as f:
        result = f.read()
    assert result == "line1\nnewline\nline3\nnewline\nline5"


def test_ssh_modify_file_default_exact_once(session_id, test_dir):
    content = "prefix UNIQUE_MARKER suffix"
    filepath = f"{test_dir}/test_modify_default.txt"
    with open(filepath, "w") as f:
        f.write(content)
    os.chmod(filepath, 0o666)

    resp = httpx.post(
        f"{BACKEND_URL}/session/{session_id}/modify_file",
        json={
            "filepath": filepath,
            "old_str": "UNIQUE_MARKER",
            "new_str": "REPLACED",
        },
        timeout=30,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0

    with open(filepath) as f:
        result = f.read()
    assert result == "prefix REPLACED suffix"


def test_ssh_modify_file_default_fails_on_multiple(session_id, test_dir):
    content = "dup dup dup"
    filepath = f"{test_dir}/test_modify_multi.txt"
    with open(filepath, "w") as f:
        f.write(content)

    resp = httpx.post(
        f"{BACKEND_URL}/session/{session_id}/modify_file",
        json={
            "filepath": filepath,
            "old_str": "dup",
            "new_str": "replaced",
        },
        timeout=30,
    )
    data = resp.json()
    assert data["code"] != 0

    with open(filepath) as f:
        result = f.read()
    assert result == content


def test_ssh_modify_file_not_found(session_id, test_dir):
    content = "some random text"
    filepath = f"{test_dir}/test_modify_nf.txt"
    with open(filepath, "w") as f:
        f.write(content)

    resp = httpx.post(
        f"{BACKEND_URL}/session/{session_id}/modify_file",
        json={
            "filepath": filepath,
            "old_str": "NONEXISTENT",
            "new_str": "replaced",
            "replace_strategy": "once",
        },
        timeout=30,
    )
    data = resp.json()
    assert data["code"] != 0

    with open(filepath) as f:
        result = f.read()
    assert result == content


def test_ssh_get_basicinfo(session_id):
    resp = httpx.get(f"{BACKEND_URL}/session/{session_id}/basicinfo", timeout=30)
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    infos = data["data"]
    assert isinstance(infos, list)
    assert len(infos) > 0
    keys = [info["key"] for info in infos]
    assert "whoami" in keys


def test_ssh_send_http_request_get(session_id, target_server):
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


def test_ssh_send_http_request_post(session_id, target_server):
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


def test_ssh_upload_file_512kb(session_id, test_dir):
    content = os.urandom(512 * 1024)
    expected_md5 = hashlib.md5(content).hexdigest()
    resp = httpx.post(
        f"{BACKEND_URL}/session/{session_id}/upload_file",
        files={"file": ("test_upload_512k.bin", content, "application/octet-stream")},
        data={"folder": test_dir},
        timeout=120,
    )
    assert resp.status_code == 200
    assert resp.json()["code"] == 0
    uploaded_path = f"{test_dir}/test_upload_512k.bin"
    assert os.path.exists(uploaded_path)
    with open(uploaded_path, "rb") as f:
        actual_md5 = hashlib.md5(f.read()).hexdigest()
    assert actual_md5 == expected_md5, f"MD5 mismatch: {actual_md5} != {expected_md5}"


def test_ssh_download_file_512kb(session_id, test_dir):
    content = os.urandom(512 * 1024)
    expected_md5 = hashlib.md5(content).hexdigest()
    filepath = f"{test_dir}/test_download_512k.bin"
    with open(filepath, "wb") as f:
        f.write(content)

    resp = httpx.get(
        f"{BACKEND_URL}/session/{session_id}/download_file",
        params={"folder": test_dir, "filename": "test_download_512k.bin"},
        timeout=120,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert "file_id" in data["data"]

    file_id = data["data"]["file_id"]
    dl_resp = httpx.get(
        f"{BACKEND_URL}/utils/fetch_downloaded_file/{file_id}", timeout=30
    )
    assert dl_resp.status_code == 200
    actual_md5 = hashlib.md5(dl_resp.content).hexdigest()
    assert actual_md5 == expected_md5, f"MD5 mismatch: {actual_md5} != {expected_md5}"


def test_ssh_create_process_alternating(session_id):
    proc_a_resp = httpx.post(
        f"{BACKEND_URL}/session/{session_id}/process",
        json={"argv": ["bash", "--norc", "--noprofile"]},
        timeout=30,
    )
    assert proc_a_resp.status_code == 200
    proc_a_data = proc_a_resp.json()
    assert proc_a_data["code"] == 0, f"create process A failed: {proc_a_data}"
    proc_a_id = proc_a_data["data"]["process_id"]

    proc_b_resp = httpx.post(
        f"{BACKEND_URL}/session/{session_id}/process",
        json={"argv": ["bash", "--norc", "--noprofile"]},
        timeout=30,
    )
    assert proc_b_resp.status_code == 200
    proc_b_data = proc_b_resp.json()
    assert proc_b_data["code"] == 0, f"create process B failed: {proc_b_data}"
    proc_b_id = proc_b_data["data"]["process_id"]

    time.sleep(0.5)

    httpx.post(
        f"{BACKEND_URL}/process/{proc_a_id}/write_stdin",
        json={"data_b64": base64.b64encode(b"echo round1_A\n").decode()},
        timeout=30,
    )
    time.sleep(0.5)
    resp_a1 = httpx.get(
        f"{BACKEND_URL}/process/{proc_a_id}/read_stdout_stderr", timeout=30
    )
    stdout_a1 = base64.b64decode(resp_a1.json()["data"]["stdout"])
    assert b"round1_A" in stdout_a1

    httpx.post(
        f"{BACKEND_URL}/process/{proc_b_id}/write_stdin",
        json={"data_b64": base64.b64encode(b"echo round1_B\n").decode()},
        timeout=30,
    )
    time.sleep(0.5)
    resp_b1 = httpx.get(
        f"{BACKEND_URL}/process/{proc_b_id}/read_stdout_stderr", timeout=30
    )
    stdout_b1 = base64.b64decode(resp_b1.json()["data"]["stdout"])
    assert b"round1_B" in stdout_b1

    httpx.post(
        f"{BACKEND_URL}/process/{proc_a_id}/write_stdin",
        json={"data_b64": base64.b64encode(b"echo round2_A\n").decode()},
        timeout=30,
    )
    time.sleep(0.5)
    resp_a2 = httpx.get(
        f"{BACKEND_URL}/process/{proc_a_id}/read_stdout_stderr", timeout=30
    )
    stdout_a2 = base64.b64decode(resp_a2.json()["data"]["stdout"])
    assert b"round2_A" in stdout_a2

    httpx.post(
        f"{BACKEND_URL}/process/{proc_b_id}/write_stdin",
        json={"data_b64": base64.b64encode(b"echo round2_B\n").decode()},
        timeout=30,
    )
    time.sleep(0.5)
    resp_b2 = httpx.get(
        f"{BACKEND_URL}/process/{proc_b_id}/read_stdout_stderr", timeout=30
    )
    stdout_b2 = base64.b64decode(resp_b2.json()["data"]["stdout"])
    assert b"round2_B" in stdout_b2

    httpx.post(
        f"{BACKEND_URL}/process/{proc_a_id}/write_stdin",
        json={"data_b64": base64.b64encode(b"exit 0\n").decode()},
        timeout=30,
    )
    httpx.post(
        f"{BACKEND_URL}/process/{proc_b_id}/write_stdin",
        json={"data_b64": base64.b64encode(b"exit 0\n").decode()},
        timeout=30,
    )
