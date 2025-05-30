# Getting Started

This guide will help you get started with the python-wayland client API.


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