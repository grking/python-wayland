# Getting Started

This guide will help you get started with the python-wayland client API.

## Installation

Install python-wayland using pip:

```bash
pip install python-wayland
```

## Requirements

* Python 3.8 or higher
* A Wayland compositor (for runtime use)

No additional dependencies are required - python-wayland is a pure Python implementation.

## Basic Usage

### 1. Check Wayland Environment

Before initializing the client, check if you're running under Wayland:

```python
import wayland.client

if wayland.client.is_wayland():
    print("Running under Wayland")
else:
    print("Not running under Wayland")
```

### 2. Initialize the Client

Create a client connection to the Wayland compositor:

```python
import wayland.client

# Initialize the client
client = wayland.client.initialise()
```

The `client` object provides access to all Wayland protocol interfaces.

### 3. Basic Wayland Operations

```python
import wayland.client

# Initialize client
client = wayland.client.initialise()

# Get the display registry
registry = client.wl_display.get_registry()

# Set up event handlers
def on_global(name, interface, version):
    print(f"Global: {interface} v{version}")

registry.events.global_ += on_global

# Process messages to receive events
client.process_messages()
```

### 4. Event Handling

Wayland uses an event-driven model. Register event handlers to respond to compositor events:

```python
def on_error(object_id, code, message):
    print(f"Error: {object_id} {code} {message}")

# Register error handler
client.wl_display.events.error += on_error
```

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

## Protocol Level Debugging

If you want to see a full wayland protocol level debug output when you run your app, set the environment variable `WAYLAND_DEBUG=1` before you run your application, e.g.:

```bash
# WAYLAND_DEBUG=1 python -m your_app
```


## Next Steps

* Browse the [API Reference](api/client.md) for detailed function documentation
* Check out [Examples](examples.md) for more complete usage patterns
* See the main [README](https://github.com/grking/python-wayland#readme) for advanced features

## Troubleshooting

### Not Running Under Wayland

If `is_wayland()` returns `False`, you may be running under X11. The library requires a Wayland compositor to function.

### Connection Issues

Ensure the `WAYLAND_DISPLAY` environment variable is set correctly and points to a valid Wayland socket.