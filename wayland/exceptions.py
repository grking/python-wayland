# Copyright (c) 2024-2025 Graham R King
# Licensed under the MIT License. See LICENSE file for details.


class WaylandError(Exception):
    """Base exception for all exceptions."""


class WaylandNotConnectedError(WaylandError):
    """Raised when not connected."""


class WaylandConnectionError(WaylandError):
    """Raised if the Wayland socket can not be connected."""
