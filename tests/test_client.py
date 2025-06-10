import wayland
from wayland.client import wayland_class


def test_initial_connection_and_global_discovery(wayland_server):
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
