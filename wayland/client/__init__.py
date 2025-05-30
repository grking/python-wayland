from __future__ import annotations

from os import getenv, path
from typing import TYPE_CHECKING, Any

from wayland.__about__ import __version__

if TYPE_CHECKING:
    from wayland.proxy import Proxy


def get_package_root() -> str:
    """Get the root directory of the wayland package.

    Returns:
        str: Absolute path to the wayland package directory.

    Example:
        >>> import wayland.client
        >>> root = wayland.client.get_package_root()
        >>> print(root)  # doctest: +SKIP
        /path/to/wayland
    """
    package_name = __package__.split(".")[0]
    package_module = __import__(package_name)
    return path.abspath(package_module.__path__[0])


def get_package_version() -> str:
    """Get the version of the wayland package.

    Returns:
        str: Version string in semantic versioning format (e.g., "1.0.0").

    Example:
        >>> import wayland.client
        >>> version = wayland.client.get_package_version()
        >>> print(version)  # doctest: +SKIP
        0.7.1
    """
    return __version__


def is_wayland() -> bool:
    """Check if the current session is running under Wayland.

    Determines if the current environment is using Wayland by checking
    the WAYLAND_DISPLAY and XDG_SESSION_TYPE environment variables.

    Returns:
        bool: True if running under Wayland, False otherwise.

    Example:
        >>> import wayland.client
        >>> if wayland.client.is_wayland():
        ...     print("Running under Wayland")
        ... else:
        ...     print("Not running under Wayland")  # doctest: +SKIP
    """
    return (
        "wayland" in getenv("WAYLAND_DISPLAY", "").lower()
        or "wayland" in getenv("XDG_SESSION_TYPE", "").lower()
    )


def initialise(_: Any | None = None) -> Proxy:
    """Initialize a Wayland client connection.

    Creates and returns a Proxy object that provides access to all Wayland
    protocol interfaces and methods. This is the main entry point for
    interacting with a Wayland compositor.

    Args:
        _: Unused parameter for compatibility. Defaults to None.

    Returns:
        wayland.proxy.Proxy: A proxy object containing all Wayland protocol methods.

    Example:
        >>> import wayland.client
        >>> client = wayland.client.initialise()
        >>> registry = client.wl_display.get_registry()
        >>> # Process Wayland events
        >>> client.process_messages()

    Note:
        This function automatically handles the Wayland socket connection
        and protocol initialization. The returned proxy object dynamically
        exposes all available Wayland interfaces.
    """
    from wayland.proxy import Proxy

    proxy = Proxy()
    proxy.initialise()
    return proxy
