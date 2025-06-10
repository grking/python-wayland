# Copyright (c) 2024-2025 Graham R King
# Licensed under the MIT License. See LICENSE file for details.

from os import getenv
from typing import TYPE_CHECKING

from wayland.debugger import Debugger

if TYPE_CHECKING:
    from wayland.proxy import Proxy as Proxy  # noqa: PLC0414


def get_wayland_proxy() -> object:
    """Return a proxy object containing all the wayland interfaces.

    Creates and returns a Proxy object that provides access to all Wayland
    protocol interfaces.

    Note:
        This is handled automatically and you do not normally
        need to call this. The `wayland` package namespace already exposes all
        the wayland interfaces, for example `wayland.wl_display`.

    Returns:
        wayland.proxy.Proxy: A proxy object containing all Wayland protocol interfaces.
    """
    from wayland.proxy import Proxy

    proxy = Proxy()
    proxy.initialise()
    return proxy


def is_wayland() -> bool:
    """Check if the current session is running under Wayland.

    Determines if the current environment is using Wayland by checking
    the WAYLAND_DISPLAY and XDG_SESSION_TYPE environment variables.

    Returns:
        True if running under Wayland, False otherwise.

    Examples:
        When running Wayland:

        >>> import wayland
        >>> wayland.client.is_wayland()
        True
    """
    return (
        "wayland" in getenv("WAYLAND_DISPLAY", "").lower()
        or "wayland" in getenv("XDG_SESSION_TYPE", "").lower()
    )


def start_debug_server() -> str:
    """Enable the Wayland protocol debugging service.

    You can debug the requests and events between your application
    and the Wayland compositor easily using the debugger
    included with `python-wayland`.

    Simply enable debugging in your application and then
    use the stand-alone debugger to monitor Wayland messages
    as your application is running.

    Step 1: To enable protocol debugging in your application
    call `start_debug_server`. This call returns immediately.

    ```python
    wayland.client.start_debug_server()
    ```

    Step 2: Run your application and then start the protocol debugger:

    ```bash
    python -m wayland.client.debug
    ```

    This will start the terminal protocol debugger:

    ![Wayland debugger interface](../assets/images/wayland-debugger.png)

    You could also connect to your application directly using the file socket
    that `start_debug_server` opened with a utility such as `socat`:

    ```bash
    socat - ABSTRACT-CONNECT:python-wayland-debug
    ```

    Returns:
        The name of the abstract file socket on which the server is listening.
    """
    debug = Debugger()
    return debug.start_debug_server()


# Simple decorator function
def wayland_class(interface_name):
    """
    A decorator to register a custom class to be used anytime
    Wayland objects of a specific interface are created.

    Whenever any instance of the given Wayland interface is created
    an instance of the registered custom class will be created in
    place of the default class.

    Examples:
        Register our own class `MyRegistry` to be instantiated
        whenever a `wl_registry` object is created:

        @wayland_class('wl_registry')
        class MyRegistry(wayland.Wl_registry): ...

    See also `register_factory` for an explicit method of
    class registration.
    """
    from wayland.proxy import Proxy

    def decorator(cls):
        proxy = Proxy()
        proxy.register_factory(interface_name, cls)
        return cls

    return decorator


# Module-level function for clean API
def register_factory(interface_name: str, custom_class):
    """
    Register a custom class to be used anytime Wayland objects of a
    specific interface are created.

    Whenever any instance of the given Wayland interface is created
    an instance of the registered custom class will be created in
    place of the default class.

    See also the decorator `@wayland_class`, which provides
    another way to register custom classes.

    Args:
        interface_name: The wayland interface name (e.g., 'wl_registry')
        custom_class: The custom class to use for this interface

    Usage:
        wayland.register_factory('wl_registry', MyRegistry)
    """
    from wayland.proxy import Proxy

    proxy = Proxy()
    return proxy.register_factory(interface_name, custom_class)


__all__ = ["get_wayland_proxy", "is_wayland", "start_debug_server"]
