# python-wayland

[![PyPI - Version](https://img.shields.io/pypi/v/python-wayland.svg)](https://pypi.org/project/python-wayland) [![Tests](https://github.com/grking/python-wayland/actions/workflows/run-tests.yml/badge.svg?branch=main)](https://github.com/grking/python-wayland/tree/main) [![PyPI - Python Version](https://img.shields.io/pypi/pyversions/python-wayland.svg)](https://pypi.org/project/python-wayland)

A Python implementation of the Wayland protocol, from scratch, with no external dependencies, not even any dependency on any Wayland libraries.

This seeks to be a Python implementation of libwayland-client.

## Features

* Includes support for all standard Wayland protocols and extensions from Hyprland and wlroots.
* No external dependencies, needs no Wayland libraries, and only Python standard libraries at runtime. This is a replacement for libwayland-client, not a wrapper for it.
* Maintains the original Wayland naming conventions to ensure references such as https://wayland.app are easy to use.
* Supports updating protocol definitions from either the local system or the latest official protocol repositories. Although protocols as of the `python-wayland` release date are built-in.
* Intellisense code completion support for methods and events. (tested in vscode).

## Naming Compatibility

Wayland identifiers that collide with Python builtin keywords are renamed to end with an underscore. There are very few of these. The list of known protocols that have changes are:

* `wayland.wl_registry.global` renamed to `global_`
* `xdg_foreign_unstable_v1.zxdg_importer_v1.import` renamed to `import_`

Enums with integer names, which are not permitted in Python, have the value prefixed with the name of the enum. This is also very rare, at the time of writing the below example is the only case in the stable and staging protocols.

For example:

```python
class wl_output.transform(Enum):
    normal: int
    90: int
    180: int
    270: int
    flipped: int
    flipped_90: int
    flipped_180: int
    flipped_270: int
```

becomes:

```python
class wl_output.transform(Enum):
    normal: int
    transform_90: int
    transform_180: int
    transform_270: int
    flipped: int
    flipped_90: int
    flipped_180: int
    flipped_270: int
```

## Making Wayland Requests

Requests are made in the standard manner, with the exception that `new_id` arguments should be omitted. There is no need to pass an integer ID for the object you want to create, that is handled automatically for you. An instance of the object created is simply returned by the request.

So the request signature is _not_ this:

```python
wayland.wl_display.get_registry( some_integer: new_id ) -> None
```

It has become simply this:

```python
wayland.wl_display.get_registry() -> wl_registry
```

Where `wl_registry` is an instance of the interface created.

## Event Handlers

Events are collected together under the `events` attribute of an interface. Define event handlers:

```python
    def on_error(self, object_id, code, message):
        print(f"Fatal error: {object_id} {code} {message}")
        sys.exit(1)
```

Register an event handler by adding it to the relevant event:

```python
    wayland.wl_display.events.error += self.on_error
```

The order of parameters in the event handler doesn't matter.

## Processing Events

To process all pending wayland events and call any registered event handlers:

```python
wayland.process_messages()
```

## Refreshing Protocols

The package is installed with the latest Wayland stable and staging protocols already built-in (`wayland/protocols.json`). Refreshing the protocol definitions is optional. It requires the python library `lxml` to be installed.

To rebuild the Wayland protocols from the locally installed protocol definitions:

```bash
python -m wayland
```

To rebuild the protocols directly from the online sources:

```bash
python -m wayland --download
```

Add the `--verbose` command line switch if you want to see progress of the protocol parsing.

## Checking Wayland Protocols

To produce a report which compares the locally installed Wayland protocol files with the latest online versions:

```bash
python -m wayland --compare
```

Example output:

    Protocol definitions which have been updated:
    
    None
    
    Available remote protocol definitions, but not installed locally:
    
    ext_image_capture_source_v1: version 1
    ext_output_image_capture_source_manager_v1: version 1
    ext_foreign_toplevel_image_capture_source_manager_v1: version 1
    
    Protocol definitions installed locally but not in official stable or staging repositories:
    
    zwp_fullscreen_shell_v1: version 1
    zwp_fullscreen_shell_mode_feedback_v1: version 1
    zwp_idle_inhibit_manager_v1: version 1

## Protocol Level Debugging

Set the environment variable `WAYLAND_DEBUG=1` before you your application, e.g.:

```bash
# WAYLAND_DEBUG=1 python -m your_app
```

## Development of python-wayland

For developing `python-wayland` itself, rather than using it, the following may be handy. `python-wayland` is configured for `hatch`.  

You can install `hatch` through `pipx`. A full bootstrap may look like:

```bash
# Install pipx
sudo apt-get install pipx  # debian / ubuntu
sudo pacman -S python-pipx  # arch

# Install hatch with pipx
pipx install hatch
```

* Run tests with `hatch test`
* Run lint check with `hatch fmt`
* Build the wheel with `hatch build`

## Thanks

Thanks to Philippe Gaultier, whose article [Wayland From Scratch](https://gaultier.github.io/blog/wayland_from_scratch.html) inspired this project.

