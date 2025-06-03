# Copyright (c) 2024-2025 Graham R King
# Licensed under the MIT License. See LICENSE file for details.

from os import getenv as __getenv

from wayland import client as client  # noqa: PLC0414

# Wayland methods are injected into the package global scope
# so, for example, "wayland.wl_display" just works. This is
# purely syntactic sugar for library callers.
if __getenv("WAYLAND_INITIALISE", "").lower() != "false" and not hasattr(
    globals(), "wl_display"
):
    from wayland.proxy import Proxy

    __dynamic_object = Proxy.DynamicObject

    __proxy = Proxy()
    __proxy.initialise(globals())

    # Clean up namespace - keep only dynamic objects,
    # dunder methods, and "client"
    __keys_to_delete = []
    for __key in list(globals().keys()):
        if (
            (not __key.startswith("__"))
            and __key != "client"
            and not isinstance(globals()[__key], __dynamic_object)
        ):
            __keys_to_delete.append(__key)

    # Delete the collected keys
    for __key in __keys_to_delete:
        del globals()[__key]

    # Clean up temporary variables
    del __keys_to_delete, __key, __dynamic_object, __proxy

del __getenv
