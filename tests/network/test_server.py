import errno
import os
import socket
import unittest
from unittest.mock import Mock, patch, sentinel

from gi.repository import GLib
from mopidy.core import CoreProxy

from mopidy_mpd import network, uri_mapper
from tests import any_int


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.mock = Mock(spec=network.Server)

    @patch.object(network, "get_socket_address", new=Mock())
    def test_init_calls_create_server_socket(self):
        network.Server.__init__(
            self.mock,
            config={},
            core=Mock(spec=CoreProxy),
            uri_map=Mock(uri_mapper.MpdUriMapper),
            protocol=sentinel.protocol,
            host=sentinel.host,
            port=sentinel.port,
        )
        self.mock.create_server_socket.assert_called_once_with(
            sentinel.host, sentinel.port
        )
        self.mock.stop()

    @patch.object(network, "get_socket_address", new=Mock())
    def test_init_calls_get_socket_address(self):
        network.Server.__init__(
            self.mock,
            config={},
            core=Mock(spec=CoreProxy),
            uri_map=Mock(uri_mapper.MpdUriMapper),
            protocol=sentinel.protocol,
            host=sentinel.host,
            port=sentinel.port,
        )
        self.mock.create_server_socket.return_value = None
        network.get_socket_address.assert_called_once_with(sentinel.host, sentinel.port)
        self.mock.stop()

    @patch.object(network, "get_socket_address", new=Mock())
    def test_init_calls_register_server(self):
        sock = Mock(spec=socket.socket)
        sock.fileno.return_value = sentinel.fileno
        self.mock.create_server_socket.return_value = sock

        network.Server.__init__(
            self.mock,
            config={},
            core=Mock(spec=CoreProxy),
            uri_map=Mock(uri_mapper.MpdUriMapper),
            protocol=sentinel.protocol,
            host=sentinel.host,
            port=sentinel.port,
        )
        self.mock.register_server_socket.assert_called_once_with(sentinel.fileno)

    @patch.object(network, "get_socket_address", new=Mock())
    def test_init_fails_on_fileno_call(self):
        sock = Mock(spec=socket.socket)
        sock.fileno.side_effect = socket.error
        self.mock.create_server_socket.return_value = sock

        with self.assertRaises(socket.error):
            network.Server.__init__(
                self.mock,
                config={},
                core=Mock(spec=CoreProxy),
                uri_map=Mock(uri_mapper.MpdUriMapper),
                protocol=sentinel.protocol,
                host=sentinel.host,
                port=sentinel.port,
            )

    def test_init_stores_values_in_attributes(self):
        # This need to be a mock and no a sentinel as fileno() is called on it
        sock = Mock(spec=socket.socket)
        self.mock.create_server_socket.return_value = sock

        network.Server.__init__(
            self.mock,
            config={},
            core=Mock(spec=CoreProxy),
            uri_map=Mock(uri_mapper.MpdUriMapper),
            protocol=sentinel.protocol,
            host=str(sentinel.host),
            port=sentinel.port,
            max_connections=sentinel.max_connections,
            timeout=sentinel.timeout,
        )
        assert sentinel.protocol == self.mock.protocol
        assert sentinel.max_connections == self.mock.max_connections
        assert sentinel.timeout == self.mock.timeout
        assert sock == self.mock.server_socket
        assert (str(sentinel.host), sentinel.port) == self.mock.address

    def test_create_server_socket_no_port(self):
        with self.assertRaises(TypeError):
            network.Server.create_server_socket(self.mock, str(sentinel.host), None)

    def test_create_server_socket_invalid_port(self):
        with self.assertRaises(TypeError):
            network.Server.create_server_socket(
                self.mock, str(sentinel.host), str(sentinel.port)
            )

    @patch.object(network, "create_tcp_socket", spec=socket.socket)
    def test_create_server_socket_sets_up_listener(self, create_tcp_socket):
        sock = create_tcp_socket.return_value

        network.Server.create_server_socket(self.mock, str(sentinel.host), 1234)
        sock.setblocking.assert_called_once_with(False)
        sock.bind.assert_called_once_with((str(sentinel.host), 1234))
        sock.listen.assert_called_once_with(any_int)
        create_tcp_socket.assert_called_once()

    @patch.object(network, "create_unix_socket", spec=socket.socket)
    def test_create_server_socket_sets_up_listener_unix(self, create_unix_socket):
        sock = create_unix_socket.return_value

        network.Server.create_server_socket(
            self.mock, "unix:" + str(sentinel.host), sentinel.port
        )
        sock.setblocking.assert_called_once_with(False)
        sock.bind.assert_called_once_with(str(sentinel.host))
        sock.listen.assert_called_once_with(any_int)
        create_unix_socket.assert_called_once()

    @patch.object(network, "create_tcp_socket", new=Mock())
    def test_create_server_socket_fails(self):
        network.create_tcp_socket.side_effect = socket.error
        with self.assertRaises(socket.error):
            network.Server.create_server_socket(self.mock, str(sentinel.host), 1234)

    @patch.object(network, "create_unix_socket", new=Mock())
    def test_create_server_socket_fails_unix(self):
        network.create_unix_socket.side_effect = socket.error
        with self.assertRaises(socket.error):
            network.Server.create_server_socket(
                self.mock, "unix:" + str(sentinel.host), sentinel.port
            )

    @patch.object(network, "create_tcp_socket", new=Mock())
    def test_create_server_bind_fails(self):
        sock = network.create_tcp_socket.return_value
        sock.bind.side_effect = socket.error

        with self.assertRaises(socket.error):
            network.Server.create_server_socket(self.mock, str(sentinel.host), 1234)

    @patch.object(network, "create_unix_socket", new=Mock())
    def test_create_server_bind_fails_unix(self):
        sock = network.create_unix_socket.return_value
        sock.bind.side_effect = socket.error

        with self.assertRaises(socket.error):
            network.Server.create_server_socket(
                self.mock, "unix:" + str(sentinel.host), sentinel.port
            )

    @patch.object(network, "create_tcp_socket", new=Mock())
    def test_create_server_listen_fails(self):
        sock = network.create_tcp_socket.return_value
        sock.listen.side_effect = socket.error

        with self.assertRaises(socket.error):
            network.Server.create_server_socket(self.mock, str(sentinel.host), 1234)

    @patch.object(network, "create_unix_socket", new=Mock())
    def test_create_server_listen_fails_unix(self):
        sock = network.create_unix_socket.return_value
        sock.listen.side_effect = socket.error

        with self.assertRaises(socket.error):
            network.Server.create_server_socket(
                self.mock, "unix:" + str(sentinel.host), sentinel.port
            )

    @patch.object(os, "unlink", new=Mock())
    @patch.object(GLib, "source_remove", new=Mock())
    def test_stop_server_cleans_unix_socket(self):
        self.mock.watcher = Mock()
        sock = Mock()
        sock.family = socket.AF_UNIX
        self.mock.server_socket = sock
        network.Server.stop(self.mock)
        os.unlink.assert_called_once_with(sock.getsockname())

    @patch.object(GLib, "io_add_watch", new=Mock())
    def test_register_server_socket_sets_up_io_watch(self):
        network.Server.register_server_socket(self.mock, sentinel.fileno)
        GLib.io_add_watch.assert_called_once_with(
            sentinel.fileno, GLib.IO_IN, self.mock.handle_connection
        )

    def test_handle_connection(self):
        self.mock.accept_connection.return_value = (
            sentinel.sock,
            sentinel.addr,
        )
        self.mock.maximum_connections_exceeded.return_value = False

        assert network.Server.handle_connection(self.mock, sentinel.fileno, GLib.IO_IN)
        self.mock.accept_connection.assert_called_once_with()
        self.mock.maximum_connections_exceeded.assert_called_once_with()
        self.mock.init_connection.assert_called_once_with(sentinel.sock, sentinel.addr)
        assert self.mock.reject_connection.call_count == 0

    def test_handle_connection_exceeded_connections(self):
        self.mock.accept_connection.return_value = (
            sentinel.sock,
            sentinel.addr,
        )
        self.mock.maximum_connections_exceeded.return_value = True

        assert network.Server.handle_connection(self.mock, sentinel.fileno, GLib.IO_IN)
        self.mock.accept_connection.assert_called_once_with()
        self.mock.maximum_connections_exceeded.assert_called_once_with()
        self.mock.reject_connection.assert_called_once_with(
            sentinel.sock, sentinel.addr
        )
        assert self.mock.init_connection.call_count == 0

    def test_accept_connection(self):
        sock = Mock(spec=socket.socket)
        connected_sock = Mock(spec=socket.socket)
        sock.accept.return_value = (
            connected_sock,
            (sentinel.host, sentinel.port, sentinel.flow, sentinel.scope),
        )
        self.mock.server_socket = sock

        sock, addr = network.Server.accept_connection(self.mock)
        assert sock == connected_sock
        assert addr == (sentinel.host, sentinel.port)

    def test_accept_connection_unix(self):
        sock = Mock(spec=socket.socket)
        connected_sock = Mock(spec=socket.socket)
        connected_sock.family = socket.AF_UNIX
        connected_sock.getsockname.return_value = sentinel.sockname
        sock.accept.return_value = (connected_sock, sentinel.addr)
        self.mock.server_socket = sock

        sock, addr = network.Server.accept_connection(self.mock)
        assert connected_sock == sock
        assert (sentinel.sockname, None) == addr

    def test_accept_connection_recoverable_error(self):
        sock = Mock(spec=socket.socket)
        self.mock.server_socket = sock

        for error in (errno.EAGAIN, errno.EINTR):
            sock.accept.side_effect = OSError(error, "")
            with self.assertRaises(network.ShouldRetrySocketCallError):
                network.Server.accept_connection(self.mock)

    # TODO: decide if this should be allowed to propegate
    def test_accept_connection_unrecoverable_error(self):
        sock = Mock(spec=socket.socket)
        self.mock.server_socket = sock
        sock.accept.side_effect = socket.error
        with self.assertRaises(socket.error):
            network.Server.accept_connection(self.mock)

    def test_maximum_connections_exceeded(self):
        self.mock.max_connections = 10

        self.mock.number_of_connections.return_value = 11
        assert network.Server.maximum_connections_exceeded(self.mock)

        self.mock.number_of_connections.return_value = 10
        assert network.Server.maximum_connections_exceeded(self.mock)

        self.mock.number_of_connections.return_value = 9
        assert not network.Server.maximum_connections_exceeded(self.mock)

    @patch("pykka.ActorRegistry.get_by_class")
    def test_number_of_connections(self, get_by_class):
        self.mock.protocol = sentinel.protocol

        get_by_class.return_value = [1, 2, 3]
        assert network.Server.number_of_connections(self.mock) == 3

        get_by_class.return_value = []
        assert network.Server.number_of_connections(self.mock) == 0

    def test_reject_connection(self):
        sock = Mock(spec=socket.socket)

        network.Server.reject_connection(
            self.mock, sock, (sentinel.host, sentinel.port)
        )
        sock.close.assert_called_once_with()

    @patch.object(network, "format_address", new=Mock())
    @patch.object(network.logger, "warning", new=Mock())
    def test_reject_connection_message(self):
        sock = Mock(spec=socket.socket)
        network.format_address.return_value = sentinel.formatted

        network.Server.reject_connection(
            self.mock, sock, (sentinel.host, sentinel.port)
        )
        network.format_address.assert_called_once_with((sentinel.host, sentinel.port))
        network.logger.warning.assert_called_once_with(
            "Rejected connection from %s", sentinel.formatted
        )

    def test_reject_connection_error(self):
        sock = Mock(spec=socket.socket)
        sock.close.side_effect = socket.error

        network.Server.reject_connection(
            self.mock, sock, (sentinel.host, sentinel.port)
        )
        sock.close.assert_called_once_with()
