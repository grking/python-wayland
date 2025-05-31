import wayland as wl

wayland = wl.client.get_wayland_proxy()


def test_get_registry():
    protocols = ["wl_shm", "xdg_wm_base", "wl_compositor"]

    received_protocols = []

    def on_wl_registry_global(name, interface, version):
        nonlocal received_protocols
        received_protocols.append(interface)

    # Hook the event to get the registry results
    wayland.wl_registry.events.global_ += on_wl_registry_global
    wayland.wl_display.get_registry()
    wayland.wl_display.dispatch_timeout(2.0)

    # Check we got some interfaces we should have
    for proto in protocols:
        if proto not in received_protocols:
            # Wait bit longer
            wayland.wl_display.dispatch_timeout(2.0)
        assert proto in received_protocols
