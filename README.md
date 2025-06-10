# python-wayland

[![PyPI - Version](https://img.shields.io/pypi/v/python-wayland.svg)](https://pypi.org/project/python-wayland) [![Tests](https://github.com/grking/python-wayland/actions/workflows/run-tests.yml/badge.svg?branch=main)](https://github.com/grking/python-wayland/tree/main) [![PyPI - Python Version](https://img.shields.io/pypi/pyversions/python-wayland.svg)](https://pypi.org/project/python-wayland) [![Documentation](https://img.shields.io/badge/docs-latest-blue.svg)](https://python-wayland.org)

A pure Python implementation of the Wayland protocol, from scratch, with no external run-time dependencies. The Wayland C client libraries are not required.

> [!WARNING]
> The development version is in the middle of significant redesign and refactor. See [CHANGELOG.md](CHANGELOG.md) for details.

## Features

* Includes support for all standard Wayland protocols and extensions from Hyprland and wlroots.
* No external dependencies, needs no Wayland libraries, and only Python standard libraries at run-time. This is a replacement for libwayland-client, not a wrapper for it.
* Maintains the original Wayland naming conventions to ensure Wayland API documentation remains relevant and easy to use.
* Supports updating protocol definitions from either the local system or the latest official protocol repositories. Although protocols as at the `python-wayland` release date are built-in.
* Intellisense code completion support for Wayland methods and events. (tested in vscode).

## Documentation

For documentation on how to use `python-wayland` see the [online documentation](https://python-wayland.org)

## Thanks

Thanks to Philippe Gaultier, whose article [Wayland From Scratch](https://gaultier.github.io/blog/wayland_from_scratch.html) inspired this project.

Thanks also to Drew DeVault for his [freely available Wayland book](https://wayland-book.com/). This project would not have been developed if not for Drew's book.

Thanks to the [`mkdocstrings` project](https://github.com/mkdocstrings/mkdocstrings), not only for the `mkdocstrings` plugin to [MkDocs](https://www.mkdocs.org/) but also because the configuration of the `python-wayland` documentation is almost entirely copied from the excellent work done by the `mkdocstrings` project in [their own documentation](https://mkdocstrings.github.io/).