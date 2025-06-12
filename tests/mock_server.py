import socket
import struct
import threading
import time
from queue import Queue

from wayland.constants import PROTOCOL_HEADER_SIZE
from wayland.message import pack_argument
from wayland.serialiser import Message, MessageType


class MockServer:
    def __init__(self, sock_path):
        self.sock_path = sock_path
        self.server_sock = None
        self.client_sock = None
        self.thread = None
        self.running = False
        self.requests = Queue()

    def start(self):
        self.server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server_sock.settimeout(1)
        self.server_sock.bind(self.sock_path)
        self.server_sock.listen(1)
        self.running = True

        self.thread = threading.Thread(target=self._run)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        if self.client_sock:
            try:
                self.client_sock.shutdown(socket.SHUT_RDWR)
                self.client_sock.close()
            except OSError:
                pass
        if self.server_sock:
            self.server_sock.close()

    def _run(self):
        try:
            self.client_sock, _ = self.server_sock.accept()
            self.client_sock.settimeout(0.1)
        except socket.timeout:
            return

        while self.running:
            try:
                header = self.client_sock.recv(PROTOCOL_HEADER_SIZE)
                if not header:
                    break
                object_id, opcode, size = struct.unpack("IHH", header)
                data = (
                    self.client_sock.recv(size - PROTOCOL_HEADER_SIZE)
                    if size > PROTOCOL_HEADER_SIZE
                    else b""
                )

                message = Message.create(
                    timestamp=time.time(),
                    msgtype=MessageType.REQUEST,
                    signature="",
                    interface="",
                    method_name="",
                    object_id=object_id,
                    args={},
                    opcode=opcode,
                    packet=header + data,
                    key=0,
                )

                self.requests.put(
                    {
                        "object_id": object_id,
                        "opcode": opcode,
                        "data": data,
                        "message": message,
                    }
                )
            except socket.timeout:
                continue
            except (BrokenPipeError, ConnectionResetError, OSError):
                break

    def send_event(self, object_id, opcode, data):
        header = struct.pack("IHH", object_id, opcode, len(data) + PROTOCOL_HEADER_SIZE)
        self.client_sock.sendall(header + data)

    def _pack_argument(self, packet, arg_type, value):
        return pack_argument(packet, arg_type, value)

    def send_global_event(self, registry_object_id, name, interface, version):
        packet = b""
        packet, _ = self._pack_argument(packet, "uint", name)
        packet, _ = self._pack_argument(packet, "string", interface)
        packet, _ = self._pack_argument(packet, "uint", version)
        self.send_event(registry_object_id, 0, packet)

    def send_capabilities_event(self, seat_object_id, capabilities):
        packet = b""
        packet, _ = self._pack_argument(packet, "uint", capabilities)
        self.send_event(seat_object_id, 0, packet)

    def send_global_remove_event(self, registry_object_id, name):
        packet = b""
        packet, _ = self._pack_argument(packet, "uint", name)
        self.send_event(registry_object_id, 1, packet)

    def get_request(self, timeout=1):
        return self.requests.get(timeout=timeout)
