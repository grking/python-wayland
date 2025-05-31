from os import path

from wayland.__about__ import __version__


def get_package_root() -> str:
    """Get the root directory of the package.

    Returns:
        Absolute path to the wayland package directory.
    """
    package_name = __package__.split(".")[0]
    package_module = __import__(package_name)
    return path.abspath(package_module.__path__[0])


def get_package_version() -> str:
    """Get the version of the wayland package.

    Examples:
        Print the current library version

        >>> print(wayland.client.get_package_version())
        0.9.0

    Returns:
        Version string in semantic versioning format (e.g., "1.0.0").

    """
    return __version__
