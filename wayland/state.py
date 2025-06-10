# Copyright (c) 2024-2025 Graham R King
# Licensed under the MIT License. See LICENSE file for details.

from __future__ import annotations

import os
import string
import struct
import threading
import time
from typing import Any, Callable

from wayland.constants import MAX_EVENT_RESOLUTION, PROTOCOL_HEADER_SIZE
from wayland.exceptions import WaylandConnectionError, WaylandNotConnectedError
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

    _instance = None
    _lock = threading.Lock()
    _initialised = False

    def __new__(cls, *args, **kwargs):  # noqa
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, proxy):
        if self._initialised:
            return

        with self._lock:
            if self._initialised:
                return
            self._connected = False
            self._proxy = proxy
            self._object_id_lock = threading.RLock()
            self._thread = None
            self._socket_path = self._get_socket_path()
            self._socket = None
            self._stop_event = threading.Event()

            self._next_object_id = 2  # 1 is reserved
            self._object_id_to_instance: dict[int, Any] = {}
            self._instance_to_object_id: dict[Any, int] = {}

            self._auto_connect = True
            self._initialised = True

    @property
    def connected(self):
        return self._connected

    def connect(self) -> bool:
        if self._connected:
            return True

        # Connect to the wayland socket
        # TODO: Should we reset all our object IDs on reconnect?
        self._socket_path = self._get_socket_path()

        def _raise_connection_error(ex=None):
            if ex is None:
                raise WaylandConnectionError from None
            raise WaylandConnectionError from ex

        try:
            if self._socket_path:
                self._socket = UnixSocketConnection(self._socket_path)
            else:
                _raise_connection_error()
        except Exception as ex:  # noqa: BLE001
            _raise_connection_error(ex)

        self._connected = True

        # Start monitoring the socket
        self._start_event_monitor()
        return True

    def disconnect(self) -> None:
        self._stop_event_monitor()
        if self._socket:
            self._socket.stop()
        self._socket = None
        self._connected = False

    def _assert_connected(self):
        if not self._connected:
            if self._auto_connect:
                self.connect()
            else:
                raise WaylandNotConnectedError

    def _get_socket_path(self) -> str:
        path = os.getenv("XDG_RUNTIME_DIR", "")
        display = os.getenv("WAYLAND_DISPLAY", "wayland-0")
        wayland_socket = os.path.join(str(path), str(display))
        if not os.path.exists(wayland_socket):
            msg = (
                "WARNING: Wayland is not active "
                f"(XDG_RUNTIME_DIR/WAYLAND_DISPLAY = '{wayland_socket}')"
            )
            log.warning(msg)
            return ""
        return f"{path}/{display}"

    def _get_next_object_id(self, prototype):
        # Return the next free id
        with self._object_id_lock:
            # Special cases
            if (
                hasattr(prototype, "_DynamicObject__interface")
                and prototype._DynamicObject__interface == "wl_display"  # noqa
            ):
                return 1  # Wayland object 1

            # Normal cases
            while True:
                object_id = self._next_object_id
                self._next_object_id += 1
                if object_id in self._object_id_to_instance:
                    continue
                break

            return object_id

    def new_object(self, prototype):
        # Check if we should use a custom factory
        if prototype.__name__ in self._proxy._custom_factories:  # noqa
            # Use custom factory
            custom_class = self._proxy._custom_factories[prototype.__name__]  # noqa
            new_object = custom_class()
        else:
            # Create an instance of this wayland dynamic class
            new_object = prototype()

        return new_object

    def allocate_new_object_id(self, object_reference):
        object_id = self._get_next_object_id(object_reference)
        self.assign_object_id(object_id, object_reference)
        return object_id

    def object_exists(self, object_id: int, object_reference: Any) -> bool:
        with self._object_id_lock:
            if object_id in self._object_id_to_instance:
                if self._object_id_to_instance[object_id] is not object_reference:
                    msg = (
                        "Object ID does not match expected object reference, "
                        f"found {self._object_id_to_instance[object_id]} "
                        f"expected {object_reference}"
                    )
                    raise ValueError(msg)
                if object_reference in self._instance_to_object_id:
                    if object_id != self._instance_to_object_id[object_reference]:
                        msg = "Object reference does not match expected object id"
                        raise ValueError(msg)
                    return True
        return False

    def assign_object_id(self, object_id: int, object_reference: Any) -> None:
        object_reference.object_id = object_id
        with self._object_id_lock:
            if not self.object_exists(object_id, object_reference):
                self._object_id_to_instance[object_id] = object_reference
                self._instance_to_object_id[object_reference] = object_id
            else:
                msg = "Duplicate object id"
                raise ValueError(msg)

    def delete_object_reference(self, object_id: int, object_reference: Any) -> None:
        with self._object_id_lock:
            if self.object_exists(object_id, object_reference):
                del self._object_id_to_instance[object_id]
                del self._instance_to_object_id[object_reference]

    def object_id_to_object_reference(self, object_id: int) -> Any | None:
        with self._object_id_lock:
            return self._object_id_to_instance.get(object_id)

    def object_reference_to_object_id(self, object_reference: Any) -> int:
        with self._object_id_lock:
            return self._instance_to_object_id.get(object_reference, 0)

    def object_id_to_event(self, object_id: int, event_id: int) -> Callable | None:
        with self._object_id_lock:
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
        if not self._thread:
            self._thread = threading.Thread(target=self._process_messages, daemon=True)
            self._thread.start()

    def _stop_event_monitor(self):
        if self._thread:
            self._stop_event.set()
            self._thread.join()
            self._thread = None

    def _send(self, message: bytes, ancillary: Any = None) -> None:
        self._assert_connected()
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
        self._assert_connected()
        if not wayland_object:
            msg = "NULL object passed as Wayland object"
            raise ValueError(msg)

        header = struct.pack(
            "IHH", wayland_object, wayland_request, len(packet) + PROTOCOL_HEADER_SIZE
        )
        self._send(header + packet, ancillary)

    def get_next_message(self) -> bool:
        self._assert_connected()
        packet = self._socket.get_next_message()
        if not packet:
            return False

        wayland_object, opcode, _ = struct.unpack_from("IHH", packet)
        packet = packet[PROTOCOL_HEADER_SIZE:]

        event = self.object_id_to_event(wayland_object, opcode)
        if event:
            event(packet, self._socket.get_next_fd)
            return True

        log.warning(f"Unhandled event {wayland_object}#{opcode}")
        return True

    def _process_messages(self) -> None:
        """Process all pending wayland messages"""
        while not self._stop_event.is_set():
            if not self.get_next_message():
                time.sleep(1 / MAX_EVENT_RESOLUTION)
