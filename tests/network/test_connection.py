import asyncio
import errno
import logging
import socket
import unittest
from unittest.mock import Mock, patch, sentinel

import pykka

from mopidy_mpd import network, uri_mapper
from tests import IsA, any_int, any_unicode


class ConnectionTest(unittest.TestCase):
    def setUp(self):
        self.mock = Mock(spec=network.Connection)
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def create_connection(self):
        conn = network.Connection(
            config={},  # type: ignore
            core=Mock(),
            uri_map=Mock(spec=uri_mapper.MpdUriMapper),
            protocol=Mock(spec=network.LineProtocol),  # type: ignore
            sock=Mock(spec=socket.SocketType),
            addr=(sentinel.host, sentinel.port),
            timeout=1,
            loop=self.loop,
        )

        conn._sock = Mock(spec=socket.SocketType)
        conn.actor_ref = Mock()
        return conn

    def test_init_ensure_nonblocking_io(self):
        sock = Mock(spec=socket.SocketType)

        network.Connection.__init__(
            self.mock,
            config={},  # type: ignore
            core=Mock(),
            uri_map=Mock(spec=uri_mapper.MpdUriMapper),
            protocol=Mock(spec=network.LineProtocol),  # type: ignore
            sock=sock,
            addr=(sentinel.host, sentinel.port),
            timeout=sentinel.timeout,
            loop=self.loop,
        )
        sock.setblocking.assert_called_once_with(False)

    def test_init_starts_actor(self):
        protocol = Mock(spec=network.LineProtocol)

        network.Connection.__init__(
            self.mock,
            config={},  # type: ignore
            core=Mock(),
            uri_map=Mock(spec=uri_mapper.MpdUriMapper),
            protocol=protocol,  # type: ignore
            sock=Mock(spec=socket.SocketType),
            addr=(sentinel.host, sentinel.port),
            timeout=sentinel.timeout,
            loop=self.loop,
        )
        protocol.start.assert_called_once()

    def test_init_stores_values_in_attributes(self):
        addr = (sentinel.host, sentinel.port)
        protocol = Mock(spec=network.LineProtocol)
        sock = Mock(spec=socket.SocketType)

        network.Connection.__init__(
            self.mock,
            config={},  # type: ignore
            core=Mock(),
            uri_map=Mock(spec=uri_mapper.MpdUriMapper),
            protocol=protocol,  # type: ignore
            sock=sock,
            addr=addr,
            timeout=sentinel.timeout,
            loop=self.loop,
        )
        assert sock == self.mock._sock
        assert protocol == self.mock.protocol
        assert sentinel.timeout == self.mock.timeout
        assert sentinel.host == self.mock.host
        assert sentinel.port == self.mock.port

    def test_init_handles_ipv6_addr(self):
        addr = (
            sentinel.host,
            sentinel.port,
            sentinel.flowinfo,
            sentinel.scopeid,
        )
        protocol = Mock(spec=network.LineProtocol)
        sock = Mock(spec=socket.SocketType)

        network.Connection.__init__(
            self.mock,
            config={},  # type: ignore
            core=Mock(),
            uri_map=Mock(spec=uri_mapper.MpdUriMapper),
            protocol=protocol,  # type: ignore
            sock=sock,
            addr=addr,
            timeout=sentinel.timeout,
            loop=self.loop,
        )
        assert sentinel.host == self.mock.host
        assert sentinel.port == self.mock.port

    def test_stop_closes_socket(self):
        self.mock.stopping = False
        self.mock.actor_ref = Mock()
        self.mock._sock = Mock(spec=socket.SocketType)

        network.Connection.stop(self.mock, sentinel.reason)
        self.mock._sock.close.assert_called_once_with()

    def test_stop_closes_socket_error(self):
        self.mock.stopping = False
        self.mock.actor_ref = Mock()
        self.mock._sock = Mock(spec=socket.SocketType)
        self.mock._sock.close.side_effect = socket.error

        network.Connection.stop(self.mock, sentinel.reason)
        self.mock._sock.close.assert_called_once_with()

    def test_stop_stops_actor(self):
        self.mock.stopping = False
        self.mock.actor_ref = Mock()
        self.mock._sock = Mock(spec=socket.SocketType)

        network.Connection.stop(self.mock, sentinel.reason)
        self.mock.actor_ref.stop.assert_called_once_with(block=False)

    def test_stop_handles_actor_already_being_stopped(self):
        self.mock.stopping = False
        self.mock.actor_ref = Mock()
        self.mock.actor_ref.stop.side_effect = pykka.ActorDeadError()
        self.mock._sock = Mock(spec=socket.SocketType)

        network.Connection.stop(self.mock, sentinel.reason)
        self.mock.actor_ref.stop.assert_called_once_with(block=False)

    def test_stop_sets_stopping_to_true(self):
        self.mock.stopping = False
        self.mock.actor_ref = Mock()
        self.mock._sock = Mock(spec=socket.SocketType)

        network.Connection.stop(self.mock, sentinel.reason)
        assert self.mock.stopping is True

    def test_stop_does_not_proceed_when_already_stopping(self):
        self.mock.stopping = True
        self.mock.actor_ref = Mock()
        self.mock._sock = Mock(spec=socket.SocketType)

        network.Connection.stop(self.mock, sentinel.reason)
        assert self.mock.actor_ref.stop.call_count == 0
        assert self.mock._sock.close.call_count == 0

    @patch.object(network.logger, "log", new=Mock())
    def test_stop_logs_reason(self):
        self.mock.stopping = False
        self.mock.actor_ref = Mock()
        self.mock._sock = Mock(spec=socket.SocketType)

        network.Connection.stop(self.mock, sentinel.reason)
        network.logger.log.assert_called_once_with(logging.DEBUG, sentinel.reason)

    @patch.object(network.logger, "log", new=Mock())
    def test_stop_logs_reason_with_level(self):
        self.mock.stopping = False
        self.mock.actor_ref = Mock()
        self.mock._sock = Mock(spec=socket.SocketType)

        network.Connection.stop(self.mock, sentinel.reason, level=sentinel.level)
        network.logger.log.assert_called_once_with(sentinel.level, sentinel.reason)

    @patch.object(network.logger, "log", new=Mock())
    def test_stop_logs_that_it_is_calling_itself(self):
        self.mock.stopping = True
        self.mock.actor_ref = Mock()
        self.mock._sock = Mock(spec=socket.SocketType)

        network.Connection.stop(self.mock, sentinel.reason)
        network.logger.log(any_int, any_unicode)

    def test_queue_send_calls_send(self):
        conn = self.create_connection()
        conn._loop = Mock(spec=asyncio.AbstractEventLoop)
        conn.send_buffer = b""

        asyncio.run(conn.queue_send(b"data"))
        conn._loop.sock_sendall.assert_called_once_with(  # type: ignore
            IsA(Mock), b"data"
        )
        assert conn.send_buffer == b""

    def test_recv_callback_sends_data_to_actor(self):
        conn = self.create_connection()
        conn._sock.recv.return_value = b"data"  # type: ignore

        assert asyncio.run(conn.recv())
        conn.actor_ref.tell.assert_called_once_with({"received": b"data"})

    def test_recv_callback_handles_dead_actors(self):
        conn = self.create_connection()
        conn._sock.recv.return_value = b"data"  # type: ignore
        conn.actor_ref.tell.side_effect = pykka.ActorDeadError()

        assert not asyncio.run(conn.recv())
        conn.actor_ref.stop.assert_called_once()

    def test_recv_callback_gets_no_data(self):
        conn = self.create_connection()
        conn._sock.recv.return_value = b""  # type: ignore

        assert not asyncio.run(conn.recv())
        assert conn.actor_ref.mock_calls == [
            ("tell", ({"close": True},), {}),
        ]

    def test_recv_callback_recoverable_error(self):
        conn = self.create_connection()
        conn._loop = Mock(spec=asyncio.AbstractEventLoop)

        for error in (errno.EWOULDBLOCK, errno.EINTR):
            conn._loop.sock_recv.side_effect = OSError(error, "")  # type: ignore
            assert asyncio.run(conn.recv())
            assert conn.actor_ref.stop.call_count == 0

    def test_recv_callback_unrecoverable_error(self):
        conn = self.create_connection()
        conn._loop = Mock(spec=asyncio.AbstractEventLoop)
        conn._loop.sock_recv.side_effect = socket.error

        assert not asyncio.run(conn.recv())
        conn.actor_ref.stop.assert_called_once()

    def test_send_callback_sends_all_data(self):
        conn = self.create_connection()
        conn.send_buffer = b"data"
        conn._loop = Mock(spec=asyncio.AbstractEventLoop)
        conn._loop.sock_sendall.return_value = None  # type: ignore

        asyncio.run(conn.send(conn.send_buffer))
        conn._loop.sock_sendall.assert_called_once_with(  # type: ignore
            IsA(Mock), b"data"
        )

    def test_send_recoverable_error(self):
        conn = self.create_connection()
        conn._loop = Mock(spec=asyncio.AbstractEventLoop)

        for error in (errno.EWOULDBLOCK, errno.EINTR):
            conn._loop.sock_sendall.side_effect = OSError(error, "")

            asyncio.run(conn.send(b"data"))
            assert self.mock.stop.call_count == 0

    def test_send_calls_socket_send(self):
        conn = self.create_connection()
        conn._sock.send.return_value = 4

        asyncio.run(conn.send(b"data"))
        conn._sock.send.assert_called_once_with(b"data")

    def test_timeout_callback(self):
        self.mock.timeout = 10

        assert not network.Connection.timeout_callback(self.mock)
        self.mock.stop.assert_called_once_with(any_unicode)

    def test_str(self):
        self.mock.host = "foo"
        self.mock.port = 999

        assert network.Connection.__str__(self.mock) == "[foo]:999"

    def test_str_without_port(self):
        self.mock.host = "foo"
        self.mock.port = None

        assert network.Connection.__str__(self.mock) == "[foo]"
