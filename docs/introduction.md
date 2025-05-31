# Introduction
`python-wayland` is a pure python implementation of the Wayland protocol and focuses on enabling clients to connect to compositors and interact with the full range of wayland interfaces.

This library seeks to expose the wayland protocol interfaces as they are, rather than convert them into some more Pythonic form. This means general wayland API documentation, such as [wayland.app](https://wayland.app), is directly useful and relevant to the use of this library.

The wayland protocol is designed for clients and compositors to talk to one another, it doesn't seek to be a high-level developer friendly API for GUI creation. See Drew DeVault's [wayland book](https://wayland-book.com/) for a great introduction.

The typical client library used for connecting to wayland compositors is the C library, `libwayland-client`. This C library is wrapped by many other languges to expose the wayland protocol API. `python-wayland` replaces `libwayland-client` and provides a pure python implementation of the protocols.

The wayland protocol API in `python-wayland` is constructed dynamically from the wayland protocol definitions, as per the design intent of the wayland protocol. There are no hardcoded wayland methods, for example there is no method for `wl_registry.bind()` within the `python-wayland` source. These methods are constructed at runtime and injected into the python namespace.

## Wayland Protocols in Python

Although the intent is to expose the wayland protocol interfaces as they are, there are two areas where this is either not possible or not desirable:

1. Naming clashes with Python built-in keywords.
2. Representing wayland references as python object instances.

### Python Naming Conflicts

Naming conflicts are rare, see [Wayland/Python Naming Conflicts](naming.md) for details.

### Wayland and Python Objects

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
