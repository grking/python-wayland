# python-wayland

[![PyPI - Version](https://img.shields.io/pypi/v/python-wayland.svg)](https://pypi.org/project/python-wayland) [![Tests](https://github.com/grking/python-wayland/actions/workflows/run-tests.yml/badge.svg?branch=main)](https://github.com/grking/python-wayland/tree/main) [![PyPI - Python Version](https://img.shields.io/pypi/pyversions/python-wayland.svg)](https://pypi.org/project/python-wayland)

A pure Python implementation of the Wayland protocol, from scratch, with no external runtime dependencies. The Wayland C client libraries are not required.

## Features

* Includes support for all standard Wayland protocols and extensions from Hyprland and wlroots.
* No external dependencies, needs no Wayland libraries, and only Python standard libraries at runtime. This is a replacement for libwayland-client, not a wrapper for it.
* Maintains the original Wayland naming conventions to ensure references such as [wayland.app](https://wayland.app) are easy to use.
* Supports updating protocol definitions from either the local system or the latest official protocol repositories. Although protocols as at the `python-wayland` release date are built-in.
* Intellisense code completion support for wayland methods and events. (tested in vscode).

## Documentation

For documentation on how to use `python-wayland` see the [documentation](https://python-wayland.readthedocs.io/en/latest/)

## Thanks

Thanks to Philippe Gaultier, whose article [Wayland From Scratch](https://gaultier.github.io/blog/wayland_from_scratch.html) inspired this project.

Thanks also to Drew DeVault, who [freely available Wayland book](https://wayland-book.com/) which was an essential resource in developing this library.