# Copyright (c) 2024-2025 Graham R King
# Licensed under the MIT License. See LICENSE file for details.

from __future__ import annotations

import json
from typing import Any

from wayland.client.debug.debugsocket import DebugSocket
from wayland.serialiser import Message


class DebugClient(DebugSocket):
    def __init__(self, socket_path: str = "python-wayland-debug"):
        super().__init__(socket_path)

        # Initialize child class attributes
        self.range_start = 0
        self.range_end = 0
        self.messages: dict[int, Message] = {}
        self._summary: dict[str, Any] = {}

    @property
    def summary(self):
        return self._summary.copy()

    @classmethod
    async def create(cls, socket_path: str = "python-wayland-debug"):
        """Create instance and establish connection."""
        debugclient = cls(socket_path)
        await debugclient.start()
        return debugclient

    def process_packet(self, line: str):
        # Process received packets
        packet_handlers = {
            "DATA/summary:": self._parse_summary,
            "DATA/debug:": self._parse_debug_msg,
        }

        for prefix, handler in packet_handlers.items():
            if line.startswith(prefix):
                data = json.loads(line[len(prefix) :])
                return handler(data)

        return self.parse_text(line)

    def _parse_summary(self, summary_data):
        self._summary = summary_data

    def _parse_debug_msg(self, msg):
        if msg["key"] < self.range_start or not self.range_start:
            self.range_start = msg["key"]
        if msg["key"] > self.range_end or not self.range_end:
            self.range_end = msg["key"]
        message = Message.create(**msg)
        self.messages[message.key] = message

    def parse_text(self, line: str):
        pass

    def has_data(self):
        return len(self.messages) > 0

    def has_range(self, start_range, end_range):
        have = True
        for key in range(start_range, end_range + 1):
            if key not in self.messages:
                have = False
                break
        return have

    async def get_messages_by_range(
        self, start_key: int, end_key: int, *, check_only: bool = False
    ) -> list[Message] | None:
        # Do we have them available already?
        have = self.has_range(start_key, end_key)
        if have:
            return [self.messages[key] for key in range(start_key, end_key + 1)]

        # if not, request them from the remote, unless the caller was just checking
        if check_only:
            return None
        await self.send_text(f"get range {start_key},{end_key}")
        return None

    async def get_message_by_key(self, key: int):
        await self.send_text(f"get msg {key}")

    async def get_last_messages(self, num_messages: int):
        await self.send_text(f"get last {num_messages}")

    async def get_summary(self):
        await self.send_text("summary")
