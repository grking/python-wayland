import errno
import socket
import struct
import threading
from unittest.mock import MagicMock, patch

import pytest

from wayland.constants import PROTOCOL_HEADER_SIZE
from wayland.unixsocket import UnixSocketConnection


def test_unixsocket_connection_error_handling():
    """Test UnixSocketConnection error handling during socket operations."""
    with patch("socket.socket") as mock_socket_class:
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        mock_socket.connect.side_effect = OSError("Connection failed")

        with pytest.raises(OSError, match="Connection failed"):
            UnixSocketConnection("/tmp/test_socket")


def test_unixsocket_run_method_oserror_handling():
    """Test UnixSocketConnection run method handles OSError exceptions correctly."""
    with patch("socket.socket") as mock_socket_class:
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        conn = UnixSocketConnection("/tmp/test_socket")

        mock_socket.recv.side_effect = OSError()
        mock_socket.recv.side_effect.errno = errno.EWOULDBLOCK

        conn.stop_event.set()

        conn.run()


def test_unixsocket_run_method_general_exception_handling():
    """Test UnixSocketConnection run method handles general exceptions correctly."""
    with patch("socket.socket") as mock_socket_class:
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        conn = UnixSocketConnection("/tmp/test_socket")

        mock_socket.recv.side_effect = ValueError("Unexpected error")

        conn.run()


def test_unixsocket_file_descriptor_extraction():
    """Test UnixSocketConnection file descriptor extraction from ancillary data."""
    with patch("socket.socket") as mock_socket_class:
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        conn = UnixSocketConnection("/tmp/test_socket")

        header = struct.pack("IHH", 1, 0, PROTOCOL_HEADER_SIZE + 4)
        message_data = b"test"

        mock_socket.recv.return_value = header

        fd_data = struct.pack("I", 42)
        ancdata = [(socket.SOL_SOCKET, socket.SCM_RIGHTS, fd_data)]
        mock_socket.recvmsg.return_value = (message_data, ancdata, 0, None)

        data, fd = conn._read()

        assert data == message_data
        assert fd == 42


def test_unixsocket_no_file_descriptor():
    """Test UnixSocketConnection when no file descriptor is present."""
    with patch("socket.socket") as mock_socket_class:
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        conn = UnixSocketConnection("/tmp/test_socket")

        header = struct.pack("IHH", 1, 0, PROTOCOL_HEADER_SIZE + 4)
        message_data = b"test"

        mock_socket.recv.return_value = header
        mock_socket.recvmsg.return_value = (message_data, [], 0, None)

        data, fd = conn._read()

        assert data == message_data
        assert fd is None


def test_unixsocket_empty_buffer_operations():
    """Test UnixSocketConnection buffer operations when buffers are empty."""
    with patch("socket.socket") as mock_socket_class:
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        conn = UnixSocketConnection("/tmp/test_socket")

        assert conn.get_next_message() is None
        assert conn.get_next_fd() is None


def test_unixsocket_sendmsg_with_ancillary():
    """Test UnixSocketConnection sendmsg with ancillary data."""
    with patch("socket.socket") as mock_socket_class:
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        conn = UnixSocketConnection("/tmp/test_socket")

        buffers = [b"test_data"]
        ancillary = [(socket.SOL_SOCKET, socket.SCM_RIGHTS, struct.pack("I", 42))]

        conn.sendmsg(buffers, ancillary)

        mock_socket.sendmsg.assert_called_once_with(buffers, ancillary)


def test_unixsocket_sendall():
    """Test UnixSocketConnection sendall method."""
    with patch("socket.socket") as mock_socket_class:
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        conn = UnixSocketConnection("/tmp/test_socket")

        test_data = b"test_message"
        conn.sendall(test_data)

        mock_socket.sendall.assert_called_once_with(test_data)


def test_unixsocket_threading_lifecycle():
    """Test UnixSocketConnection threading lifecycle management."""
    with patch("socket.socket") as mock_socket_class:
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        with patch.object(UnixSocketConnection, "start") as mock_start:
            conn = UnixSocketConnection("/tmp/test_socket")
            mock_start.assert_called_once()

        with patch.object(threading.Thread, "join") as mock_join:
            conn.stop()
            mock_join.assert_called_once()


def test_unixsocket_buffer_with_custom_size():
    """Test UnixSocketConnection with custom buffer size."""
    with patch("socket.socket") as mock_socket_class:
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        custom_buffer_size = 1024
        conn = UnixSocketConnection("/tmp/test_socket", buffer_size=custom_buffer_size)

        assert conn.buffer.maxlen == custom_buffer_size
        assert conn.fd_buffer.maxlen == custom_buffer_size


def test_unixsocket_read_with_fd_storage():
    """Test UnixSocketConnection read method stores file descriptors correctly."""
    with patch("socket.socket") as mock_socket_class:
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        conn = UnixSocketConnection("/tmp/test_socket")

        with patch.object(conn, "_read") as mock_read:
            mock_read.return_value = (b"test_data", 42)

            conn.read()

            assert len(conn.buffer) == 1
            assert conn.buffer[0] == b"test_data"
            assert len(conn.fd_buffer) == 1
            assert conn.fd_buffer[0] == 42


def test_unixsocket_read_without_fd():
    """Test UnixSocketConnection read method when no file descriptor is present."""
    with patch("socket.socket") as mock_socket_class:
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        conn = UnixSocketConnection("/tmp/test_socket")

        with patch.object(conn, "_read") as mock_read:
            mock_read.return_value = (b"test_data", None)

            conn.read()

            assert len(conn.buffer) == 1
            assert conn.buffer[0] == b"test_data"
            assert len(conn.fd_buffer) == 0
