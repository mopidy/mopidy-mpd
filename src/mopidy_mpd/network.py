from __future__ import annotations

import asyncio
import contextlib
import errno
import logging
import os
import re
import socket
import sys
import threading
from typing import TYPE_CHECKING, Any, Never, Optional

import pykka

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from collections.abc import Generator
    from types import TracebackType

    from mopidy.core import CoreProxy
    from mopidy_mpd import types
    from mopidy_mpd.session import MpdSession, MpdSessionKwargs
    from mopidy_mpd.types import SocketAddress
    from mopidy_mpd.uri_mapper import MpdUriMapper

CONTROL_CHARS = dict.fromkeys(range(32))


def get_systemd_socket() -> socket.socket | None:
    """Attempt to get a socket from systemd."""
    fdnames = os.environ.get("LISTEN_FDNAMES", "").split(":")
    if "mpd" not in fdnames:
        return None
    fd = fdnames.index("mpd") + 3  # 3 is the first systemd file handle
    return socket.socket(fileno=fd)


def get_unix_socket_path(socket_path: str) -> str | None:
    match = re.search("^unix:(.*)", socket_path)
    if not match:
        return None
    return match.group(1)


def is_unix_socket(sock: socket.socket) -> bool:
    """Check if the provided socket is a Unix domain socket"""
    if hasattr(socket, "AF_UNIX"):
        return sock.family == socket.AF_UNIX
    return False


def get_socket_address(host: str, port: int) -> tuple[str, int | None]:
    unix_socket_path = get_unix_socket_path(host)
    if unix_socket_path is not None:
        return (unix_socket_path, None)
    return (host, port)


class ShouldRetrySocketCallError(Exception):
    """Indicate that attempted socket call should be retried"""


def try_ipv6_socket() -> bool:
    """Determine if system really supports IPv6"""
    if not socket.has_ipv6:
        return False
    try:
        socket.socket(socket.AF_INET6).close()
    except OSError as exc:
        logger.debug(
            f"Platform supports IPv6, but socket creation failed, disabling: {exc}"
        )
        return False
    else:
        return True


#: Boolean value that indicates if creating an IPv6 socket will succeed.
has_ipv6 = try_ipv6_socket()


def create_tcp_socket() -> socket.socket:
    """Create a TCP socket with or without IPv6 depending on system support"""
    if has_ipv6:
        sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        # Explicitly configure socket to work for both IPv4 and IPv6
        if hasattr(socket, "IPPROTO_IPV6"):
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        elif sys.platform == "win32":  # also match 64bit windows.
            # Python 2.7 on windows does not have the IPPROTO_IPV6 constant
            # Use values extracted from Windows Vista/7/8's header
            sock.setsockopt(41, 27, 0)
    else:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    return sock


def create_unix_socket() -> socket.socket:
    """Create a Unix domain socket"""
    return socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)


def format_address(address: SocketAddress) -> str:
    """Format socket address for display."""
    host, port = address[:2]
    if port is not None:
        return f"[{host}]:{port}"
    return f"[{host}]"


def format_hostname(hostname: str) -> str:
    """Format hostname for display."""
    if has_ipv6 and re.match(r"\d+.\d+.\d+.\d+", hostname) is not None:
        hostname = f"::ffff:{hostname}"
    return hostname


class Server:
    """Setup listener and register it with the asyncio loop."""

    def __init__(  # noqa: PLR0913
        self,
        *,
        config: types.Config,
        core: CoreProxy,
        uri_map: MpdUriMapper,
        protocol: type[MpdSession],
        host: str,
        port: int,
        max_connections: int = 5,
        timeout: int = 30,
    ) -> None:
        self.config = config
        self.core = core
        self.uri_map = uri_map
        self.protocol = protocol

        self.max_connections = max_connections
        self.timeout = timeout
        self.server_socket = self.create_server_socket(host, port)
        self.address = get_socket_address(host, port)
        self._should_stop = asyncio.Event()

    def create_server_socket(self, host: str, port: int) -> socket.socket:
        sock = get_systemd_socket()
        if sock is not None:
            return sock

        socket_path = get_unix_socket_path(host)
        if socket_path is not None:  # host is a path so use unix socket
            sock = create_unix_socket()
            sock.bind(socket_path)
        else:
            # ensure the port is supplied
            if not (port and isinstance(port, int)):
                raise TypeError(f"Expected an integer, not {port!r}")
            sock = create_tcp_socket()
            sock.bind((host, port))

        sock.setblocking(False)  # noqa: FBT003
        sock.listen(1)
        return sock

    def stop(self) -> None:
        if is_unix_socket(self.server_socket):
            unix_socket_path = self.server_socket.getsockname()
        else:
            unix_socket_path = None

        self.server_socket.shutdown(socket.SHUT_RDWR)
        self.server_socket.close()

        # clean up the socket file
        if unix_socket_path is not None:
            os.unlink(unix_socket_path)  # noqa: PTH108

        self._should_stop.set()

    def handle_connection(
        self,
        client: socket.socket,
        addr: SocketAddress,
        loop: asyncio.AbstractEventLoop,
    ) -> bool:
        if is_unix_socket(client):
            addr = (client.getsockname(), None)
        if self.maximum_connections_exceeded():
            self.reject_connection(client, addr, reason="Maximum connections exceeded")
        else:
            self.init_connection(client, addr, loop)
        return True

    def maximum_connections_exceeded(self) -> bool:
        return (
            self.max_connections is not None
            and self.number_of_connections() >= self.max_connections
        )

    def number_of_connections(self) -> int:
        return len(pykka.ActorRegistry.get_by_class(self.protocol))

    def reject_connection(
        self, sock: socket.socket, addr: SocketAddress, reason: str = ""
    ) -> None:
        logger.warning("Rejected connection from %s: %s", format_address(addr), reason)
        with contextlib.suppress(OSError):
            sock.close()

    def init_connection(
        self, sock: socket.socket, addr: SocketAddress, loop: asyncio.AbstractEventLoop
    ) -> None:
        conn = Connection(
            config=self.config,
            core=self.core,
            uri_map=self.uri_map,
            protocol=self.protocol,
            sock=sock,
            addr=addr,
            timeout=self.timeout,
            loop=loop,
        )

        asyncio.create_task(conn.serve())

    async def wait_stop(self, timeout: Optional[float] = None) -> None:
        await asyncio.wait_for(self._should_stop.wait(), timeout=timeout)

    def should_stop(self) -> bool:
        return self._should_stop.is_set()

    async def run(self) -> None:
        loop = asyncio.get_event_loop()
        self._should_stop.clear()
        wait_stop = loop.create_task(self.wait_stop())

        while not self.should_stop():
            try:
                tasks = [
                    loop.create_task(loop.sock_accept(self.server_socket)),
                    wait_stop,
                ]

                await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

                if tasks[1].done():
                    tasks[1].result()
                    break

                try:
                    client, addr = tasks[0].result()
                    self.handle_connection(client, addr, loop)
                except OSError as exc:
                    if exc.errno in (errno.EBADF, errno.ENOTSOCK):
                        continue
                    raise exc
            except OSError as exc:
                if exc.errno in (errno.EAGAIN, errno.EINTR):
                    continue
                raise exc


class Connection:
    host: str
    port: int | None

    def __init__(  # noqa: PLR0913
        self,
        *,
        config: types.Config,
        core: CoreProxy,
        uri_map: MpdUriMapper,
        protocol: type[MpdSession],
        sock: socket.socket,
        addr: SocketAddress,
        timeout: int,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        sock.setblocking(False)  # noqa: FBT003

        self.host, self.port = addr[:2]

        self._sock = sock
        self._loop = loop
        self.protocol = protocol
        self.timeout = timeout

        self.send_lock = threading.Lock()
        self.send_buffer = b""

        self.stopping = False

        protocol_kwargs: MpdSessionKwargs = {
            "config": config,
            "core": core,
            "uri_map": uri_map,
            "connection": self,
            "loop": loop,
        }
        self.actor_ref = self.protocol.start(**protocol_kwargs)

    async def recv(self) -> bool:
        try:
            task = asyncio.create_task(self._loop.sock_recv(self._sock, 4096))
            tasks, _ = await asyncio.wait(
                [task], timeout=self.timeout, return_when=asyncio.FIRST_COMPLETED
            )

            if not (tasks and task in tasks):
                self.stop(f"Client inactive for {self.timeout:d}s; closing connection")
                return False

            data = task.result()
        except OSError as exc:
            if exc.errno in (errno.EWOULDBLOCK, errno.EINTR):
                return True
            self.stop(f"Unexpected client error: {exc}")
            return False

        if not data:
            self.actor_ref.tell({"close": True})
            return False

        try:
            self.actor_ref.tell({"received": data})
        except pykka.ActorDeadError:
            self.stop("Actor is dead.")
            return False

        return True

    async def serve(self) -> None:
        while not self.stopping:
            should_continue = await self.recv()
            if not should_continue:
                break

    def stop(self, reason: str, level: int = logging.DEBUG) -> None:
        if self.stopping:
            logger.log(level, "Already stopping: %s", reason)
            return

        self.stopping = True

        logger.log(level, reason)

        with contextlib.suppress(pykka.ActorDeadError):
            self.actor_ref.stop(block=False)

        with contextlib.suppress(OSError):
            self._sock.close()

    async def queue_send(self, data: bytes) -> None:
        """Try to send data to client exactly as is and queue rest."""
        with self.send_lock:
            task = asyncio.create_task(self.send(self.send_buffer + data))
            await asyncio.wait({task}, timeout=self.timeout)
            self.send_buffer = b""

    async def send(self, data: bytes) -> None:
        """Send data to client."""
        try:
            await self._loop.sock_sendall(self._sock, data)
        except OSError as exc:
            if exc.errno in (errno.EWOULDBLOCK, errno.EINTR):
                return
            self.stop(f"Unexpected client error: {exc}")

    def timeout_callback(self) -> bool:
        self.stop(f"Client inactive for {self.timeout:d}s; closing connection")
        return False

    def __str__(self) -> str:
        return format_address((self.host, self.port))


class LineProtocol(pykka.ThreadingActor):
    """
    Base class for handling line based protocols.

    Takes care of receiving new data from server's client code, decoding and
    then splitting data along line boundaries.
    """

    #: Line terminator to use for outputed lines.
    terminator = b"\n"

    #: Regex to use for spliting lines.
    delimiter = re.compile(rb"\r?\n")

    #: What encoding to expect incoming data to be in.
    encoding = "utf-8"

    def __init__(self, connection: Connection) -> None:
        super().__init__()
        self.connection = connection
        self.prevent_timeout = False
        self.recv_buffer = b""

    @property
    def host(self) -> str:
        return self.connection.host

    @property
    def port(self) -> int | None:
        return self.connection.port

    def on_line_received(self, line: str) -> None:
        """
        Called whenever a new line is found.

        Should be implemented by subclasses.
        """
        raise NotImplementedError

    def on_receive(self, message: dict[str, Any]) -> None:
        """Handle messages with new data from server."""
        if "close" in message:
            self.connection.stop("Client most likely disconnected.")
            return

        if "received" not in message:
            return

        self.recv_buffer += message["received"]

        for line in self.parse_lines():
            decoded_line = self.decode(line)
            if decoded_line is not None:
                self.on_line_received(decoded_line)

    def on_failure(
        self,
        exception_type: type[BaseException] | None,
        exception_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Clean up connection resouces when actor fails."""
        super().on_failure(exception_type, exception_value, traceback)
        self.connection.stop("Actor failed.")
        logger.exception("Actor failed.", exc_info=exception_value)

    def on_stop(self) -> None:
        """Clean up connection resouces when actor stops."""
        self.connection.stop("Actor is shutting down.")

    def parse_lines(self) -> Generator[bytes, Any, None]:
        """Consume new data and yield any lines found."""
        while re.search(self.terminator, self.recv_buffer):
            line, self.recv_buffer = self.delimiter.split(self.recv_buffer, 1)
            yield line

    def encode(self, line: str) -> bytes:
        """
        Handle encoding of line.

        Can be overridden by subclasses to change encoding behaviour.
        """
        try:
            return line.encode(self.encoding)
        except UnicodeError:
            logger.warning(
                "Stopping actor due to encode problem, data "
                "supplied by client was not valid %s",
                self.encoding,
            )
            self.stop()
            return Never  # pyright: ignore[reportReturnType]

    def decode(self, line: bytes) -> str:
        """
        Handle decoding of line.

        Can be overridden by subclasses to change decoding behaviour.
        """
        try:
            return line.decode(self.encoding)
        except UnicodeError:
            logger.warning(
                "Stopping actor due to decode problem, data "
                "supplied by client was not valid %s",
                self.encoding,
            )
            self.stop()
            return Never  # pyright: ignore[reportReturnType]

    def join_lines(self, lines: list[str]) -> str:
        if not lines:
            return ""
        line_terminator = self.decode(self.terminator)
        return line_terminator.join(lines) + line_terminator

    async def send_lines(self, lines: list[str]) -> None:
        """
        Send array of lines to client via connection.

        Join lines using the terminator that is set for this class, encode it
        and send it to the client.
        """
        if not lines:
            return

        # Remove all control characters (first 32 ASCII characters)
        lines = [line.translate(CONTROL_CHARS) for line in lines]

        data = self.join_lines(lines)
        await self.connection.queue_send(self.encode(data))
