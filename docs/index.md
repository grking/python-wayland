# python-wayland Client API

A Python implementation of the Wayland protocol, from scratch, with no external dependencies, not even any dependency on any Wayland libraries.

This documentation covers the **client API** provided by the `wayland.client` module - the main interface for Python applications to interact with Wayland compositors.

## Features

* **Pure Python**: No external dependencies, needs no Wayland libraries
* **Complete Protocol Support**: Includes support for all standard Wayland protocols and extensions
* **Type Safety**: Full type hints for better development experience
* **Intellisense Support**: Code completion for methods and events
* **Compatibility**: Maintains original Wayland naming conventions

## Quick Start

```python
import wayland.client

# Check if running under Wayland
if wayland.client.is_wayland():
    # Initialize the client
    client = wayland.client.initialise()

    # Get the registry to discover available interfaces
    registry = client.wl_display.get_registry()

    # Process Wayland messages
    client.process_messages()
```

## Navigation

* **[Getting Started](getting-started.md)** - Installation and basic usage
* **[API Reference](api/client.md)** - Complete client API documentation
* **[Examples](examples.md)** - Practical usage examples

## About

This library seeks to be a Python implementation of libwayland-client, providing a replacement rather than a wrapper for the native C library.

For more information about the complete library, see the [main repository](https://github.com/grking/python-wayland).