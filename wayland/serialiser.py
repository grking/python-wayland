# Copyright (c) 2024-2025 Graham R King
# Licensed under the MIT License. See LICENSE file for details.
from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from enum import Enum

from wayland.constants import MAX_PROTOCOL_PACKET_DUMP_SIZE


class MessageType(Enum):
    REQUEST = "req"
    EVENT = "evt"


class MessageEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, bytes):
            return base64.b64encode(obj).decode("utf-8")
        if isinstance(obj, Message):
            # Manually create dict to avoid deep copy issues
            return {
                "timestamp": obj.timestamp,
                "msgtype": obj.msgtype,
                "signature": obj.signature,
                "interface": obj.interface,
                "method_name": obj.method_name,
                "object_id": obj.object_id,
                "args": self._serialize_args(obj.args),
                "opcode": obj.opcode,
                "packet": obj.packet[:MAX_PROTOCOL_PACKET_DUMP_SIZE],
                "key": obj.key,
            }
        return super().default(obj)

    def _serialize_args(self, args):
        """Serialize args dict, handling non-serializable objects"""
        result = {}
        for key, value in args.items():
            obj_type = str(type(value))

            if isinstance(value, Enum):
                obj_value = str(value)
            elif isinstance(value, list):
                obj_value = ",".join([str(x) for x in value])
            elif type(value).__module__ != "builtins":
                obj_value = f"{value.__class__.__name__}@{value.object_id}"
            else:
                obj_value = value

            result[key] = {"type": obj_type, "value": obj_value}
        return result


@dataclass(frozen=True)
class Message:
    timestamp: float
    msgtype: MessageType
    signature: str
    interface: str
    method_name: str
    object_id: int
    args: dict
    opcode: int
    packet: bytes
    key: int

    @classmethod
    def create(
        cls,
        timestamp: float | None,
        msgtype: MessageType,
        signature: str,
        interface: str,
        method_name: str,
        object_id: int,
        args: dict,
        opcode: int,
        packet: bytes,
        key: int,
    ) -> Message:
        if isinstance(msgtype, str):
            msgtype = MessageType(msgtype)

        if timestamp is None:
            timestamp = time.time()

        return cls(
            timestamp,
            msgtype,
            signature,
            interface,
            method_name,
            object_id,
            args,
            opcode,
            packet,
            key,
        )
