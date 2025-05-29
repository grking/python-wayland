import mmap
import time

import wayland as wl

wayland = wl.client.initialise()


def test_keyboard():
    keymap = None
    have_keyboard = False

    def on_wl_registry_global(name, interface, version):
        if interface in ["wl_seat"]:
            wayland.wl_registry.bind(name, interface, version)

    def on_seat_capabilities(capabilities):
        if capabilities & capabilities.keyboard:
            wayland.wl_seat.get_keyboard()

    def on_keyboard_keymap(format, fd, size):
        nonlocal keymap
        nonlocal have_keyboard
        have_keyboard = True
        mapped_file = mmap.mmap(fd, 0, access=mmap.ACCESS_COPY)
        keymap = mapped_file.read(size)

    # Hook the event to get the registry results
    wayland.wl_registry.events.global_ += on_wl_registry_global
    wayland.wl_seat.events.capabilities += on_seat_capabilities
    wayland.wl_keyboard.events.keymap += on_keyboard_keymap

    wayland.wl_display.get_registry()

    start = time.time()
    while not keymap and time.time() < start + 3:
        time.sleep(0.1)
        wayland.process_messages()

    # If we don't have a keyboard, don't test it
    if not have_keyboard:
        return

    # Check we got some interfaces we should have
    assert keymap is not None
