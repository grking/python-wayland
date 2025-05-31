import wayland as wl

wayland = wl.client.get_wayland_proxy()


def test_display_singleton():
    assert wayland.wl_display.object_id == 1
