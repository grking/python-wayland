from os import getenv, path

from wayland.__about__ import __version__


def get_package_root():
    # Returns the directory that this project is sitting in
    package_name = __package__.split(".")[0]
    package_module = __import__(package_name)
    return path.abspath(package_module.__path__[0])


def get_package_version():
    return __version__


def is_wayland():
    return (
        "wayland" in getenv("WAYLAND_DISPLAY", "").lower()
        or "wayland" in getenv("XDG_SESSION_TYPE", "").lower()
    )


def initialise(_=None):
    # Return an object that contains all the wayland interfaces
    from wayland.proxy import Proxy

    proxy = Proxy()
    proxy.initialise()
    return proxy
