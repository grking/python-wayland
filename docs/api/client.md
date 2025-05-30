# Client API Reference

The `wayland.client` module provides the main interface for Python applications to interact with Wayland compositors.

## Overview

The client API consists of four main functions:

* [`initialise()`][wayland.client.initialise] - Initialize a Wayland client connection
* [`is_wayland()`][wayland.client.is_wayland] - Check if running under Wayland
* [`get_package_version()`][wayland.client.get_package_version] - Get library version
* [`get_package_root()`][wayland.client.get_package_root] - Get package directory

## Functions

::: wayland.client.initialise

::: wayland.client.is_wayland

::: wayland.client.get_package_version

::: wayland.client.get_package_root

## Usage Notes

### Thread Safety

The client API is not thread-safe. Use appropriate synchronization if accessing from multiple threads.

### Resource Management

The Wayland connection is automatically managed. Call `process_messages()` regularly to handle incoming events.

### Error Handling

Wayland errors are reported through the `wl_display.events.error` event. Always register an error handler:

```python
def on_error(object_id, code, message):
    print(f"Wayland error: {message}")

client.wl_display.events.error += on_error