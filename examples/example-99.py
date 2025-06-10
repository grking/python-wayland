import wayland

displays_done = 0
total_displays = 0

# Define some basic event handlers
def on_error(object_id, code, message):
    # See: https://python-wayland.org/wayland/wl_display/#wayland.wl_display.events.error
    print(f"Fatal error: {object_id} {code} {message}")
    exit(1)


def on_wl_registry_global(name, interface, version):
    global total_displays

    # See: https://python-wayland.org/wayland/wl_registry/#wayland.wl_registry.events.global_
    if interface == "wl_output":
        # "output" here is actually an object instance, we ignore that
        # fact for the purposes of this simple example. In a real implementation
        # we could handle these events in a more object oriented manner.
        output = wayland.wl_registry.bind(name, interface, version)
        total_displays += 1
    else:
        return

    def make_handlers():
        def on_geometry(
            x, y, physical_width, physical_height, subpixel, make, model, transform
        ):
            # See: https://python-wayland.org/wayland/wl_output/#wayland.wl_output.events.geometry
            print(f"  Monitor: {make} {model}")
            print(f"  Position: {x}, {y}")
            print(f"  Physical size: {physical_width}x{physical_height}mm")

        def on_mode(flags, width, height, refresh):
            # See: https://python-wayland.org/wayland/wl_output/#wayland.wl_output.events.mode
            if flags & 1:  # Current mode
                print(f"  Resolution: {width}x{height} @ {refresh / 1000:.1f}Hz")

        def on_description(description):
            # See: https://python-wayland.org/wayland/wl_output/#wayland.wl_output.events.description
            print(f"{description}")

        def on_done():
            # See: https://python-wayland.org/wayland/wl_output/#wayland.wl_output.events.done
            global displays_done
            displays_done += 1

        return on_geometry, on_mode, on_description, on_done

    geo, mode, desc, done = make_handlers()
    output.events.geometry += geo
    output.events.mode += mode
    output.events.description += desc
    output.events.done += done


# Register our event handlers
wayland.wl_registry.events.global_ += on_wl_registry_global
wayland.wl_display.events.error += on_error

# Request the global registry from the wayland compositor
# See https://python-wayland.org/wayland/wl_display/#wayland.wl_display.get_registry
wayland.wl_display.get_registry()

# Simple event loop to get the responses
while not displays_done or displays_done < total_displays:
    wayland.wl_display.dispatch_timeout(0.1)
