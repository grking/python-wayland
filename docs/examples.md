# Examples

This page provides practical examples of using the python-wayland client API.

## Basic Example

Wayland is a low level protocol and therefore fairly verbose. The following example connects to the compositor, requests information on the current displays and prints it. For example:

```text
Sharp Corporation LQ173M1JW12  (eDP-1)
  Resolution: 1920x1080 @ 360.0Hz
  Monitor: Sharp Corporation LQ173M1JW12
  Position: 0, 0
  Physical size: 380x210mm

Sharp Corporation LQ173M1JW12  (eDP-2)
  Resolution: 1920x1080 @ 360.0Hz
  Monitor: Sharp Corporation LQ173M1JW12
  Position: 1, 0
  Physical size: 380x210mm
```

It is a simple implementation which demonstrates:

* Accessing some core wayland interfaces
* Handling wayland events
* Event loop message processing with `wayland.process_messages()`
* Handling multiple object instances with individual handlers
* Synchronisation with `done` events.

```python
# Print information about the available displays.
import wayland
import time

displays_done = 0
total_displays = 0

# Define some basic event handlers
def on_error(object_id, code, message):
    # See: https://wayland.app/protocols/wayland#wl_display:event:error
    print(f"Fatal error: {object_id} {code} {message}")
    exit(1)


def on_wl_registry_global(name, interface, version):
    global total_displays

    # See: https://wayland.app/protocols/wayland#wl_registry:event:global
    if interface == "wl_output":
        # "output" here is actually an object instance, we ignore that
        # fact for the purposes of this simple example. In a real implementation
        # we could handle these events in a more object oriented manner.
        output = wayland.wl_registry.bind(name, interface, version)
        total_displays += 1
    else:
        return

    def make_handlers():
        def on_geometry(
            x, y, physical_width, physical_height, subpixel, make, model, transform
        ):
            # See: https://wayland.app/protocols/wayland#wl_output:event:geometry
            print(f"  Monitor: {make} {model}")
            print(f"  Position: {x}, {y}")
            print(f"  Physical size: {physical_width}x{physical_height}mm")

        def on_mode(flags, width, height, refresh):
            # See: https://wayland.app/protocols/wayland#wl_output:event:mode
            if flags & 1:  # Current mode
                print(f"  Resolution: {width}x{height} @ {refresh / 1000:.1f}Hz")

        def on_description(description):
            # See: https://wayland.app/protocols/wayland#wl_output:event:description
            print(f"{description}")

        def on_done():
            # See: https://wayland.app/protocols/wayland#wl_output:event:done
            global displays_done
            displays_done += 1

        return on_geometry, on_mode, on_description, on_done

    geo, mode, desc, done = make_handlers()
    output.events.geometry += geo
    output.events.mode += mode
    output.events.description += desc
    output.events.done += done


# Register our event handlers
wayland.wl_registry.events.global_ += on_wl_registry_global
wayland.wl_display.events.error += on_error

# Request the global registry from the wayland compositor
# See https://wayland.app/protocols/wayland#wl_display:request:get_registry
wayland.wl_display.get_registry()

# Simple event loop to get the responses
while not displays_done or displays_done < total_displays:
    wayland.process_messages()
    time.sleep(0.1)
```

## Basic Client Setup

```python
import wayland.client

def main():
    # Check if we're running under Wayland
    if not wayland.client.is_wayland():
        print("Not running under Wayland")
        return

    # Initialize the client
    client = wayland.client.initialise()

    # Get the registry
    registry = client.wl_display.get_registry()

    # Process initial messages
    client.process_messages()

if __name__ == "__main__":
    main()
```

## Discovering Available Interfaces

```python
import wayland.client

def discover_interfaces():
    client = wayland.client.initialise()
    registry = client.wl_display.get_registry()

    # Store discovered globals
    globals_list = []

    def on_global(name, interface, version):
        globals_list.append({
            'name': name,
            'interface': interface,
            'version': version
        })
        print(f"Found: {interface} v{version}")

    # Register the global event handler
    registry.events.global_ += on_global

    # Process messages to discover interfaces
    client.process_messages()

    return globals_list

# Usage
interfaces = discover_interfaces()
for iface in interfaces:
    print(f"Interface: {iface['interface']}")
```

## Error Handling

```python
import wayland.client
import sys

def setup_error_handling(client):
    def on_error(object_id, code, message):
        print(f"Fatal Wayland error: {message}")
        print(f"Object ID: {object_id}, Code: {code}")
        sys.exit(1)

    # Register error handler
    client.wl_display.events.error += on_error

def main():
    client = wayland.client.initialise()
    setup_error_handling(client)

    # Your application logic here
    registry = client.wl_display.get_registry()
    client.process_messages()
```

## Event Loop Integration

```python
import wayland.client

class WaylandApp:
    def __init__(self):
        self.client = wayland.client.initialise()
        self.setup_events()

    def setup_events(self):
        # Error handling
        self.client.wl_display.events.error += self.on_error

        # Registry events
        registry = self.client.wl_display.get_registry()
        registry.events.global_ += self.on_global
        registry.events.global_remove += self.on_global_remove

    def on_error(self, object_id, code, message):
        print(f"Error: {message}")

    def on_global(self, name, interface, version):
        print(f"Global added: {interface}")

    def on_global_remove(self, name):
        print(f"Global removed: {name}")

    def run(self):
        # Main event loop
        while True:
            # Process Wayland messages
            self.client.process_messages()

            # Your application logic here
            # Note: In a real app, you'd want proper event loop integration

# Usage
app = WaylandApp()
app.run()
```

## Version and Environment Information

```python
import wayland.client

def print_environment_info():
    print(f"python-wayland version: {wayland.client.get_package_version()}")
    print(f"Package root: {wayland.client.get_package_root()}")
    print(f"Running under Wayland: {wayland.client.is_wayland()}")

    # Additional environment details
    import os
    print(f"WAYLAND_DISPLAY: {os.getenv('WAYLAND_DISPLAY', 'Not set')}")
    print(f"XDG_SESSION_TYPE: {os.getenv('XDG_SESSION_TYPE', 'Not set')}")

print_environment_info()
```

## Surface Creation (Advanced)

```python
import wayland.client

def create_surface():
    client = wayland.client.initialise()
    registry = client.wl_display.get_registry()

    compositor = None

    def on_global(name, interface, version):
        nonlocal compositor
        if interface == 'wl_compositor':
            # Bind to the compositor interface
            compositor = registry.bind(name, interface, version)

    registry.events.global_ += on_global
    client.process_messages()

    if compositor:
        # Create a surface
        surface = compositor.create_surface()
        print("Surface created successfully")
        return surface
    else:
        print("Compositor not found")
        return None

# Usage
surface = create_surface()
```

## Common Patterns

### Synchronization

```python
def sync_with_compositor(client):
    """Wait for all pending operations to complete"""
    callback = client.wl_display.sync()

    done = False
    def on_done(callback_data):
        nonlocal done
        done = True

    callback.events.done += on_done

    # Process messages until sync is complete
    while not done:
        client.process_messages()
```

### Resource Cleanup

```python
def cleanup_resources(objects):
    """Properly destroy Wayland objects"""
    for obj in objects:
        if hasattr(obj, 'destroy'):
            obj.destroy()
```

These examples demonstrate the core patterns for using the python-wayland client API. For more complex applications, refer to the Wayland protocol documentation and the library's test suite.