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

import contextlib
import os

from wayland.proxy import Proxy


def get_package_root():
    # Returns the directory that this project is sitting in
    package_name = __package__.split(".")[0]
    package_module = __import__(package_name)
    return os.path.abspath(package_module.__path__[0])


def initialise(auto=None):
    if auto:
        proxy = Proxy()
        proxy.initialise(globals(), get_package_root())
        return

    proxy = Proxy()
    proxy.initialise(proxy, get_package_root())
    return proxy


# Auto initialise if we are running under wayland
__should_init = os.getenv("WAYLAND_INITIALISE", "") == "TRUE"
__environment = os.getenv("WAYLAND_DISPLAY", "")
if not __environment:
    __environment = os.getenv("XDG_SESSION_TYPE", "")
__should_init = "wayland" in __environment.lower() or __should_init
if __should_init:
    with contextlib.suppress(FileNotFoundError):
        initialise(True)
