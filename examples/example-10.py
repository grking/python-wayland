# Print a list of Wayland global interfaces
# Explicit class factory registration
import wayland
from wayland.client import register_factory


class Registry(wayland.wl_registry):

    def on_global(self, name, interface, version):
        print(f'{name},"{interface}",{version}')


if __name__ == "__main__":

    register_factory("wl_registry", Registry)

    display = wayland.wl_display()
    registry = display.get_registry()

    while True:
        display.dispatch_timeout(0.2)
