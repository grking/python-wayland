import wayland
from wayland.client import wayland_class


def test_initial_connection_and_global_discovery(wayland_server):
    """Test initial Wayland connection establishment and global object discovery.

    This test verifies that a client can successfully connect to a Wayland server
    and discover global objects through the registry mechanism. The test creates
    a display connection, requests the registry, and verifies that global events
    are properly received and processed when the server advertises available
    interfaces like wl_compositor.
    """
    global_event_received = False

    @wayland_class("wl_registry")
    class TestRegistry(wayland.wl_registry):
        def on_global(self, name, interface, version):
            nonlocal global_event_received
            global_event_received = True
            assert name == 1
            assert interface == "wl_compositor"
            assert version == 4

    display = wayland.wl_display()
    registry = display.get_registry()

    request = wayland_server.get_request(timeout=1)
    assert request["object_id"] == 1
    assert request["opcode"] == 1

    wayland_server.send_global_event(registry.object_id, 1, "wl_compositor", 4)

    display.dispatch_timeout(1)

    assert global_event_received


def test_object_creation_and_method_invocation(wayland_server):
    """Test object binding and method invocation in the Wayland protocol.

    This test validates that clients can bind to global objects and invoke methods
    on them. It simulates discovering a wl_compositor global, binding to it, and
    then calling create_surface() to create a new surface object. The test verifies
    that the correct protocol requests are sent to the server in the proper sequence.
    """

    @wayland_class("wl_registry")
    class TestRegistry(wayland.wl_registry):
        def on_global(self, name, interface, version):
            if interface == "wl_compositor":
                compositor = self.bind(name, "wl_compositor", version)
                surface = compositor.create_surface()
                assert surface is not None

    display = wayland.wl_display()
    registry = display.get_registry()

    request = wayland_server.get_request(timeout=1)
    assert request["object_id"] == 1
    assert request["opcode"] == 1

    wayland_server.send_global_event(registry.object_id, 1, "wl_compositor", 4)

    display.dispatch_timeout(1)

    bind_request = wayland_server.get_request(timeout=1)
    assert bind_request["object_id"] == registry.object_id
    assert bind_request["opcode"] == 0

    surface_request = wayland_server.get_request(timeout=1)
    assert surface_request["opcode"] == 0


def test_comprehensive_event_deserialization(wayland_server):
    """Test comprehensive event deserialization and argument handling.

    This test verifies that the client can properly deserialize events with
    various argument types from the server. It binds to a wl_seat object and
    tests receiving a capabilities event with integer arguments, ensuring that
    the event data is correctly parsed and passed to the event handler method.
    """
    event_received = False
    received_args = {}
    seat = None

    @wayland_class("wl_registry")
    class TestRegistry(wayland.wl_registry):
        def on_global(self, name, interface, version):
            nonlocal seat
            if interface == "wl_seat":
                seat = self.bind(name, "wl_seat", version)

    @wayland_class("wl_seat")
    class TestSeat(wayland.wl_seat):
        def on_capabilities(self, capabilities):
            nonlocal event_received, received_args
            event_received = True
            received_args["capabilities"] = capabilities

    display = wayland.wl_display()
    registry = display.get_registry()

    wayland_server.get_request(timeout=1)

    wayland_server.send_global_event(registry.object_id, 1, "wl_seat", 1)

    display.dispatch_timeout(1)

    wayland_server.get_request(timeout=1)

    assert seat is not None
    capabilities_value = 3
    wayland_server.send_capabilities_event(seat.object_id, capabilities_value)

    display.dispatch_timeout(1)

    assert event_received
    assert received_args["capabilities"] == capabilities_value


def test_explicit_factory_registration(wayland_server):
    """Test explicit factory registration for custom object classes.

    This test validates the factory registration mechanism that allows clients
    to register custom classes for specific Wayland interfaces. It registers
    a CustomSeat class for the wl_seat interface, then verifies that when
    binding to a wl_seat global, the custom class is instantiated instead
    of the default wl_seat class.
    """
    event_received = False
    seat = None

    class CustomSeat(wayland.wl_seat):
        def on_capabilities(self, capabilities):
            nonlocal event_received
            event_received = True
            assert capabilities == 1

    wayland.client.register_factory("wl_seat", CustomSeat)

    @wayland_class("wl_registry")
    class TestRegistry(wayland.wl_registry):
        def on_global(self, name, interface, version):
            nonlocal seat
            if interface == "wl_seat":
                seat = self.bind(name, "wl_seat", version)

    display = wayland.wl_display()
    registry = display.get_registry()

    wayland_server.get_request(timeout=1)

    wayland_server.send_global_event(registry.object_id, 1, "wl_seat", 1)

    display.dispatch_timeout(1)

    wayland_server.get_request(timeout=1)

    assert seat is not None
    wayland_server.send_capabilities_event(seat.object_id, 1)

    display.dispatch_timeout(1)

    assert event_received


def test_object_lifecycle_destruction(wayland_server):
    """Test object lifecycle management and proper destruction.

    This test verifies that Wayland objects can be properly destroyed and that
    the destruction process sends the correct protocol messages. It creates a
    surface object, destroys it, and uses a sync callback to ensure the destroy
    request is processed. The test validates that destroy requests are sent with
    the correct object ID and opcode.
    """
    callback_done_received = False
    surface = None
    callback = None

    @wayland_class("wl_registry")
    class TestRegistry(wayland.wl_registry):
        def on_global(self, name, interface, version):
            nonlocal surface
            if interface == "wl_compositor":
                compositor = self.bind(name, "wl_compositor", version)
                surface = compositor.create_surface()

    @wayland_class("wl_callback")
    class TestCallback(wayland.wl_callback):
        def on_done(self, callback_data):
            nonlocal callback_done_received
            callback_done_received = True

    display = wayland.wl_display()
    registry = display.get_registry()

    wayland_server.get_request(timeout=1)

    wayland_server.send_global_event(registry.object_id, 1, "wl_compositor", 4)

    display.dispatch_timeout(1)

    wayland_server.get_request(timeout=1)
    wayland_server.get_request(timeout=1)

    assert surface is not None
    surface_initial_id = surface.object_id

    surface.destroy()
    callback = display.sync()

    destroy_request = wayland_server.get_request(timeout=1)
    assert destroy_request["object_id"] == surface_initial_id
    assert destroy_request["opcode"] == 0

    sync_request = wayland_server.get_request(timeout=1)
    assert sync_request["object_id"] == display.object_id
    assert sync_request["opcode"] == 0

    callback_object_id = callback.object_id
    packet = b""
    packet, _ = wayland_server._pack_argument(packet, "uint", 0)
    wayland_server.send_event(callback_object_id, 0, packet)

    display.dispatch_timeout(1)

    assert callback_done_received


def test_dynamic_registry_global_removal(wayland_server):
    """Test dynamic global object removal from the registry.

    This test validates that clients can properly handle the dynamic removal
    of global objects from the registry. It registers a global object (wl_seat),
    verifies it's received via the global event, then sends a global_remove
    event and confirms that the removal event is properly handled and the
    object is removed from the client's tracking.
    """
    global_received = False
    global_removed = False
    received_name = None
    removed_name = None
    globals_dict = {}

    @wayland_class("wl_registry")
    class TestRegistry(wayland.wl_registry):
        def on_global(self, name, interface, version):
            nonlocal global_received, received_name
            if interface == "wl_seat":
                global_received = True
                received_name = name
                globals_dict[name] = {"interface": interface, "version": version}

        def on_global_remove(self, name):
            nonlocal global_removed, removed_name
            global_removed = True
            removed_name = name
            if name in globals_dict:
                del globals_dict[name]

    display = wayland.wl_display()
    registry = display.get_registry()

    wayland_server.get_request(timeout=1)

    wayland_server.send_global_event(registry.object_id, 1, "wl_seat", 1)

    display.dispatch_timeout(1)

    assert global_received
    assert received_name == 1

    wayland_server.send_global_remove_event(registry.object_id, 1)

    display.dispatch_timeout(1)

    assert global_removed
    assert removed_name == 1
    assert 1 not in globals_dict


def test_dispatch_timeout(wayland_server):
    """Test dispatch timeout functionality and timing accuracy.

    This test verifies that the dispatch_timeout method properly handles
    timeout scenarios when no events are available. It measures the actual
    elapsed time during a timeout period to ensure the timeout mechanism
    works correctly and returns within the expected time bounds, validating
    both the return value and timing behavior.
    """
    import time

    display = wayland.wl_display()

    start_time = time.time()
    result = display.dispatch_timeout(0.1)
    end_time = time.time()

    elapsed_time = end_time - start_time

    assert result == 0
    assert 0.08 <= elapsed_time <= 0.15


def test_factory_re_registration(wayland_server):
    """Test factory re-registration and override behavior.

    This test validates that factory registration can be overridden by
    registering multiple custom classes for the same interface. It registers
    two different custom seat classes for wl_seat, then verifies that the
    most recently registered class (CustomSeat2) is used when binding to
    a wl_seat global, demonstrating that later registrations override earlier ones.
    """
    seat_instance = None

    class CustomSeat1(wayland.wl_seat):
        pass

    class CustomSeat2(wayland.wl_seat):
        pass

    wayland.client.register_factory("wl_seat", CustomSeat1)
    wayland.client.register_factory("wl_seat", CustomSeat2)

    @wayland_class("wl_registry")
    class TestRegistry(wayland.wl_registry):
        def on_global(self, name, interface, version):
            nonlocal seat_instance
            if interface == "wl_seat":
                seat_instance = self.bind(name, "wl_seat", version)

    display = wayland.wl_display()
    registry = display.get_registry()

    wayland_server.get_request(timeout=1)

    wayland_server.send_global_event(registry.object_id, 1, "wl_seat", 1)

    display.dispatch_timeout(1)

    wayland_server.get_request(timeout=1)

    assert seat_instance is not None
    assert isinstance(seat_instance, CustomSeat2)
    assert not isinstance(seat_instance, CustomSeat1)


def test_message_serialization_in_debugger_flow(wayland_server):
    """Test that Message serialization works correctly in end-to-end communication.

    This test exercises the serialiser functionality by enabling debugging and
    verifying that messages are properly serialized and can be converted to JSON
    during the communication flow between client and server.
    """
    import json

    from wayland.debugger import Debugger
    from wayland.serialiser import MessageEncoder

    debugger = Debugger()
    debugger.set_max_size(100)

    @wayland_class("wl_registry")
    class TestRegistry(wayland.wl_registry):
        def on_global(self, name, interface, version):
            if interface == "wl_compositor":
                compositor = self.bind(name, "wl_compositor", version)
                surface = compositor.create_surface()
                assert surface is not None

    display = wayland.wl_display()
    registry = display.get_registry()

    wayland_server.get_request(timeout=1)
    wayland_server.send_global_event(registry.object_id, 1, "wl_compositor", 4)
    display.dispatch_timeout(1)

    wayland_server.get_request(timeout=1)
    wayland_server.get_request(timeout=1)

    assert len(debugger) >= 2

    for message in debugger:
        json_str = json.dumps(message, cls=MessageEncoder)
        parsed = json.loads(json_str)

        assert "timestamp" in parsed
        assert "msgtype" in parsed
        assert "interface" in parsed
        assert "method_name" in parsed
        assert "object_id" in parsed
        assert "args" in parsed
        assert "opcode" in parsed
        assert "packet" in parsed
        assert "key" in parsed


def test_state_object_lifecycle_management(wayland_server):
    """Test WaylandState object ID allocation and lifecycle management.

    This test exercises the object ID allocation, assignment, and deletion
    functionality of WaylandState, ensuring proper tracking of object
    references and IDs throughout their lifecycle.
    """
    import wayland
    from wayland.proxy import Proxy

    proxy = Proxy()
    state = proxy.state

    display = wayland.wl_display()
    registry = display.get_registry()

    wayland_server.get_request(timeout=1)

    assert state.object_exists(display.object_id, display)
    assert state.object_exists(registry.object_id, registry)

    assert state.object_id_to_object_reference(display.object_id) is display
    assert state.object_id_to_object_reference(registry.object_id) is registry
    assert state.object_id_to_object_reference(999) is None

    assert state.object_reference_to_object_id(display) == display.object_id
    assert state.object_reference_to_object_id(registry) == registry.object_id

    fake_object = object()
    assert state.object_reference_to_object_id(fake_object) == 0


def test_state_error_handling_scenarios(wayland_server):
    """Test WaylandState error handling for various edge cases.

    This test verifies that WaylandState properly handles error conditions
    such as invalid object IDs, duplicate assignments, and connection errors.
    """
    import pytest

    import wayland
    from wayland.exceptions import WaylandNotConnectedError
    from wayland.proxy import Proxy

    proxy = Proxy()
    state = proxy.state

    state._auto_connect = False
    state.disconnect()

    with pytest.raises(WaylandNotConnectedError):
        state.send_wayland_message(1, 0, b"")

    state._auto_connect = True
    with pytest.raises(ValueError, match="NULL object passed"):
        state.send_wayland_message(0, 0, b"")

    display = wayland.wl_display()

    with pytest.raises(ValueError, match="Duplicate object id"):
        state.assign_object_id(display.object_id, display)

    class FakeObject:
        def __init__(self):
            self.object_id = 999

    fake_object = FakeObject()

    assert not state.object_exists(999, fake_object)

    state.delete_object_reference(999, fake_object)


def test_state_event_resolution_and_dispatch(wayland_server):
    """Test WaylandState event resolution and message dispatch functionality.

    This test verifies that WaylandState can properly resolve object IDs to
    event handlers and dispatch incoming messages to the correct handlers.
    """
    import wayland
    from wayland.proxy import Proxy

    @wayland.client.wayland_class("wl_registry")
    class TestRegistry(wayland.wl_registry):
        def on_global(self, name, interface, version):
            if interface == "wl_seat":
                self.bind(name, "wl_seat", version)

    proxy = Proxy()
    state = proxy.state

    display = wayland.wl_display()
    registry = display.get_registry()

    wayland_server.get_request(timeout=1)
    wayland_server.send_global_event(registry.object_id, 1, "wl_seat", 1)
    display.dispatch_timeout(1)

    bind_request = wayland_server.get_request(timeout=1)
    seat_object_id = bind_request["data"][:4]
    seat_object_id = int.from_bytes(seat_object_id, byteorder="little")

    seat = state.object_id_to_object_reference(seat_object_id)
    assert seat is not None

    event_handler = state.object_id_to_event(seat_object_id, 0)
    assert event_handler is not None
    assert hasattr(event_handler, "opcode")
    assert event_handler.opcode == 0

    assert state.object_id_to_event(999, 0) is None
    assert state.object_id_to_event(seat_object_id, 999) is None


def test_state_message_processing_edge_cases(wayland_server):
    """Test WaylandState message processing edge cases and error handling.

    This test verifies that WaylandState properly handles various edge cases
    in message processing, including unhandled events and malformed messages.
    """
    import time

    import wayland
    from wayland.proxy import Proxy

    proxy = Proxy()
    state = proxy.state

    display = wayland.wl_display()
    display.get_registry()

    wayland_server.get_request(timeout=1)

    wayland_server.send_event(999, 999, b"")

    time.sleep(0.2)

    result = state.get_next_message()
    assert result is False


def test_state_threading_and_singleton_behavior():
    """Test WaylandState singleton behavior and thread safety.

    This test verifies that WaylandState maintains singleton behavior
    across multiple instantiation attempts and handles threading correctly.
    """
    import threading

    from wayland.proxy import Proxy
    from wayland.state import WaylandState

    instances = []

    def create_instance():
        proxy = Proxy()
        instances.append(proxy.state)

    threads = []
    for _ in range(5):
        thread = threading.Thread(target=create_instance)
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    first_instance = instances[0]
    for instance in instances[1:]:
        assert instance is first_instance

    direct_state = WaylandState(None)
    assert direct_state is first_instance


def test_proxy_singleton_behavior():
    """Test that Proxy maintains singleton behavior across multiple instantiations."""
    from wayland.proxy import Proxy

    proxy1 = Proxy()
    proxy2 = Proxy()
    proxy3 = Proxy()

    assert proxy1 is proxy2
    assert proxy2 is proxy3
    assert proxy1 is proxy3


def test_proxy_getitem_functionality():
    """Test Proxy's __getitem__ method for accessing attributes."""
    import pytest

    from wayland.proxy import Proxy

    proxy = Proxy()

    assert proxy["state"] is proxy.state

    with pytest.raises(KeyError, match="'nonexistent_key' not found"):
        _ = proxy["nonexistent_key"]


def test_event_handler_registration_and_removal(wayland_server):
    """Test event handler registration and removal functionality."""
    event_calls = []
    seat = None

    def handler1(capabilities):
        event_calls.append(("handler1", capabilities))

    def handler2(capabilities):
        event_calls.append(("handler2", capabilities))

    @wayland.client.wayland_class("wl_registry")
    class TestRegistry(wayland.wl_registry):
        def on_global(self, name, interface, version):
            nonlocal seat
            if interface == "wl_seat":
                seat = self.bind(name, "wl_seat", version)

    display = wayland.wl_display()
    registry = display.get_registry()

    wayland_server.get_request(timeout=1)
    wayland_server.send_global_event(registry.object_id, 1, "wl_seat", 1)
    display.dispatch_timeout(1)

    wayland_server.get_request(timeout=1)

    assert seat is not None

    seat.events.capabilities += handler1
    seat.events.capabilities += handler2
    seat.events.capabilities -= handler1

    wayland_server.send_capabilities_event(seat.object_id, 5)
    display.dispatch_timeout(1)

    assert len(event_calls) == 1
    assert event_calls[0] == ("handler2", 5)


def test_proxy_initialise_error_handling():
    """Test Proxy.initialise error handling for missing protocol files."""
    from wayland.proxy import Proxy

    proxy = Proxy()

    result = proxy.initialise(path="/nonexistent/path")
    assert result is False


def test_dynamic_object_bool_conversion(wayland_server):
    """Test DynamicObject __bool__ method based on object_id."""
    display = wayland.wl_display()
    registry = display.get_registry()

    assert bool(display) is True
    assert bool(registry) is True

    fake_object = wayland.wl_surface()
    fake_object.object_id = 0
    assert bool(fake_object) is False


def test_keyword_collision_handling(wayland_server):
    """Test that Python keyword collisions are handled properly in requests and events."""
    import keyword

    display = wayland.wl_display()

    for attr_name in dir(display):
        if hasattr(getattr(display, attr_name), "name"):
            request_name = getattr(display, attr_name).name
            if keyword.iskeyword(request_name.rstrip("_")):
                assert attr_name.endswith(
                    "_"
                ), f"Keyword collision not handled for {request_name}"


def test_proxy_scope_handling():
    """Test Proxy scope handling with different scope types."""
    from wayland.proxy import Proxy

    proxy = Proxy()

    dict_scope = {}
    result = proxy.initialise(scope=dict_scope)
    assert result is True
    assert "wl_display" in dict_scope

    class ObjectScope:
        pass

    object_scope = ObjectScope()
    result = proxy.initialise(scope=object_scope)
    assert result is True
    assert hasattr(object_scope, "wl_display")


def test_custom_factory_override_behavior(wayland_server):
    """Test that custom factories properly override default classes."""
    seat_instances = []

    class CustomSeat1(wayland.wl_seat):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            seat_instances.append(("CustomSeat1", self))

    class CustomSeat2(wayland.wl_seat):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            seat_instances.append(("CustomSeat2", self))

    wayland.client.register_factory("wl_seat", CustomSeat1)
    wayland.client.register_factory("wl_seat", CustomSeat2)

    @wayland.client.wayland_class("wl_registry")
    class TestRegistry(wayland.wl_registry):
        def on_global(self, name, interface, version):
            if interface == "wl_seat":
                self.bind(name, "wl_seat", version)

    display = wayland.wl_display()
    registry = display.get_registry()

    wayland_server.get_request(timeout=1)
    wayland_server.send_global_event(registry.object_id, 1, "wl_seat", 1)
    display.dispatch_timeout(1)
    wayland_server.get_request(timeout=1)

    assert len(seat_instances) == 1
    assert seat_instances[0][0] == "CustomSeat2"
