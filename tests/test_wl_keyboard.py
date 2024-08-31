import mmap
import time

import wayland

WAYLAND_DELAY = 0.5


def test_keyboard():
    keymap = None

    def on_wl_registry_global(name, interface, version):
        if interface in ["wl_seat", "wl_keyboard"]:
            wayland.wl_registry.bind(name, interface, version)

    def on_seat_capabilities(capabilities):
        if capabilities & 2:
            wayland.wl_seat.get_keyboard()

    def on_keyboard_keymap(format, fd, size):
        nonlocal keymap
        mapped_file = mmap.mmap(fd, 0, access=mmap.ACCESS_COPY)
        keymap = mapped_file.read(size)

    # Hook the event to get the registry results
    wayland.wl_registry.events.global_ += on_wl_registry_global
    wayland.wl_seat.events.capabilities += on_seat_capabilities
    wayland.wl_keyboard.events.keymap += on_keyboard_keymap

    wayland.wl_display.get_registry()

    start = time.time()
    while not keymap and time.time() < start + 5:
        time.sleep(0.1)
        wayland.process_messages()
    # Check we got some interfaces we should have
    assert keymap is not None
