# Examples

This page provides practical examples of using the python-wayland client API.

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