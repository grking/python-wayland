# Introduction
`python-wayland` is a pure Python implementation of the Wayland protocol, focused on the development of Wayland clients rather than compositors.

Wayland interfaces are exposed with the original Wayland naming convention by default, rather than renaming them into a more Pythonic form. This is so [wayland API documentation](https://python-wayland.org/wayland) and other Wayland references are directly useful and relevant to the use of this library.

Wayland names are renamed if they clashes with Python keywords, see [Wayland/Python Naming Conflicts](naming.md) for details.

## A Basic Example

Here we connect to the Wayland compositor and print a list of the available global interfaces and their version numbers.

```python
import wayland
from wayland import wayland_class

@wayland_class("wl_registry")
class Registry(wayland.wl_registry):

    def on_global(self, name, interface, version):
        print(interface)

display = wayland.wl_display()
registry = display.get_registry()
while True:
    display.dispatch_timeout(0.2)
```

Let's break that down and take a look at what's happening in more detail.

```python
import wayland
from wayland import wayland_class
```

The main `wayland` package is imported and we choose to import the optional `wayland_class` decorator. This is one of the available methods for registering our own custom classes which can inherit from the Wayland classes and override or extend their functionality.

```python
@wayland_class("wl_registry")
class Registry(wayland.wl_registry):
```

We define our own class named `Registry` inheriting from the Wayland interface `wl_registry`. The decorator provides a shortcut to tell `python-wayland` that anytime a object of the type `wl_registry` is created it should create an instance of our own custom class rather than the default class.

```python
    def on_global(self, name, interface, version):
        print(interface)
```

This is one way of registering event handlers, an implicit event handler using a method naming convention. If we define methods starting with `on_` followed by the name of the Wayland event, those methods will be automatically bound as an event handler for us.

Our `on_global` method will be automatically called for every `global` event that the `wl_registry` sends. There is nothing else we need do other than define the method.

There are also alternative, more explicit, methods of registering event handlers.

```python
display = wayland.wl_display()
```

Here we create an instance of `wl_display`, the special Wayland object number 1. In `python-wayland` this object is extended with essential functionality such as event dispatching, in a similar way as `libwayland-client` the standard C Wayland library does. See it's [documentation](wayland/wl_display/) for full details of the available functions.

Still up to this point we have not attempted to make any connection to the local Wayland compositor. Everything up to here would work even on a system which was not running Wayland.

```python
registry = display.get_registry()
```

The standard Wayland `wl_display.get_registry()` method. It creates and returns an instance of `wl_registry`. Because we registered our own class for `wl_registry` this method will actually return an instance of our own class. As our class inherited from the standard `wl_registry` class, it's behaviour stays the same as the normal Wayland behaviour and as soon as it's created, `wl_registry` starts generating `global` events.

As we had not explicitly connected to the Wayland compositor, and because auto connection is enabled by default, calling `get_registry()` caused `python-wayland` to connect to the Wayland socket and start request and event processing. An exception would be raised here if no Wayland compositor was available for us to connect to.

```python
while True:
    display.dispatch_timeout(0.2)
```

Our very basic main event loop. We call the display objects `dispatch_timeout` method, a blocking call to dispatch Wayland events to registered event handlers. If there are no events pending it will block until either events arrive or the timeout given in seconds elapses.

As each `global` event is raised by the compositor through the `wl_registry` object our `on_global` event handler will be called and we will see the names of the global interfaces printed:

```text
wl_seat
wl_data_device_manager
wl_compositor
wl_subcompositor
wl_shm
...etc...
```

