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

from wayland.baseobject import WaylandObject
from wayland.client.package import get_package_root
from wayland.constants import MAX_EVENT_RESOLUTION
from wayland.debugger import Debugger
from wayland.log import log
from wayland.message import pack_argument, unpack_argument
from wayland.state import WaylandState


class Proxy:
    _instance = None
    _lock = threading.Lock()
    _initialised = False

    def __new__(cls, *args, **kwargs):  # noqa
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    # A single shared collection of queues for output events
    # queued per thread
    _event_queues: ClassVar[dict] = {}
    _event_lock = threading.Lock()

    class Request:
        def __init__(
            self,
            *,
            name=None,
            args=None,
            opcode=None,
            state=None,
            scope=None,
            object_id=None,
            interface=None,
        ):
            self.name = name
            self.interface = (interface,)
            self.request_args = args
            self.opcode = opcode
            self.request = True
            self.event = False
            self.object_id = object_id
            self.state = state
            self.scope = scope
            self.kwargs = {}
            self.packet = b""
            self._debugger = Debugger()

        def __call__(self, *args):
            args = list(args)

            # Read some properties from the class to which this request is bound
            object_id = self.object_id
            scope = self.scope

            kwargs = {}
            packet = b""
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
                    new_object = self.state.new_object(scope[interface])
                    return_value = new_object.object_id
                    value = new_object.object_id

                else:
                    # A normal argument, just grab the value
                    value = args.pop(0)

                kwargs[arg["name"]] = value

                # Pack the argument
                packet, fds = self.__pack_argument(packet, arg["type"], value)
                if fds:
                    ancillary = [
                        (socket.SOL_SOCKET, socket.SCM_RIGHTS, struct.pack("I", fds[0]))
                    ]

            self.kwargs = kwargs.copy()
            self.packet = packet
            self._debugger.log(self)

            # Send the wayland request
            self.state.send_wayland_message(object_id, self.opcode, packet, ancillary)

            if return_value:
                return_value = self.state.object_id_to_object_reference(return_value)
            return return_value

        def __pack_argument(self, packet, arg_type, value):
            return pack_argument(packet, arg_type, value)

    class Events:
        pass

    class Event:
        def __init__(
            self,
            *,
            name=None,
            args=None,
            opcode=None,
            properties=None,
            interface=None,
            object_id=None,
        ):
            self.name = name
            self.interface = interface
            self.properties = properties
            self.opcode = opcode
            self.object_id = object_id
            self.event_args = args
            self.event = True
            self._lock = threading.Lock()
            self._event_handlers = {}
            self._debugger = Debugger()
            self.kwargs = {}
            self.packet = b""

        def __transform_args(self, packet, get_fd):
            kwargs = {}
            self.packet = packet
            for arg in self.event_args:
                arg_type = arg["type"]
                enum_type = arg.get("enum")
                # Get the value
                packet, value = self.__unpack_argument(
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

        def __thread_id(self):
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
                tid = self.__thread_id()
                with self._lock:
                    self._event_handlers[tid].append(handler)
            return self

        def __isub__(self, handler):
            """Unregisters an existing handler."""
            tid = self.__thread_id()
            with self._lock:
                if handler in self._event_handlers[tid]:
                    self._event_handlers[tid].remove(handler)
            return self

        def __call__(self, packet, get_fd):
            # This event has been triggered, let our event listeners
            # know about it. In fact, don't, but queue up the notifications
            # for when each thread is ready.
            kwargs = self.__transform_args(packet, get_fd)
            self.kwargs = kwargs

            self._debugger.log(self)

            # Put this event callback in each threads queue
            with self._lock:
                for thread_id in self._event_handlers:
                    if len(self._event_handlers[thread_id]) > 0:
                        for handler in self._event_handlers[thread_id]:
                            # Store method ptr, args
                            Proxy._queue_event(thread_id, handler, kwargs)

        def __int_to_enum(self, enum_name, value):
            for attr_name, attr_type in self.properties:
                if (
                    isinstance(attr_type, type)
                    and issubclass(attr_type, Enum)
                    and attr_name == enum_name
                ):
                    return attr_type(value)
            return value

        def __unpack_argument(self, packet, arg_type, get_fd, enum_type):
            return unpack_argument(
                packet, arg_type, get_fd, enum_type, self.__int_to_enum
            )

    class DynamicObject:
        @property
        def object_id(self):
            return self.__object_id

        @object_id.setter
        def object_id(self, value):
            self.__object_id = value
            log.protocol(f"{self.__name} assigned object_id {self.__object_id}")

        def __new__(cls, *args, **kwargs):  # noqa
            return super().__new__(cls)

        def __init__(
            self,
            name=None,
            scope=None,
            requests=None,
            events=None,
            enums=None,
            state=None,
        ):
            # If called with no arguments or minimal arguments, use smart construction
            if name is None:
                self.__smart_init()
                return

            # Normal construction with all arguments
            self.__name = name
            self.__interface = name
            self.__scope = scope
            self.__state = state
            self.__requests = requests or []
            self.__events = events or []
            self.__enums = enums or []
            self.__object_id = 0

            # Allocate an object id
            self.__state.allocate_new_object_id(self)

            # Special wayland case of object 1
            if name == "wl_display":
                self.__setup_display_methods()

            # Bind requests and events
            self.events = Proxy.Events()
            self.__bind_requests(self.__requests)
            self.__bind_events(self.__events)
            self.__bind_enums(self.__enums)

            # Auto-register event handlers after everything is set up
            self.__register_event_handlers()

        def __smart_init(self):
            """Initialise using the proxy context"""
            proxy = Proxy()

            # Get the class name from the class hierarchy
            class_name = None
            for cls in self.__class__.__mro__:
                if cls.__name__ in proxy._dynamic_classes:
                    class_name = cls.__name__
                    break

            if class_name is None:
                msg = f"Could not determine wayland class name for {self.__class__.__name__}"
                raise RuntimeError(msg)

            # Get the protocol details from the proxy
            details = proxy._get_class_details(class_name)

            # Initialise with proper arguments
            Proxy.DynamicObject.__init__(
                self,
                class_name,
                proxy.scope,
                details.get("requests", []),
                details.get("events", []),
                details.get("enums", []),
                proxy.state,
            )

        def __setup_display_methods(self):
            """Setup special methods for wl_display"""

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

        def __register_event_handlers(self):
            """Automatically register methods matching on_<event_name> pattern"""
            for attr_name in dir(self):
                if attr_name.startswith("on_"):
                    method = getattr(self, attr_name)
                    if callable(method):
                        event_name = attr_name[3:]  # Remove 'on_' prefix

                        # Handle both 'on_event' and 'on_event_' patterns
                        if event_name.endswith("_"):
                            event_name = event_name[:-1]

                        # Check if this event exists
                        if hasattr(self.events, event_name):
                            event = getattr(self.events, event_name)
                            event += method
                            log.debug(
                                f"Auto-registered {attr_name} for {self.__name}.{event_name}"
                            )
                        elif hasattr(self.events, event_name + "_"):
                            # Handle keyword collision cases
                            event = getattr(self.events, event_name + "_")
                            event += method
                            log.debug(
                                f"Auto-registered {attr_name} for {self.__name}.{event_name}_"
                            )
                        else:
                            log.warning(
                                f"Method {attr_name} found but no matching event '{event_name}' in {self.__name}"
                            )

        def __bind_requests(self, requests):
            for request in requests:
                # Avoid python keyword naming collisions
                attr_name = request["name"]
                if keyword.iskeyword(attr_name):
                    attr_name += "_"

                # Create a new request
                request_obj = Proxy.Request(
                    name=attr_name,
                    interface=self.__name,
                    args=request["args"],
                    opcode=request["opcode"],
                    state=self.__state,
                    scope=self.__scope,
                    object_id=self.object_id,
                )
                # Set the request with the correct binding
                setattr(self, attr_name, request_obj)

        def __bind_events(self, events):
            for event in events:
                # Avoid python keyword naming collisions
                attr_name = event["name"]
                if keyword.iskeyword(attr_name):
                    attr_name += "_"

                # Create a new event
                event_obj = Proxy.Event(
                    name=attr_name,
                    interface=self.__interface,
                    object_id=self.__object_id,
                    args=event["args"],
                    opcode=event["opcode"],
                    properties=self.__dict__.items(),
                )
                # Set the event with the correct binding
                setattr(self.events, attr_name, event_obj)

        def __bind_enums(self, enums):
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
        if self._initialised:
            return

        with self._lock:
            if self._initialised:
                return

            self.state = WaylandState(self)
            self.scope = None
            self._dynamic_classes = {}
            self._class_details = {}
            self._custom_factories = {}

            self._initialised = True

    def __getitem__(self, key):
        if hasattr(self, key):
            attr = getattr(self, key)
            if callable(attr):
                return attr()
            return attr

        msg = f"'{key}' not found"
        raise KeyError(msg)

    def register_factory(self, interface_name, custom_class):
        """Register a custom class to be used when creating objects of a specific interface"""
        self._custom_factories[interface_name] = custom_class
        log.debug(
            f"Registered custom factory for {interface_name}: {custom_class.__name__}"
        )
        return custom_class

    def _create_object_instance(self, interface_name, *args, **kwargs):
        """Create an object instance, using custom factory if registered"""
        if interface_name in self._custom_factories:
            # Use the custom class
            custom_class = self._custom_factories[interface_name]
            return custom_class(*args, **kwargs)
        # Use the standard dynamic class
        standard_class = self._dynamic_classes[interface_name]
        return standard_class(*args, **kwargs)

    def _get_class_details(self, class_name):
        """Get the original protocol details for a class"""
        return self._class_details.get(class_name, {})

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
            # Store the details for later use
            self._class_details[class_name] = details

            class_variables = {
                # "version": details.get("version", 1),
            }

            # Create the dynamic class
            dynamic_class = type(
                class_name,
                (
                    WaylandObject,
                    Proxy.DynamicObject,
                ),
                class_variables,
            )

            # Save the class
            self._dynamic_classes[class_name] = dynamic_class

            # Inject class into scope
            if isinstance(self.scope, dict):
                self.scope[class_name] = dynamic_class
            else:
                setattr(self.scope, class_name, dynamic_class)

        # initialised ok
        return True
