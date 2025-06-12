# Copyright (c) 2024-2025 Graham R King
# Licensed under the MIT License. See LICENSE file for details.


class WaylandObject:
    """A common ancestor for Wayland classes.

    This is the class from which all other `python-wayland` classes descend.
    Do not use this class directly.

    Its main purpose is to provide a single common ancestor to facilitate
    runtime checking of classes and instances to see if they are Wayland
    classes or instances.

    Examples:
        Check if `myvar` is an instance of any Wayland type:

        >>> isinstance(myvar, WaylandObject)

        Check if `myclass` is a Wayland class:

        >>> issubclass(myclass, WaylandObject)
    """
