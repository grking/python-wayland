# Copyright (c) 2024-2025 Graham R King
# Licensed under the MIT License. See LICENSE file for details.

import json
import keyword
import socket
import struct
import threading
import time
import types
from enum import Enum, IntFlag
from queue import Empty, SimpleQueue
from typing import ClassVar

from wayland.client.package import get_package_root
from wayland.constants import MAX_EVENT_RESOLUTION
from wayland.debugger import Debugger
from wayland.log import log
from wayland.state import WaylandState

# Global reference to active proxy instance
_active_proxy = None


def _set_active_proxy(proxy):
    """Set the active proxy instance for inspection."""
    global _active_proxy  # noqa: PLW0603
    _active_proxy = proxy


def _get_active_proxy():
    """Get the active proxy instance."""
    return _active_proxy


class Proxy:
    # A single shared collection of queues for output events
    # queued per thread
    _event_queues: ClassVar[dict] = {}
    _event_lock = threading.Lock()

    class Request:
        def __init__(self, parent, name, args, opcode, state):
            self.name = name
            self.request_args = args
            self.opcode = opcode
            self.request = True
            self.event = False
            self.parent = parent
            self.state = state
            self.kwargs = {}
            self.packet = b""
            self._debugger = Debugger()

        @classmethod
        def _pad(cls, data):
            if isinstance(data, str):
                data = data.encode("utf-8")
            data += b"\x00"
            padding = ((len(data) + 3) & ~3) - len(data)
            data += b"\x00" * padding
            return data

        def __call__(self, *args):
            args = list(args)

            # Read some properties from the class to which this request is bound
            object_id = self.parent.object_id
            scope = self.parent._scope

            kwargs = {}
            packet = b""
            values = []
            interface = None
            ancillary = None
            return_value = None
            for arg in self.request_args:
                # Remember any interface value we see
                if arg["name"] == "interface":
                    interface = args.pop(0)
                    value = interface
                elif arg["type"] == "new_id":
                    # use the object type of the new_id arg if possible
                    if arg.get("interface"):
                        interface = arg.get("interface")

                    # Create a new object to return as
                    new_object_id, new_object = self.state.new_object(scope[interface])
                    return_value = new_object_id
                    value = new_object_id

                else:
                    # A normal argument, just grab the value
                    value = args.pop(0)

                kwargs[arg["name"]] = value

                # Pack the argument
                packet, value = self._pack_argument(packet, arg["type"], value)
                ancillary = self._handle_fd_argument(arg["type"], value, ancillary)

                # Debug info
                values.append(self._format_debug_arg(value, arg["type"]))

            self.kwargs = kwargs.copy()
            self.packet = packet
            self._debugger.log(self)

            # Send the wayland request
            self.state.send_wayland_message(object_id, self.opcode, packet, ancillary)

            if return_value:
                return_value = self.state.object_id_to_object_reference(return_value)
            return return_value

        def _pack_argument(self, packet, arg_type, value):
            if arg_type in ("new_id", "uint"):
                if isinstance(value, Enum):
                    packet += struct.pack("I", value.value)
                else:
                    packet += struct.pack("I", value)
            elif arg_type == "object":
                packet += struct.pack("I", getattr(value, "object_id", 0))
            elif arg_type == "int":
                packet += struct.pack("i", value)
            elif arg_type == "enum":
                packet += struct.pack("I", value.value)
            elif arg_type == "string":
                length = len(value) + 1
                value = self._pad(value)
                packet += struct.pack(f"I{len(value)}s", length, value)
            elif arg_type == "fixed":
                integer_part = int(value) << 8
                fractional_part = int((value - int(value)) * 256)
                value = integer_part | (fractional_part & 0xFF)
                packet += struct.pack("I", value)

            return packet, value

        def _handle_fd_argument(self, arg_type, value, ancillary):
            if arg_type == "fd":
                ancillary = [
                    (socket.SOL_SOCKET, socket.SCM_RIGHTS, struct.pack("I", value))
                ]
            return ancillary

        def _format_debug_arg(self, value, arg_type):
            if arg_type == "object" and isinstance(value, object):
                return f"{value._name}#{value.object_id}"
            return str(value)

    class Events:
        pass

    class Event:
        def __init__(self, parent, name, args, opcode):
            self.name = name
            self.parent = parent
            self.opcode = opcode
            self.event_args = args
            self.event = True
            self._lock = threading.Lock()
            self._event_handlers = {}
            self._debugger = Debugger()
            self.kwargs = {}
            self.packet = b""

        def _transform_args(self, packet, get_fd):
            kwargs = {}
            self.packet = packet
            for arg in self.event_args:
                arg_type = arg["type"]
                enum_type = arg.get("enum")
                # Get the value
                packet, value = self._unpack_argument(
                    packet, arg_type, get_fd, enum_type
                )
                # Save the argument value
                kwargs[arg["name"]] = value

                # For new_id on events, pass the interface as an argument to the event handler too
                if arg_type == "new_id" and arg.get("interface"):
                    # Get the interface name
                    interface = arg.get("interface")
                    # Save the argument
                    kwargs["interface"] = interface
                    # TODO: we don't expand object id to an actual object instance
                    msg = "No events like this to test yet"
                    raise NotImplementedError(msg)
            return kwargs

        def _thread_id(self):
            tid = threading.current_thread().native_id
            # Ensure we are setup for this thread
            with self._lock:
                if tid not in self._event_handlers:
                    self._event_handlers[tid] = []
            with Proxy._event_lock:
                if tid not in Proxy._event_queues:
                    Proxy._event_queues[tid] = SimpleQueue()
            return tid

        def __iadd__(self, handler):
            """Registers a new handler to be called when the event is triggered."""
            if callable(handler):
                tid = self._thread_id()
                with self._lock:
                    self._event_handlers[tid].append(handler)
            return self

        def __isub__(self, handler):
            """Unregisters an existing handler."""
            tid = self._thread_id()
            with self._lock:
                if handler in self._event_handlers[tid]:
                    self._event_handlers[tid].remove(handler)
            return self

        def __call__(self, packet, get_fd):
            # This event has been triggered, let our event listeners
            # know about it. In fact, don't, but queue up the notifications
            # for when each thread is ready.
            kwargs = self._transform_args(packet, get_fd)
            self.kwargs = kwargs

            self._debugger.log(self)

            # Put this event callback in each threads queue
            with self._lock:
                for thread_id in self._event_handlers:
                    if len(self._event_handlers[thread_id]) > 0:
                        for handler in self._event_handlers[thread_id]:
                            # Store method ptr, args
                            Proxy._queue_event(thread_id, handler, kwargs)

        def _int_to_enum(self, enum_name, value):
            for attr_name, attr_type in self.parent.__dict__.items():
                if (
                    isinstance(attr_type, type)
                    and issubclass(attr_type, Enum)
                    and attr_name == enum_name
                ):
                    return attr_type(value)
            return value

        def _unpack_argument(self, packet, arg_type, get_fd, enum_type):
            read = 0
            if enum_type is not None:
                (value,) = struct.unpack_from("I", packet)
                value = self._int_to_enum(enum_type, value)
                read = 4
            elif arg_type in ("new_id", "uint", "object"):
                (value,) = struct.unpack_from("I", packet)
                read = 4
            elif arg_type == "int":
                (value,) = struct.unpack_from("i", packet)
                read = 4
            elif arg_type == "fd":
                # we fetch the fd from the incoming fd queue
                value = get_fd()
            elif arg_type == "string":
                (length,) = struct.unpack_from("I", packet)
                packet = packet[4:]
                padded_length = (length + 3) & ~3
                (value,) = struct.unpack_from(f"{padded_length}s", packet)
                value = value[: length - 1].decode("utf-8")
                read = padded_length
            elif arg_type == "array":
                (length,) = struct.unpack_from("I", packet)
                packet = packet[4:]
                padded_length = (length + 3) & ~3
                if length > 0:
                    # Read the raw array data
                    (array_data,) = struct.unpack_from(f"{padded_length}s", packet)
                    # Convert bytes to list of integers
                    num_elements = length // 4
                    value = list(struct.unpack(f"{num_elements}I", array_data[:length]))
                else:
                    value = []

                read = padded_length
            elif arg_type == "fixed":
                (value,) = struct.unpack_from("I", packet)
                read = 4
                integer_part = value >> 8
                fractional_part = value & 0xFF
                value = integer_part + fractional_part / 256.0
            else:
                raise ValueError("Unknown type " + arg_type)

            return packet[read:], value

    class DynamicObject:
        @property
        def object_id(self):
            return self._object_id

        @object_id.setter
        def object_id(self, value):
            self._object_id = value
            log.protocol(f"{self._name} assigned object_id {self._object_id}")

        def __init__(self, name, scope, requests, events, enums, state):
            self._name = name
            self._scope = scope
            self._state = state
            self._requests = requests
            self._events = events
            self._enums = enums
            self._object_id = 0
            # Special wayland case, the global singleton interface
            if name == "wl_display":

                def dispatch(self):
                    return Proxy._dispatch()

                def dispatch_pending(self):
                    return Proxy._dispatch_pending()

                def dispatch_timeout(self, timeout_in_seconds):
                    return Proxy._dispatch_timeout(timeout_in_seconds)

                # Bind these dynamic methods
                self.dispatch = types.MethodType(dispatch, self)
                self.dispatch_pending = types.MethodType(dispatch_pending, self)
                self.dispatch_timeout = types.MethodType(dispatch_timeout, self)

                self.object_id, _ = self._state.new_object(self)

            # Bind requests and events
            self.events = Proxy.Events()
            self._bind_requests(requests)
            self._bind_events(events)
            self._bind_enums(enums)

        def copy(self):
            return self.__class__(
                self._name,
                self._scope,
                self._requests,
                self._events,
                self._enums,
                self._state,
            )

        def _bind_requests(self, requests):
            for request in requests:
                # Avoid python keyword naming collisions
                attr_name = request["name"]
                if keyword.iskeyword(attr_name):
                    attr_name += "_"

                # Create a new request
                request_obj = Proxy.Request(
                    self, attr_name, request["args"], request["opcode"], self._state
                )
                # Set the request with the correct binding
                setattr(self, attr_name, request_obj)

        def _bind_events(self, events):
            for event in events:
                # Avoid python keyword naming collisions
                attr_name = event["name"]
                if keyword.iskeyword(attr_name):
                    attr_name += "_"

                # Create a new event
                event_obj = Proxy.Event(self, attr_name, event["args"], event["opcode"])
                # Set the event with the correct binding
                setattr(self.events, attr_name, event_obj)

        def _bind_enums(self, enums):
            for enum in enums:
                # Avoid python keyword naming collisions
                attr_name = enum["name"]
                if keyword.iskeyword(attr_name):
                    attr_name += "_"

                # Create a new enum
                enum_params = {
                    item["name"]: int(item["value"], 0) for item in enum["args"]
                }
                if enum.get("bitfield"):
                    enum_obj = IntFlag(attr_name, enum_params)
                else:
                    enum_obj = Enum(attr_name, enum_params)
                # Set the enum with the correct binding
                setattr(self, attr_name, enum_obj)

        def __bool__(self):
            return self.object_id > 0

    # Proxy class methods

    def __init__(self):
        self.state = WaylandState()
        self.scope = None

    def __getitem__(self, key):
        if hasattr(self, key):
            attr = getattr(self, key)
            if callable(attr):
                return attr()
            return attr

        msg = f"'{key}' not found"
        raise KeyError(msg)

    @classmethod
    def _queue_event(cls, thread_id, func_ptr, kwargs):
        with Proxy._event_lock:
            qu = Proxy._event_queues[thread_id]
        qu.put((func_ptr, kwargs))

    @classmethod
    def _dispatch_timeout(cls, timeout_in_seconds):
        # Blocking call to event dispatch, returns once some events have
        # been processed or timeout has elapsed. timeout in seconds and
        # can be fractional
        have_events = False
        max_time = time.time() + timeout_in_seconds
        while not have_events:
            have_events = cls._dispatch_pending()
            if not have_events:
                time.sleep(1 / MAX_EVENT_RESOLUTION)
            if time.time() > max_time:
                break
        return have_events

    @classmethod
    def _dispatch(cls):
        # Blocking call to event dispatch, returns once some events have
        # been processed
        have_events = False
        while not have_events:
            have_events = cls._dispatch_pending()
            if not have_events:
                time.sleep(1 / MAX_EVENT_RESOLUTION)

    @classmethod
    def _dispatch_pending(cls):
        # Non-Blocking call to event dispatch. Dispatches all pending events
        # returns True if any events were dispatched, False otherwise.
        tid = threading.current_thread().native_id
        have_events = False

        # Get the queue if we haven't got it
        with Proxy._event_lock:
            if tid in Proxy._event_queues:
                qu = Proxy._event_queues[tid]
            else:
                return False

        # Call any pending event handlers, for handlers registered
        # by the same thread context that is calling the dispatch
        # method. We're calling the handler *in* the same thread
        # context it was registered with also.
        while True:
            try:
                func_ptr, kwargs = qu.get_nowait()
                # We let exceptions here propagate back to the calling
                # thread. It's that threads code that has raised the
                # exception anyway
                func_ptr(**kwargs)
                have_events = True
            except Empty:
                break

        return have_events

    def initialise(self, scope=None, path=None):
        if scope is None:
            self.scope = self
        else:
            self.scope = scope
        if path is None:
            path = get_package_root()

        try:
            with open(f"{path}/protocols.json", encoding="utf-8") as infile:
                structure = json.load(infile)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            msg = f"Wayland protocol definitions not found: {e}"
            log.error(msg)
            return False

        for class_name, details in structure.items():
            # Process requests
            requests = details.get("requests", [])
            events = details.get("events", [])
            enums = details.get("enums", [])
            dynamic_class = type(class_name, (Proxy.DynamicObject,), {})
            instance = dynamic_class(
                class_name, self.scope, requests, events, enums, self.state
            )
            # Inject instance into scope
            if isinstance(self.scope, dict):
                self.scope[class_name] = instance
            else:
                setattr(self.scope, class_name, instance)

        # initialised ok
        return True
