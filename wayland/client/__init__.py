from os import getenv
from typing import TYPE_CHECKING

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


__all__ = ["get_wayland_proxy", "is_wayland"]
