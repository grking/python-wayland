# Copyright (c) 2024 Graham R King
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice (including the
# next paragraph) shall be included in all copies or substantial
# portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT.  IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from __future__ import annotations

import os
import string
import struct
import threading
import time
from typing import Any, Callable

from wayland.constants import MAX_EVENT_RESOLUTION, PROTOCOL_HEADER_SIZE
from wayland.log import log
from wayland.unixsocket import UnixSocketConnection


class WaylandState:
    """
    WaylandState tracks Wayland object instances and sends and receives
    Wayland messages.

    Incoming messages are dispatched to event handlers,
    outgoing messages are sent to the local unix socket.

    WaylandState is a singleton, exposed as wayland.state.
    """

    def __init__(self, *, disable_event_dispatch_thread=False):
        self._thread = None
        self._socket_path = self._get_socket_path()
        if self._socket_path:
            self._socket = UnixSocketConnection(self._socket_path)
        else:
            self._socket = None
        self._next_object_id = 1
        self._object_id_to_instance: dict[int, Any] = {}
        self._instance_to_object_id: dict[Any, int] = {}
        # By default check for incoming events at least every millisecond
        if not disable_event_dispatch_thread:
            self._start_event_monitor()

    @staticmethod
    def _get_socket_path() -> str:
        path = os.getenv("XDG_RUNTIME_DIR")
        display = os.getenv("WAYLAND_DISPLAY", "wayland-0")
        if not path:
            msg = "WARNING: Wayland is not active (XDG_RUNTIME_DIR environment variable not set)"
            log.warning(msg)
            return ""
        return f"{path}/{display}"

    def new_object(self, object_reference: Any) -> tuple[int, Any]:
        object_id = self._next_object_id
        self._next_object_id += 1

        if object_reference.object_id:
            object_reference = object_reference.copy()

        self.add_object_reference(object_id, object_reference)
        return object_id, object_reference

    def object_exists(self, object_id: int, object_reference: Any) -> bool:
        if object_id in self._object_id_to_instance:
            if self._object_id_to_instance[object_id] is not object_reference:
                msg = "Object ID does not match expected object reference"
                raise ValueError(msg)
            if object_reference in self._instance_to_object_id:
                if object_id != self._instance_to_object_id[object_reference]:
                    msg = "Object reference does not match expected object id"
                    raise ValueError(msg)
                return True
        return False

    def add_object_reference(self, object_id: int, object_reference: Any) -> None:
        object_reference.object_id = object_id
        if not self.object_exists(object_id, object_reference):
            self._object_id_to_instance[object_id] = object_reference
            self._instance_to_object_id[object_reference] = object_id
        else:
            msg = "Duplicate object id"
            raise ValueError(msg)

    def delete_object_reference(self, object_id: int, object_reference: Any) -> None:
        if self.object_exists(object_id, object_reference):
            del self._object_id_to_instance[object_id]
            del self._instance_to_object_id[object_reference]

    def object_id_to_object_reference(self, object_id: int) -> Any | None:
        return self._object_id_to_instance.get(object_id)

    def object_reference_to_object_id(self, object_reference: Any) -> int:
        return self._instance_to_object_id.get(object_reference, 0)

    def object_id_to_event(self, object_id: int, event_id: int) -> Callable | None:
        obj = self.object_id_to_object_reference(object_id)
        if obj and hasattr(obj, "events"):
            obj = obj.events
            for attribute_name in dir(obj):
                if not attribute_name.startswith("_"):
                    attribute = getattr(obj, attribute_name)
                    if (
                        callable(attribute)
                        and hasattr(attribute, "opcode")
                        and attribute.opcode == event_id
                        and attribute.event
                    ):
                        return attribute
        return None

    def _debug_packet(self, data: bytes, ancillary: Any = None) -> None:
        for i in range(0, len(data), 4):
            group = data[i : i + 4]
            hex_group = " ".join(f"{byte:02X}" for byte in group)
            string_group = "".join(
                chr(byte) if chr(byte) in string.printable else "." for byte in group
            )
            integer_value = int.from_bytes(group, byteorder="little")
            log.protocol(f"    {hex_group}    {string_group}    {integer_value}")

        if ancillary:
            log.protocol(f"    Plus ancillary file descriptor data: {ancillary}")

    def _start_event_monitor(self):
        self._thread = threading.Thread(target=self._process_messages, daemon=True)
        self._thread.start()

    def _send(self, message: bytes, ancillary: Any = None) -> None:
        if not self._socket:
            return
        self._debug_packet(message, ancillary)
        if ancillary:
            self._socket.sendmsg([message], ancillary)
        else:
            self._socket.sendall(message)

    def send_wayland_message(
        self,
        wayland_object: int,
        wayland_request: int,
        packet: bytes = b"",
        ancillary: Any = None,
    ) -> None:
        if not wayland_object:
            msg = "NULL object passed as Wayland object"
            raise ValueError(msg)

        header = struct.pack(
            "IHH", wayland_object, wayland_request, len(packet) + PROTOCOL_HEADER_SIZE
        )
        self._send(header + packet, ancillary)

    def get_next_message(self) -> bool:
        if not self._socket:
            return False
        packet = self._socket.get_next_message()
        if not packet:
            return False

        wayland_object, opcode, _ = struct.unpack_from("IHH", packet)
        packet = packet[PROTOCOL_HEADER_SIZE:]

        event = self.object_id_to_event(wayland_object, opcode)
        if event:
            event(packet, self._socket.get_next_fd)
            return True

        log.event(f"Unhandled event {wayland_object}#{opcode}")
        return True

    def _process_messages(self) -> None:
        """Process all pending wayland messages"""
        while True:
            if not self.get_next_message():
                time.sleep(1 / MAX_EVENT_RESOLUTION)
