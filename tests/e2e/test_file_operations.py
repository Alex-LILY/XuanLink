import os
import shutil
import subprocess
import sys
import time
import uuid

import httpx
import pytest

BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 18022
PHP_HOST = "127.0.0.1"
PHP_PORT = 19999
BACKEND_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"
PHP_URL = f"http://{PHP_HOST}:{PHP_PORT}"


@pytest.fixture(scope="module")
def php_server():
    assert shutil.which("php") is not None, "PHP is required for e2e tests"
    test_env = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "test_environment")
    )
    proc = subprocess.Popen(
        ["php", "-S", f"{PHP_HOST}:{PHP_PORT}", "-t", test_env],
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
def session_id(php_server, backend_server):
    sid = str(uuid.uuid4())
    resp = httpx.post(
        f"{BACKEND_URL}/update_webshell",
        json={
            "session_type": "ONELINE_PHP",
            "name": "e2e_file_test",
            "connection": {
                "url": f"{PHP_URL}/shell.php",
                "password_method": "POST",
                "password": "data",
                "http_params_obfs": False,
            },
            "session_id": sid,
            "note": "e2e file ops test",
            "location": "",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["code"] == 0
    yield sid
    httpx.delete(f"{BACKEND_URL}/session/{sid}")


@pytest.fixture(scope="module")
def test_dir():
    path = f"/tmp/eg_e2e_{uuid.uuid4().hex[:8]}"
    os.makedirs(path)
    yield path
    shutil.rmtree(path, ignore_errors=True)


def test_get_pwd(session_id):
    resp = httpx.get(f"{BACKEND_URL}/session/{session_id}/get_pwd")
    assert resp.status_code == 200, f"resp: {resp.text}"
    data = resp.json()
    assert data["code"] == 0
    assert isinstance(data["data"], str)
    assert len(data["data"]) > 0


def test_list_dir(session_id, test_dir):
    resp = httpx.get(
        f"{BACKEND_URL}/session/{session_id}/list_dir",
        params={"current_dir": test_dir},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    entries = data["data"]
    assert isinstance(entries, list)
    assert any(e["name"] == "." for e in entries)
    assert any(e["name"] == ".." for e in entries)


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
    content = f"hello e2e {uuid.uuid4().hex[:8]}"
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


def test_modify_file_once(session_id, test_dir):
    content = "line1\noldline\nline3\noldline\nline5"
    filepath = f"{test_dir}/test_modify_once.txt"
    with open(filepath, "w") as f:
        f.write(content)

    resp = httpx.post(
        f"{BACKEND_URL}/session/{session_id}/modify_file",
        json={
            "filepath": filepath,
            "old_str": "oldline",
            "new_str": "newline",
            "replace_strategy": "once",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0

    with open(filepath) as f:
        result = f.read()
    assert result == "line1\nnewline\nline3\noldline\nline5"


def test_modify_file_all(session_id, test_dir):
    content = "line1\noldline\nline3\noldline\nline5"
    filepath = f"{test_dir}/test_modify_all.txt"
    with open(filepath, "w") as f:
        f.write(content)

    resp = httpx.post(
        f"{BACKEND_URL}/session/{session_id}/modify_file",
        json={
            "filepath": filepath,
            "old_str": "oldline",
            "new_str": "newline",
            "replace_strategy": "all",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0

    with open(filepath) as f:
        result = f.read()
    assert result == "line1\nnewline\nline3\nnewline\nline5"


def test_modify_file_default_exact_once(session_id, test_dir):
    content = "prefix UNIQUE_MARKER suffix"
    filepath = f"{test_dir}/test_modify_default.txt"
    with open(filepath, "w") as f:
        f.write(content)

    resp = httpx.post(
        f"{BACKEND_URL}/session/{session_id}/modify_file",
        json={
            "filepath": filepath,
            "old_str": "UNIQUE_MARKER",
            "new_str": "REPLACED",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0

    with open(filepath) as f:
        result = f.read()
    assert result == "prefix REPLACED suffix"


def test_modify_file_default_fails_on_multiple(session_id, test_dir):
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
    )
    data = resp.json()
    assert data["code"] != 0

    with open(filepath) as f:
        result = f.read()
    assert result == content


def test_modify_file_not_found(session_id, test_dir):
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
    )
    data = resp.json()
    assert data["code"] != 0

    with open(filepath) as f:
        result = f.read()
    assert result == content
