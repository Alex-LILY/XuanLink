import subprocess
import sys
import time
import uuid

import httpx
import pytest

HOST = "127.0.0.1"
PORT = 18022
BASE_URL = f"http://{HOST}:{PORT}"


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


def test_webshell_crud(backend_server):
    session_id = str(uuid.uuid4())

    add_resp = httpx.post(
        f"{BASE_URL}/update_webshell",
        json={
            "session_type": "ONELINE_PHP",
            "name": "e2e_test",
            "connection": {
                "url": "http://127.0.0.1:9999/shell.php",
                "password_method": "POST",
                "password": "cmd",
            },
            "session_id": session_id,
            "note": "e2e test",
            "location": "",
        },
    )
    assert add_resp.status_code == 200
    assert add_resp.json()["code"] == 0

    list_resp = httpx.get(f"{BASE_URL}/session")
    assert list_resp.status_code == 200
    sessions = list_resp.json()["data"]
    assert any(str(s["id"]) == session_id for s in sessions)

    delete_resp = httpx.delete(f"{BASE_URL}/session/{session_id}")
    assert delete_resp.status_code == 200
    assert delete_resp.json()["code"] == 0

    list_resp2 = httpx.get(f"{BASE_URL}/session")
    assert list_resp2.status_code == 200
    sessions2 = list_resp2.json()["data"]
    assert not any(str(s["id"]) == session_id for s in sessions2)
