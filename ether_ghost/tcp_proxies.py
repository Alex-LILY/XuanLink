"""
TCP代理管理模块

实现两种TCP代理服务：
1. PsudoTcpServeConnection - 伪TCP代理
2. VesselTcpForwardServeConnection - Vessel TCP转发代理

提供代理服务的启动和管理功能
"""

import asyncio
import traceback
import re
import base64
import uuid
import time
import typing as t
import logging
import socket
from urllib.parse import urlparse


logger = logging.getLogger("core.tcp_proxies")

from .core import SessionInterface, exceptions, PHPSessionInterface
from .vessel_php.main import get_vessel_client
from .regeorg_tunnel import get_tunnel, ReGeorgSocket


class PsudoTcpServeConnection:
    def __init__(
        self,
        session: SessionInterface,
        listen_host: str,
        listen_port: int,
        host: str,
        port: int,
        send_method: t.Union[str, None],
    ):
        self.session = session
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.host = host
        self.port = port
        self.send_method = send_method

    async def serve_connection_raw(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        request = b""
        while not request.endswith(b"\r\n\r\n"):
            request += await reader.read(1024)
        if b"HTTP/1.1" not in request:
            writer.write(
                b"HTTP/1.1 400 Bad Request\r\nContent-Length: 14\r\nConnection: close\r\n\r\n400 bad req sb\r\n\r\n"
            )
            writer.write_eof()
            writer.close()
            return
        if b"Connection: close" not in request:
            request = request.replace(
                b"HTTP/1.1\r\n", b"HTTP/1.1\r\nConnection: close\r\n", 1
            )
        response = await self.session.send_bytes_over_tcp(
            self.host, self.port, request, self.send_method
        )
        if response is None:
            writer.write_eof()
            writer.close()
            return
        if b"Server: " in response:
            response = re.sub(rb"Server: .+\r\n", b"Server: sbserver\r\n", response)
        writer.write(response)
        writer.write_eof()
        writer.close()
        return

    async def serve_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        try:
            await self.serve_connection_raw(reader, writer)
        except Exception:
            logger.error("Exception in serve_connection", exc_info=True)

    async def start_server(self) -> asyncio.Task:
        try:
            server = await asyncio.start_server(
                self.serve_connection, self.listen_host, self.listen_port
            )
        except OSError as exc:
            if exc.errno == 98:
                raise exceptions.ServerError(
                    f"无法绑定{self.listen_host}:{self.listen_port}，是不是被占用了？"
                )
            raise exceptions.ServerError("无法启动代理") from exc
        except Exception as exc:
            raise exceptions.ServerError("无法启动代理") from exc
        task = asyncio.create_task(server.serve_forever())
        return task


async def start_psudo_tcp_proxy(
    session: SessionInterface,
    listen_host: str,
    listen_port: int,
    host: str,
    port: int,
    send_method: t.Union[str, None],
) -> asyncio.Task:
    return await PsudoTcpServeConnection(
        session, listen_host, listen_port, host, port, send_method
    ).start_server()


# TODO: 允许用户在设置里指定这两个值
REQUEST_INTERVAL_SHORT = 0.1
REQUEST_INTERVAL_LONG = 2


async def sender(
    state: dict,
    call: t.Callable[..., t.Awaitable],
    socket_id: int,
    reader: asyncio.StreamReader,
):
    while state["socket_open"]:
        # TODO: 允许用户设置这里的buffer大小
        tosend = await reader.read(1024 * 128)
        if not tosend:
            state["socket_open"] = False
            return
        try:
            await call(
                "tcp_socket_write",
                socket_id,
                base64.b64encode(tosend).decode(),
                timeout=1,
            )
        except exceptions.TargetRuntimeError as e:
            if "VESSEL_FAILED" not in str(e):
                raise e
            logger.debug(f"Sent {len(tosend)} bytes")
            state["socket_open"] = False
            return
        state["last_communicate_time"] = time.perf_counter()


async def receiver(
    state: dict,
    call: t.Callable[..., t.Awaitable],
    socket_id: int,
    writer: asyncio.StreamWriter,
):
    while state["socket_open"]:
        try:
            towrite = await call(
                "tcp_socket_read",
                socket_id,
                1024 * 128,
                timeout=1,
            )
        except exceptions.TargetRuntimeError as e:
            if "VESSEL_FAILED" not in str(e):
                raise e
            state["socket_open"] = False
            return
        if towrite is None:
            await asyncio.sleep(1)
            continue
        towrite_bytes = base64.b64decode(towrite)
        if not towrite_bytes:
            await asyncio.sleep(
                REQUEST_INTERVAL_SHORT
                if time.perf_counter() - state["last_communicate_time"] < 3
                else REQUEST_INTERVAL_LONG
            )
            logger.debug(f"Received {len(towrite_bytes)} bytes")
            continue
        writer.write(towrite_bytes)
        state["last_communicate_time"] = time.perf_counter()


class VesselTcpForwardServeConnection:
    def __init__(
        self,
        session: PHPSessionInterface,
        load_vessel_client_code: str,
        listen_host: str,
        listen_port: int,
        host: str,
        port: int,
    ):
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.host = host
        self.port = port
        self.call = get_vessel_client(session, load_vessel_client_code)
        self.session_key = f"_{uuid.uuid4()}"

    async def serve_connection_raw(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        socket_id = await self.call(
            "tcp_socket_connect", self.host, self.port, timeout=1
        )
        if socket_id is None:
            raise exceptions.ServerError("Cannot connect")
        logger.info(f"Opened new socket {socket_id=}")
        state = {
            "socket_open": True,
            "session_key": self.session_key,
            "last_communicate_time": time.perf_counter(),
        }
        try:
            await asyncio.gather(  # type: ignore
                sender(state, self.call, socket_id, reader),  # type: ignore
                receiver(state, self.call, socket_id, writer),  # type: ignore
            )
        finally:
            state["socket_open"] = False
        try:
            await self.call(
                "tcp_socket_close",
                socket_id,
                1024,
                timeout=1,
            )
        except exceptions.TargetRuntimeError as e:
            if "VESSEL_FAILED" not in str(e):
                raise e
            logger.warning(f"Socket close failed {socket_id=}: {str(e)}")
        logger.info(f"Socket closed {socket_id=}")

    async def serve_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        try:
            await self.serve_connection_raw(reader, writer)
        except Exception:
            writer.close()
            logger.error("Exception in serve_connection", exc_info=True)

    async def start_server(self):

        await asyncio.sleep(0.1)
        server = await asyncio.start_server(
            self.serve_connection, self.listen_host, self.listen_port
        )

        return asyncio.create_task(server.serve_forever())


async def _regeorg_relay(
    sock: ReGeorgSocket,
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    initial_remote_bytes: bytes = b"",
):
    """在本地 TCP 连接和 ReGeorg 远程 socket 之间双向转发数据。"""
    if initial_remote_bytes:
        await sock.write(initial_remote_bytes)

    running = True

    async def local_to_remote():
        nonlocal running
        try:
            while running:
                data = await reader.read(1024 * 128)
                if not data:
                    running = False
                    return
                await sock.write(data)
        except Exception as exc:
            logger.debug("local_to_remote 结束: %s", exc)
            running = False

    async def remote_to_local():
        nonlocal running
        try:
            while running:
                data = await sock.read(1024 * 128)
                if not data:
                    running = False
                    try:
                        writer.write_eof()
                    except Exception:
                        pass
                    return
                writer.write(data)
                await writer.drain()
        except Exception as exc:
            logger.debug("remote_to_local 结束: %s", exc)
            running = False

    try:
        await asyncio.gather(local_to_remote(), remote_to_local())
    finally:
        try:
            await sock.close()
        except Exception:
            pass
        try:
            writer.close()
        except Exception:
            pass


async def start_vessel_forward_tcp(
    session: PHPSessionInterface,
    load_vessel_client_code: str,
    listen_host: str,
    listen_port: int,
    host: str,
    port: int,
) -> asyncio.Task:
    return await VesselTcpForwardServeConnection(
        session,
        load_vessel_client_code,
        listen_host,
        listen_port,
        host,
        port,
    ).start_server()


async def _vessel_relay(
    call: t.Callable[..., t.Awaitable],
    socket_id: int,
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    initial_remote_bytes: bytes = b"",
):
    """在客户端和Vessel远程socket之间双向转发数据。"""
    if initial_remote_bytes:
        await call(
            "tcp_socket_write",
            socket_id,
            base64.b64encode(initial_remote_bytes).decode(),
            timeout=1,
        )

    state = {
        "socket_open": True,
        "last_communicate_time": time.perf_counter(),
    }

    async def sender():
        while state["socket_open"]:
            tosend = await reader.read(1024 * 128)
            if not tosend:
                state["socket_open"] = False
                return
            try:
                await call(
                    "tcp_socket_write",
                    socket_id,
                    base64.b64encode(tosend).decode(),
                    timeout=1,
                )
            except exceptions.TargetRuntimeError as e:
                if "VESSEL_FAILED" not in str(e):
                    raise e
                state["socket_open"] = False
                return
            state["last_communicate_time"] = time.perf_counter()

    async def receiver():
        while state["socket_open"]:
            try:
                towrite = await call(
                    "tcp_socket_read",
                    socket_id,
                    1024 * 128,
                    timeout=1,
                )
            except exceptions.TargetRuntimeError as e:
                if "VESSEL_FAILED" not in str(e):
                    raise e
                state["socket_open"] = False
                return
            if towrite is None:
                await asyncio.sleep(1)
                continue
            towrite_bytes = base64.b64decode(towrite)
            if not towrite_bytes:
                await asyncio.sleep(
                    REQUEST_INTERVAL_SHORT
                    if time.perf_counter() - state["last_communicate_time"] < 3
                    else REQUEST_INTERVAL_LONG
                )
                continue
            writer.write(towrite_bytes)
            await writer.drain()
            state["last_communicate_time"] = time.perf_counter()

    try:
        await asyncio.gather(sender(), receiver())
    finally:
        state["socket_open"] = False
        try:
            await call("tcp_socket_close", socket_id, timeout=1)
        except exceptions.TargetRuntimeError as e:
            if "VESSEL_FAILED" not in str(e):
                raise e


class VesselHttpProxyServeConnection:
    """基于ReGeorg隧道的HTTP代理：CONNECT走隧道，普通HTTP直接转发。"""

    def __init__(
        self,
        session: PHPSessionInterface,
        listen_host: str,
        listen_port: int,
    ):
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.session = session

    async def _parse_target(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> t.Tuple[str, int, bytes, bytes]:
        """解析HTTP代理握手，返回(目标host, 目标port, 初始数据, 连接成功后要发给客户端的响应)。"""
        header_data = b""
        while b"\r\n\r\n" not in header_data:
            chunk = await reader.read(4096)
            if not chunk:
                break
            header_data += chunk
            if len(header_data) > 65536:
                raise ValueError("HTTP请求头过大")
        if not header_data:
            raise ValueError("空的HTTP请求")

        lines = header_data.split(b"\r\n")
        request_line_parts = lines[0].split()
        if len(request_line_parts) < 2:
            raise ValueError("非法的HTTP请求行")
        method = request_line_parts[0].decode("ascii", errors="ignore").upper()
        uri = request_line_parts[1].decode("ascii", errors="ignore")

        if method == "CONNECT":
            target = uri
            if ":" not in target:
                target += ":443"
            host, port_str = target.rsplit(":", 1)
            port = int(port_str)
            return host, port, b"", b"HTTP/1.1 200 Connection established\r\n\r\n"

        # 普通HTTP请求：从URL或Host头解析目标
        host, port = None, 80
        parsed = urlparse(uri)
        if parsed.scheme in ("http", "https"):
            host = parsed.hostname
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
        else:
            for line in lines[1:]:
                if line.lower().startswith(b"host:"):
                    host_part = line.split(b":", 1)[1].strip().decode("ascii", errors="ignore")
                    if ":" in host_part:
                        host, port_str = host_part.rsplit(":", 1)
                        port = int(port_str)
                    else:
                        host = host_part
                    break
        if not host:
            writer.write(
                b"HTTP/1.1 400 Bad Request\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
            )
            await writer.drain()
            raise ValueError("无法解析HTTP代理目标")
        return host, port, header_data, b""

    async def _forward_http_request(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        header_data: bytes,
        host: str,
        port: int,
    ):
        """普通HTTP请求直接通过session.send_http_request转发，不占用Vessel隧道。"""
        lines = header_data.split(b"\r\n")
        request_line_parts = lines[0].split()
        if len(request_line_parts) < 3:
            raise ValueError("非法的HTTP请求行")
        method = request_line_parts[0].decode("ascii", errors="ignore")
        uri = request_line_parts[1].decode("ascii", errors="ignore")

        headers: t.Dict[str, str] = {}
        for line in lines[1:]:
            if not line:
                continue
            if b":" not in line:
                continue
            key, value = line.split(b":", 1)
            headers[key.decode("ascii", errors="ignore").strip()] = value.decode("ascii", errors="ignore").strip()

        if uri.startswith("http://") or uri.startswith("https://"):
            url = uri
        else:
            default_port = 80 if port == 80 else port
            url = f"http://{host}:{default_port}{uri}"

        body = b""
        content_length_str = headers.get("Content-Length") or headers.get("content-length")
        if content_length_str:
            content_length = int(content_length_str)
            remaining = content_length
            while remaining > 0:
                chunk = await reader.read(min(remaining, 4096))
                if not chunk:
                    break
                body += chunk
                remaining -= len(chunk)
        elif headers.get("Transfer-Encoding", "").lower() == "chunked":
            # 不支持chunked请求体
            writer.write(b"HTTP/1.1 501 Not Implemented\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
            await writer.drain()
            return

        response = await self.session.send_http_request(url, method, headers, body or None)
        status_line = f"HTTP/1.1 {response['status_code']} OK\r\n".encode()
        writer.write(status_line)
        for key, value in response["headers"].items():
            writer.write(f"{key}: {value}\r\n".encode())
        writer.write(b"\r\n")
        writer.write(response["body"])
        await writer.drain()

    async def serve_connection_raw(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        try:
            host, port, initial_bytes, success_response = await self._parse_target(reader, writer)
        except Exception as exc:
            logger.debug("HTTP代理握手失败: %s", exc)
            writer.close()
            return

        if not success_response:
            # 普通HTTP请求：使用session.send_http_request，无需Vessel隧道
            try:
                await self._forward_http_request(reader, writer, initial_bytes, host, port)
            except Exception as exc:
                logger.warning("HTTP代理转发请求失败: %s", exc)
                writer.write(
                    b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
                )
                await writer.drain()
            writer.close()
            return

        # CONNECT 隧道：使用 ReGeorg 建立双向 TCP 隧道
        try:
            tunnel = await get_tunnel(self.session)
            sock = await tunnel.open_socket()
            connected = await sock.connect(host, port)
        except Exception as exc:
            logger.warning("HTTP代理连接目标失败 %s:%s: %s", host, port, exc)
            connected = False

        if not connected:
            writer.write(
                b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
            )
            await writer.drain()
            writer.close()
            return

        writer.write(success_response)
        await writer.drain()

        try:
            await _regeorg_relay(sock, reader, writer)
        except Exception:
            logger.error("HTTP代理转发异常", exc_info=True)
        finally:
            writer.close()

    async def serve_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        try:
            await self.serve_connection_raw(reader, writer)
        except Exception:
            logger.error("HTTP代理连接异常", exc_info=True)
            try:
                writer.close()
            except Exception:
                pass

    async def start_server(self) -> asyncio.Task:
        try:
            server = await asyncio.start_server(
                self.serve_connection, self.listen_host, self.listen_port
            )
        except OSError as exc:
            if exc.errno == 98:
                raise exceptions.ServerError(
                    f"无法绑定{self.listen_host}:{self.listen_port}，是不是被占用了？"
                )
            raise exceptions.ServerError("无法启动HTTP代理") from exc
        return asyncio.create_task(server.serve_forever())


class VesselSocks5ServeConnection:
    """基于ReGeorg隧道的SOCKS5代理。"""

    def __init__(
        self,
        session: PHPSessionInterface,
        listen_host: str,
        listen_port: int,
    ):
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.session = session

    async def _parse_target(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> t.Tuple[str, int]:
        header = await reader.read(2)
        if len(header) < 2:
            raise ValueError("SOCKS5握手头不完整")
        ver, nmethods = header[0], header[1]
        if ver != 0x05:
            raise ValueError("非SOCKS5请求")
        methods = await reader.read(nmethods)
        if 0x00 not in methods:
            writer.write(b"\x05\xFF")
            await writer.drain()
            raise ValueError("SOCKS5需要认证")
        writer.write(b"\x05\x00")
        await writer.drain()

        req = await reader.read(4)
        if len(req) < 4:
            raise ValueError("SOCKS5请求不完整")
        ver, cmd, _, atyp = req
        if ver != 0x05:
            raise ValueError("非SOCKS5请求")
        if cmd != 0x01:  # 只支持CONNECT
            writer.write(b"\x05\x07\x00\x01\x00\x00\x00\x00\x00\x00")
            await writer.drain()
            raise ValueError("SOCKS5不支持该命令")

        if atyp == 0x01:  # IPv4
            addr_bytes = await reader.read(4)
            addr = socket.inet_ntoa(addr_bytes)
        elif atyp == 0x03:  # 域名
            domain_len_data = await reader.read(1)
            domain_len = domain_len_data[0]
            addr = (await reader.read(domain_len)).decode("ascii", errors="ignore")
        elif atyp == 0x04:  # IPv6
            addr_bytes = await reader.read(16)
            addr = socket.inet_ntop(socket.AF_INET6, addr_bytes)
        else:
            writer.write(b"\x05\x08\x00\x01\x00\x00\x00\x00\x00\x00")
            await writer.drain()
            raise ValueError("SOCKS5不支持的地址类型")

        port_bytes = await reader.read(2)
        port = int.from_bytes(port_bytes, "big")
        return addr, port

    async def serve_connection_raw(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        try:
            host, port = await self._parse_target(reader, writer)
        except Exception as exc:
            logger.debug("SOCKS5握手失败: %s", exc)
            writer.close()
            return

        try:
            tunnel = await get_tunnel(self.session)
            sock = await tunnel.open_socket()
            connected = await sock.connect(host, port)
        except Exception as exc:
            logger.warning("SOCKS5连接目标失败 %s:%s: %s", host, port, exc)
            connected = False

        if not connected:
            writer.write(b"\x05\x05\x00\x01\x00\x00\x00\x00\x00\x00")
            await writer.drain()
            writer.close()
            return

        # 响应成功，BND.ADDR使用0.0.0.0:0
        writer.write(b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")
        await writer.drain()

        try:
            await _regeorg_relay(sock, reader, writer)
        except Exception:
            logger.error("SOCKS5转发异常", exc_info=True)
        finally:
            writer.close()

    async def serve_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        try:
            await self.serve_connection_raw(reader, writer)
        except Exception:
            logger.error("SOCKS5连接异常", exc_info=True)
            try:
                writer.close()
            except Exception:
                pass

    async def start_server(self) -> asyncio.Task:
        try:
            server = await asyncio.start_server(
                self.serve_connection, self.listen_host, self.listen_port
            )
        except OSError as exc:
            if exc.errno == 98:
                raise exceptions.ServerError(
                    f"无法绑定{self.listen_host}:{self.listen_port}，是不是被占用了？"
                )
            raise exceptions.ServerError("无法启动SOCKS5代理") from exc
        return asyncio.create_task(server.serve_forever())


async def start_vessel_http_proxy(
    session: PHPSessionInterface,
    listen_host: str,
    listen_port: int,
) -> asyncio.Task:
    return await VesselHttpProxyServeConnection(
        session, listen_host, listen_port
    ).start_server()


async def start_vessel_socks5_proxy(
    session: PHPSessionInterface,
    listen_host: str,
    listen_port: int,
) -> asyncio.Task:
    return await VesselSocks5ServeConnection(
        session, listen_host, listen_port
    ).start_server()
