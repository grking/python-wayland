# Copyright (c) 2024-2025 Graham R King
# Licensed under the MIT License. See LICENSE file for details.

import struct
from enum import Enum

WAYLAND_ALIGNMENT = 4
WAYLAND_WORD_SIZE = 4


def pad_data(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    data += b"\x00"
    padding = ((len(data) + WAYLAND_ALIGNMENT - 1) & ~(WAYLAND_ALIGNMENT - 1)) - len(
        data
    )
    data += b"\x00" * padding
    return data


def pack_argument(packet, arg_type, value):
    fds = []
    if arg_type in ("new_id", "uint"):
        if isinstance(value, Enum):
            packet += struct.pack("I", value.value)
        else:
            packet += struct.pack("I", value)
    elif arg_type == "object":
        packet += struct.pack("I", getattr(value, "object_id", 0))
    elif arg_type == "int":
        packet += struct.pack("i", value)
    elif arg_type == "enum":
        packet += struct.pack("I", value.value)
    elif arg_type == "string":
        encoded_value = value.encode("utf-8")
        length = len(encoded_value) + 1
        padded_data = pad_data(value)
        packet += struct.pack(f"I{len(padded_data)}s", length, padded_data)
    elif arg_type == "fixed":
        integer_part = int(value) << 8
        fractional_part = int((value - int(value)) * 256)
        packed_value = integer_part | (fractional_part & 0xFF)
        packet += struct.pack("I", packed_value)
    elif arg_type == "fd":
        fds.append(value)

    return packet, fds


def unpack_argument(packet, arg_type, get_fd, enum_type, int_to_enum_func):
    read = 0
    if enum_type is not None:
        (value,) = struct.unpack_from("I", packet)
        value = int_to_enum_func(enum_type, value)
        read = WAYLAND_WORD_SIZE
    elif arg_type in ("new_id", "uint", "object"):
        (value,) = struct.unpack_from("I", packet)
        read = WAYLAND_WORD_SIZE
    elif arg_type == "int":
        (value,) = struct.unpack_from("i", packet)
        read = WAYLAND_WORD_SIZE
    elif arg_type == "fd":
        value = get_fd()
    elif arg_type == "string":
        (length,) = struct.unpack_from("I", packet)
        padded_length = (length + WAYLAND_ALIGNMENT - 1) & ~(WAYLAND_ALIGNMENT - 1)
        (value,) = struct.unpack_from(
            f"{padded_length}s", packet, offset=WAYLAND_WORD_SIZE
        )
        value = value[: length - 1].decode("utf-8")
        read = WAYLAND_WORD_SIZE + padded_length
    elif arg_type == "array":
        (length,) = struct.unpack_from("I", packet)
        padded_length = (length + WAYLAND_ALIGNMENT - 1) & ~(WAYLAND_ALIGNMENT - 1)
        if length > 0:
            (array_data,) = struct.unpack_from(
                f"{padded_length}s", packet, offset=WAYLAND_WORD_SIZE
            )
            num_elements = length // WAYLAND_WORD_SIZE
            value = list(struct.unpack(f"{num_elements}I", array_data[:length]))
        else:
            value = []
        read = WAYLAND_WORD_SIZE + padded_length
    elif arg_type == "fixed":
        (value,) = struct.unpack_from("I", packet)
        read = WAYLAND_WORD_SIZE
        integer_part = value >> 8
        fractional_part = value & 0xFF
        value = integer_part + fractional_part / 256.0
    else:
        raise ValueError("Unknown type " + arg_type)

    return packet[read:], value
