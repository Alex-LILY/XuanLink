import os
import subprocess
import sys
import time
import uuid

import httpx
import pytest

HOST = "127.0.0.1"
BACKEND_PORT = 18022
PHP_PORT = 19999
BASE_URL = f"http://{HOST}:{BACKEND_PORT}"
PHP_URL = f"http://{HOST}:{PHP_PORT}"
TEST_ENV_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "test_environment")
)


@pytest.fixture(scope="module")
def php_server():
    proc = subprocess.Popen(
        ["php", "-S", f"{HOST}:{PHP_PORT}", "-t", TEST_ENV_DIR],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    started = False
    for _ in range(100):
        time.sleep(0.1)
        try:
            resp = httpx.get(f"{PHP_URL}/index.html")
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
            f"PHP server failed to start.\nstdout: {stdout.decode()}\nstderr: {stderr.decode()}"
        )
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
            HOST,
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


def test_php_webshell_real(php_server, backend_server):
    session_id = str(uuid.uuid4())
    session_body = {
        "session_type": "ONELINE_PHP",
        "name": "e2e_real_test",
        "connection": {
            "url": f"{PHP_URL}/shell.php",
            "password_method": "POST",
            "password": "data",
            "http_params_obfs": False,
        },
        "session_id": session_id,
        "note": "e2e real test",
        "location": "",
    }

    add_resp = httpx.post(f"{BASE_URL}/update_webshell", json=session_body)
    assert add_resp.status_code == 200
    assert add_resp.json()["code"] == 0

    test_resp = httpx.post(f"{BASE_URL}/test_webshell", json=session_body)
    assert test_resp.status_code == 200
    data = test_resp.json()
    assert data["code"] == 0
    assert data["data"]["success"] is True

    read_resp = httpx.get(
        f"{BASE_URL}/session/{session_id}/get_file_contents",
        params={"current_dir": TEST_ENV_DIR, "filename": "index.html"},
    )
    assert read_resp.status_code == 200
    assert read_resp.json()["code"] == 0
    text = read_resp.json()["data"]["text"]
    assert "Hello World!" in text

    delete_resp = httpx.delete(f"{BASE_URL}/session/{session_id}")
    assert delete_resp.status_code == 200
    assert delete_resp.json()["code"] == 0
