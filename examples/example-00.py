# Print a list of Wayland global interfaces
# Class factory registration with decorator
import wayland
from wayland.client import wayland_class


@wayland_class("wl_registry")
class Registry(wayland.wl_registry):

    def on_global(self, name, interface, version):
        print(interface)


if __name__ == "__main__":

    display = wayland.wl_display()
    registry = display.get_registry()

    while True:
        display.dispatch_timeout(0.2)
