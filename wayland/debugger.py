# Copyright (c) 2024-2025 Graham R King
# Licensed under the MIT License. See LICENSE file for details.
from __future__ import annotations

import contextlib
import json
import os
import socket
import threading
from collections import deque
from dataclasses import dataclass
from typing import Iterator

from wayland.client.package import get_package_version
from wayland.constants import PROTOCOL_DEBUG_SOCKET_NAME
from wayland.log import log
from wayland.serialiser import Message, MessageEncoder, MessageType
from wayland.singleton import singleton


@dataclass
class ClientState:
    socket: socket.socket
    is_streaming: bool = False


@singleton
class Debugger:
    """
    A Wayland protocol debugger.

    Runs an interactive server on an abstract file socket for
    debug clients to obtain information for display.
    """

    def __init__(self, max_log_size: int = 10000):
        self._msgdata = deque(maxlen=max_log_size)
        self._socket_path = None
        self._clients: dict[socket.socket, ClientState] = {}
        self._clients_lock = threading.Lock()
        self._running = False
        self._msg_id = 1
        self._server_sock = None
        self._listening_thread = None
        self._msg_lock = threading.Lock()

    def start_debug_server(self):
        from wayland.debugger_commands import DebuggerCommandHandler

        self._command_handler = DebuggerCommandHandler(self)
        self._socket_listen()

    def _socket_listen(self):
        socket_names = [
            os.getenv("PYTHON_WAYLAND_DEBUG_SOCKET", PROTOCOL_DEBUG_SOCKET_NAME),
            f"{PROTOCOL_DEBUG_SOCKET_NAME}-{os.getpid()}",
        ]

        for socket_name in socket_names:
            self._server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                self._server_sock.bind(f"\0{socket_name}")
                self._server_sock.listen(5)
                self._running = True
                self._socket_path = socket_name
                break
            except OSError as e:
                log.warning(e)

        if not self._running:
            log.error("Failed to start debugger.")
            return

        self._listening_thread = threading.Thread(
            target=self._accept_connections, daemon=True, name="DebuggerListener"
        )
        self._listening_thread.start()
        return self._socket_path

    def _stop_stream(self):
        self._running = False

        if self._server_sock:
            with contextlib.suppress(OSError):
                self._server_sock.close()
                self._server_sock = None

        if self._listening_thread and self._listening_thread.is_alive():
            with contextlib.suppress(OSError, RuntimeError):
                self._listening_thread.join(timeout=3.0)

        with self._clients_lock:
            clients_to_cleanup = list(self._clients.keys())

        for client_sock in clients_to_cleanup:
            self._cleanup_client(client_sock)

    def _accept_connections(self):
        while self._running:
            try:
                if not self._server_sock:
                    break
                client_sock, _ = self._server_sock.accept()
                log.debug("Accepted new debug connection.")

                with self._clients_lock:
                    self._clients[client_sock] = ClientState(client_sock)

                handler_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_sock,),
                    daemon=True,
                    name=f"DebuggerClientHandler-{client_sock.fileno()}",
                )
                handler_thread.start()

            except OSError as e:
                if self._running:
                    log.error(f"Socket error accepting connection: {e}")
                break
            except (ValueError, RuntimeError) as e:
                if self._running:
                    log.error(f"Unexpected error accepting connection: {e}")
                break

    def _handle_command(self, client_sock: socket.socket, command: str) -> bool:
        return self._command_handler.handle_command(client_sock, command)

    def has_range(self, start_range, end_range):
        """Does the message data we have include keys in the given range"""

        with self._msg_lock:
            if not len(self._msgdata):
                return False

            # Our msg data has contiguous integer keys
            start_key = self._msgdata[0].key
            end_key = self._msgdata[-1].key
            if (start_range >= start_key and start_range <= end_key) or (
                end_range <= end_key and end_range >= start_key
            ):
                # We have at least some of this data range
                return True

            return False

    def get_message_data_by_range(self, start_range: int, end_range: int) -> None:
        # Do we have this data?
        have = self.has_range(start_range, end_range)
        if not have:
            return

        with self._msg_lock:
            start_key = self._msgdata[0].key
            end_key = self._msgdata[-1].key
            offset = 0 if start_range < start_key else start_range - start_key
            count = (end_range - start_range) + 1
            last_item = offset + count
            if last_item > end_key:
                last_item = end_key
            return [self._msgdata[i] for i in range(offset, last_item)]

    def get_client_streaming_status(self, client_sock):
        """Check if a client is in streaming mode."""
        with self._clients_lock:
            return (
                client_sock in self._clients and self._clients[client_sock].is_streaming
            )

    def set_client_streaming(self, client_sock, *, streaming: bool):
        """Set the streaming status for a client."""
        with self._clients_lock:
            if client_sock in self._clients:
                self._clients[client_sock].is_streaming = streaming
                return True
            return False

    def _handle_client(self, client_sock: socket.socket):
        try:
            self._send_welcome_message(client_sock)
            self._client_command_loop(client_sock)
        finally:
            self._cleanup_client(client_sock)

    def send_text(self, client_sock: socket.socket, msg):
        """Send an informational text message to a specific client"""
        try:
            if not msg.endswith("\n"):
                msg = f"{msg}\n"
            client_sock.sendall(msg.encode("utf-8"))
        except OSError:
            return False
        else:
            return True

    def send_data(self, client_sock: socket.socket, msg, msgtype="debug"):
        """Send some data to a specific client"""
        try:
            msg = self.serialise_message(msg, msgtype)
            # Already prefixed by the serialiser
            client_sock.sendall(msg)
        except OSError:
            return False
        else:
            return True

    def _send_welcome_message(self, client_sock: socket.socket):
        try:
            version = get_package_version()
        except ImportError:
            version = "unknown"
        self.send_text(client_sock, f"python wayland debugger {version}")

    def _client_command_loop(self, client_sock: socket.socket):
        buffer = ""

        while self._running and client_sock.fileno() != -1:
            try:
                client_sock.settimeout(1.0)
                data_bytes = client_sock.recv(1024)
                client_sock.settimeout(None)

                if not data_bytes:
                    break

                try:
                    # Add new data to buffer
                    buffer += data_bytes.decode()
                except UnicodeDecodeError:
                    continue

                # Process complete lines
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    command = line.strip()
                    if command and not self._handle_command(client_sock, command):
                        return

                # buffer now contains any partial line

            except socket.timeout:
                continue
            except (OSError, ConnectionResetError, BrokenPipeError) as e:
                log.info(f"Client socket/connection error in _handle_client: {e}")
                break

    def _cleanup_client(self, client_sock: socket.socket):
        with self._clients_lock:
            self._clients.pop(client_sock, None)

        with contextlib.suppress(OSError):
            client_sock.shutdown(socket.SHUT_RDWR)
            client_sock.close()

    def set_max_size(self, max_log_size: int) -> None:
        """
        Changes the maximum number of entries in the debug log.
        """
        with self._msg_lock:
            self._msgdata = deque(self._msgdata, max_log_size)

    def _log(self, msg: Message) -> None:
        """Save the message data and send to streaming clients."""
        with self._msg_lock:
            self._msgdata.append(msg)
        self._send_to_streaming_clients(msg)

    def serialise_message(self, msg, msgtype="debug"):
        return (
            f"DATA/{msgtype}: " + json.dumps(msg, cls=MessageEncoder) + "\n"
        ).encode("utf-8")

    def _send_to_streaming_clients(self, message: Message):
        with self._clients_lock:
            streaming_clients = [
                client_state.socket
                for client_state in self._clients.values()
                if client_state.is_streaming
            ]

        if not streaming_clients:
            return

        failed_clients = [
            client_sock
            for client_sock in streaming_clients
            if not self.send_data(client_sock, message)
        ]

        for client_sock in failed_clients:
            self._cleanup_client(client_sock)

    def log(self, msg) -> None:
        """Log an Event or Request."""
        # Received Proxy.Event or Proxy.Request instances

        with self._msg_lock:
            key = self._msg_id
            self._msg_id += 1

        msgtype = MessageType.EVENT if msg.event else MessageType.REQUEST
        signature = ""
        msg = Message.create(
            None,
            msgtype,
            signature,
            msg.interface,
            msg.name,
            msg.object_id,
            msg.kwargs,
            msg.opcode,
            msg.packet,
            key,
        )
        self._log(msg)

    def get_event_count(self):
        return sum(1 for msg in self if msg.msgtype == MessageType.EVENT)

    def __getitem__(self, index):
        with self._msg_lock:
            if isinstance(index, slice):
                # For simple slices with step=1
                start, stop, step = index.indices(len(self._msgdata))
                if step == 1:
                    from itertools import islice

                    return list(islice(self._msgdata, start, stop))
                msg = "Complex slicing not implemented"
                raise NotImplementedError(msg)
            return self._msgdata[index]

    def __len__(self) -> int:
        with self._msg_lock:
            return len(self._msgdata)

    def __iter__(self) -> Iterator[Message]:
        with self._msg_lock:
            return iter(self._msgdata)

    def clear(self):
        with self._msg_lock:
            self._msgdata.clear()
