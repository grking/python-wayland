# Print information about the available display outputs.
import wayland
from wayland.client import wayland_class


@wayland_class("wl_registry")
class Registry(wayland.wl_registry):

    def __init__(self):
        super().__init__()
        self.outputs = []

    def on_global(self, name, interface, version):
        if interface == "wl_output":
            output = self.bind(name, interface, version)
            self.outputs.append(output)
        else:
            return  # ignore all other interfaces


@wayland_class("wl_output")
class Output(wayland.wl_output):

    def __init__(self):
        super().__init__()
        self.done = False

    def on_geometry(
        self, x, y, physical_width, physical_height, subpixel, make, model, transform
    ):
        print(f"  Monitor: {make} {model}")
        print(f"  Position: {x}, {y}")
        print(f"  Physical size: {physical_width}x{physical_height}mm")

    def on_mode(self, flags, width, height, refresh):
        if flags & 1:  # Current mode
            print(f"  Resolution: {width}x{height} @ {refresh / 1000:.1f}Hz")

    def on_description(self, description):
        print(f"{description}")

    def on_done(self):
        self.done = True


# Request the global registry from the wayland compositor
display = wayland.wl_display()
registry = display.get_registry()

# Simple event loop to get the responses
while not registry.outputs or not all(output.done for output in registry.outputs):
    display.dispatch_timeout(0.1)
