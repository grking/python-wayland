# Copyright (c) 2024-2025 Graham R King
# Licensed under the MIT License. See LICENSE file for details.

PROTOCOL_HEADER_SIZE = 8

MAX_EVENT_RESOLUTION = 1000
"""Things that poll for events do so this many times per second"""

PROTOCOL_DEBUG_SOCKET_NAME = "python-wayland-debug"
"""The default abstract file socket name on which the library debug server listens.

If this socket is already in use, the PID of the current process will be added to the
socket name: {PROTOCOL_DEBUG_SOCKET_NAME}-{PID}

To override all of that and set your own socket name, set the environmental variable
PYTHON_WAYLAND_DEBUG_SOCKET to be the name of the socket
"""

MAX_PROTOCOL_PACKET_DUMP_SIZE = 256
"""The maximum number of bytes to include in low-level protocol data
debugging messages.

Only impacts debugging message output not general functionality.
"""
