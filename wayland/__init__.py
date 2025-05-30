# Copyright (c) 2024 Graham R King
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice (including the
# next paragraph) shall be included in all copies or substantial
# portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT.  IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from os import getenv as __getenv

# Wayland methods are injected into the package global scope
# so, for example, "wayland.wl_display" just works. This is
# purely syntactic sugar for library callers.
if __getenv("WAYLAND_INITIALISE", "").lower() != "false" and (
    __getenv("WAYLAND_INITIALISE", "").lower() == "true"
    or "wayland" in __getenv("WAYLAND_DISPLAY", "").lower()
    or "wayland" in __getenv("XDG_SESSION_TYPE", "").lower()
):
    from wayland.proxy import Proxy

    __dynamic_object = Proxy.DynamicObject

    __proxy = Proxy()
    __proxy.initialise(globals())

    # Clean up namespace - keep only dynamic objects, dunder methods, and "client"
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
