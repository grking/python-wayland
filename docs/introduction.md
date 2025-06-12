# Getting Started: A Simple Example

Let's start by connecting to a Wayland compositor and discovering what global interfaces it provides:

```python
--8<-- "examples/00-simple-decorator.py"
```

Running this code produces output like:

```bash
wl_seat (version 9)
wl_data_device_manager (version 3)
wl_compositor (version 6)
wl_subcompositor (version 1)
wl_shm (version 1)
wp_viewporter (version 1)
```

## Understanding the Code

Let's break down what's happening in this example:

### 1. Imports

```python
import wayland
from wayland import wayland_class
```

We import the main library and the [`wayland_class`][wayland.client.wayland_class] decorator, which provides a convenient way to register custom interface implementations.

### 2. Custom Registry Class

```python
@wayland_class("wl_registry")
class Registry(wayland.wl_registry):
```

Here we create a custom class that extends [`wl_registry`][wayland.wl_registry]. The decorator tells `python-wayland` to use our custom class whenever a `wl_registry` object is created.

### 3. Event Handler Method

```python
    def on_global(self, name, interface, version):
        print(f"{interface} (version {version})")
```

This demonstrates implicit event handler registration. Methods named `on_` followed by an event name are automatically registered as handlers. In this case, `on_global` will handle all [`global`][wayland.wl_registry.events.global_] events from the registry.

> **Note:** There are other ways to register event handlers, which we'll explore in later sections.

### 4. Creating the Display

```python
display = wayland.wl_display()
```

This creates a [`wl_display`][wayland.wl_display] instance—the fundamental Wayland object (ID 1). In `python-wayland`, this object includes essential functionality like connection management and event dispatching, similar to `libwayland-client`.

At this point, we haven't connected to the compositor yet. The connection happens automatically when needed.

### 5. Getting the Registry

```python
registry = display.get_registry()
```

The [`get_registry`][wayland.wl_display.get_registry] method creates a registry instance. Since we registered our custom class, this returns an instance of `Registry` rather than the default `wl_registry`.

This call triggers:

* Automatic connection to the Wayland compositor (if not already connected)
* The compositor immediately sends [`global`][wayland.wl_registry.events.global_] events for all available interfaces

> **Important:** An exception will be raised here if no Wayland compositor is available.

### 6. Event Loop

```python
while True:
    display.dispatch_timeout(0.2)
```

This simple event loop continuously processes Wayland events. The [`dispatch_timeout`][wayland.wl_display.dispatch_timeout] method:

* Dispatches any pending events to their handlers
* Blocks for up to 0.2 seconds waiting for new events
* Returns when events are processed or the timeout expires

As [`global`][wayland.wl_registry.events.global_] events arrive, our `on_global` handler prints each interface name and version.

## Next Steps

This example demonstrated the basics of:

* Connecting to a Wayland compositor
* Implementing custom interface classes
* Handling Wayland events
* Running an event loop

See [further examples](examples.md).

_More documentation to be written_