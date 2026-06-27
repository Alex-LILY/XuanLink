import asyncio
import base64
import os
import shutil
import subprocess
import sys
import time
import uuid

import httpx
import pytest

BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 18024
PHP_HOST = "127.0.0.1"
PHP_PORT = 19997
VESSEL_PHP_PORT = 19996
BACKEND_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"
PHP_URL = f"http://{PHP_HOST}:{PHP_PORT}"
VESSEL_PHP_URL = f"http://{PHP_HOST}:{VESSEL_PHP_PORT}"
TEST_ENV_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "test_environment")
)


def _check_php_available():
    return shutil.which("php") is not None


def _check_php_proc_open():
    try:
        result = subprocess.run(
            ["php", "-r", "echo function_exists('proc_open') ? 'yes' : 'no';"],
            capture_output=True,
            timeout=5,
            text=True,
        )
        return result.returncode == 0 and "yes" in result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


@pytest.fixture(scope="module")
def php_server():
    if not _check_php_available():
        pytest.skip("PHP not available")
    if not _check_php_proc_open():
        pytest.skip("PHP proc_open not available")
    proc = subprocess.Popen(
        ["php", "-S", f"{PHP_HOST}:{PHP_PORT}", "-t", TEST_ENV_DIR],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    started = False
    for _ in range(50):
        time.sleep(0.1)
        try:
            resp = httpx.get(f"{PHP_URL}/shell.php")
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
def vessel_php_server():
    proc = subprocess.Popen(
        ["php", "-S", f"{PHP_HOST}:{VESSEL_PHP_PORT}", "-t", TEST_ENV_DIR],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    started = False
    for _ in range(50):
        time.sleep(0.1)
        try:
            resp = httpx.get(f"{VESSEL_PHP_URL}/shell.php")
            if resp.status_code == 200:
                started = True
                break
        except httpx.ConnectError:
            continue
    if not started:
        proc.terminate()
        proc.wait()
        pytest.fail("Vessel PHP server failed to start")
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
def session_id(php_server, vessel_php_server, backend_server):
    sid = str(uuid.uuid4())
    resp = httpx.post(
        f"{BACKEND_URL}/update_webshell",
        json={
            "session_type": "ONELINE_PHP",
            "name": "e2e_process_test",
            "connection": {
                "url": f"{PHP_URL}/shell.php",
                "password_method": "POST",
                "password": "data",
                "http_params_obfs": False,
                "vessel_server_url": f"{VESSEL_PHP_URL}/shell.php",
            },
            "session_id": sid,
            "note": "e2e process test",
            "location": "",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["code"] == 0
    yield sid
    httpx.delete(f"{BACKEND_URL}/session/{sid}")


@pytest.fixture(scope="module")
def linux_cmd_session_id(php_server, backend_server):
    sid = str(uuid.uuid4())
    resp = httpx.post(
        f"{BACKEND_URL}/update_webshell",
        json={
            "session_type": "LINUX_CMD_ONELINER",
            "name": "e2e_linux_cmd_process_test",
            "connection": {
                "url": f"{PHP_URL}/cmd.php",
                "password": "data",
                "password_method": "POST",
            },
            "session_id": sid,
            "note": "e2e linux cmd process test",
            "location": "",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["code"] == 0
    yield sid
    httpx.delete(f"{BACKEND_URL}/session/{sid}")


def test_create_process_and_interact(session_id):
    resp = httpx.post(
        f"{BACKEND_URL}/session/{session_id}/process",
        json={"argv": ["bash"]},
        timeout=60,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0, f"create_process failed: {data}"
    process_id = data["data"]["process_id"]

    time.sleep(1)

    write_resp = httpx.post(
        f"{BACKEND_URL}/process/{process_id}/write_stdin",
        json={"data_b64": base64.b64encode(b"echo hello_from_process\n").decode()},
        timeout=30,
    )
    assert write_resp.status_code == 200
    assert write_resp.json()["code"] == 0

    time.sleep(1)

    read_resp = httpx.get(
        f"{BACKEND_URL}/process/{process_id}/read_stdout_stderr",
        timeout=30,
    )
    assert read_resp.status_code == 200
    read_data = read_resp.json()
    assert read_data["code"] == 0, f"read failed: {read_data}"
    stdout = base64.b64decode(read_data["data"]["stdout"])
    assert b"hello_from_process" in stdout, f"stdout: {stdout!r}"

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


def test_linux_cmd_create_process(linux_cmd_session_id):
    resp = httpx.post(
        f"{BACKEND_URL}/session/{linux_cmd_session_id}/process",
        json={"argv": ["bash", "--norc", "--noprofile"]},
    )
    assert resp.status_code == 200, f"Failed to create process: {resp.text}"
    data = resp.json()
    assert data["code"] == 0, f"Error: {data}"
    process_id = data["data"]["process_id"]
    pid = data["data"]["pid"]
    assert pid is not None

    time.sleep(0.5)

    cmd = b"echo hello_process\n"
    resp = httpx.post(
        f"{BACKEND_URL}/process/{process_id}/write_stdin",
        json={"data_b64": base64.b64encode(cmd).decode()},
    )
    assert resp.status_code == 200

    time.sleep(1.0)
    resp = httpx.get(f"{BACKEND_URL}/process/{process_id}/read_stdout_stderr")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    stdout = base64.b64decode(data["data"]["stdout"])
    assert b"hello_process" in stdout

    resp = httpx.post(
        f"{BACKEND_URL}/process/{process_id}/write_stdin",
        json={"data_b64": base64.b64encode(b"exit 42\n").decode()},
    )
    assert resp.status_code == 200

    time.sleep(0.5)
    resp = httpx.get(
        f"{BACKEND_URL}/process/{process_id}/wait",
        params={"timeout": 5},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["returncode"] == 42
