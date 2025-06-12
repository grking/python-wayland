# API Documentation

All the Wayland interfaces are available in the [`wayland`](../wayland/index.md) namespace.

`wayland.client` provides additional library specific functionality that is not part of the Wayland protocol itself.

* [`wayland.client`][wayland.client]
* [`wayland.client.package`][wayland.client.package]

## Wayland Protocol Debugger

A stand alone terminal Wayland protocol debugger is included. This allows you to monitor all requests and events between your application and the Wayland compositor.

![Wayland debugger interface](../assets/images/wayland-debugger.png)

This is easy to use in your application. See the [documentation here](client.md#wayland.client.start_debug_server).
