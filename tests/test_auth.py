import subprocess
import sys
import time
import uuid

import httpx
import pytest


def _wait_for_server(port: int, timeout: float = 10.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            resp = httpx.get(f"http://127.0.0.1:{port}/utils/version", timeout=1.0)
            if resp.status_code == 200:
                return
        except httpx.ConnectError:
            pass
        time.sleep(0.2)
    raise RuntimeError(f"Server on port {port} did not start within {timeout}s")


@pytest.fixture(scope="module")
def auth_server():
    port = 18022 + hash(uuid.uuid4()) % 1000
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "ether_ghost",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--no-browser",
            "--auth",
            "testuser:testpass",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    _wait_for_server(port)
    yield port
    proc.terminate()
    proc.wait(timeout=5)


def test_auth_rejected_with_wrong_password(auth_server: int):
    resp = httpx.get(
        f"http://127.0.0.1:{auth_server}/connectortype",
        auth=("testuser", "wrongpass"),
    )
    assert resp.status_code == 401


def test_auth_rejected_without_credentials(auth_server: int):
    resp = httpx.get(f"http://127.0.0.1:{auth_server}/connectortype")
    assert resp.status_code == 401


def test_auth_accepted_with_correct_credentials(auth_server: int):
    resp = httpx.get(
        f"http://127.0.0.1:{auth_server}/connectortype",
        auth=("testuser", "testpass"),
    )
    assert resp.status_code == 200


def test_safe_utils_no_auth_required(auth_server: int):
    resp = httpx.get(f"http://127.0.0.1:{auth_server}/utils/version")
    assert resp.status_code == 200


def test_test_proxy_requires_auth(auth_server: int):
    resp = httpx.get(
        f"http://127.0.0.1:{auth_server}/utils/test_proxy",
        params={"proxy": "http://127.0.0.1:7810", "site": "google"},
    )
    assert resp.status_code == 401
