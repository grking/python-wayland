# Copyright (c) 2024-2025 Graham R King
# Licensed under the MIT License. See LICENSE file for details.

from __future__ import annotations

import asyncio
import contextlib


class DebugSocket:
    def __init__(self, socket_path: str = "python-wayland-debug"):
        self.socket_path = socket_path
        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None
        self.buffer = ""
        self._running = False

    async def connect(self):
        """Connect to the abstract Unix domain socket."""
        # For abstract sockets, prepend null byte
        abstract_path = f"\0{self.socket_path}"

        try:
            self.reader, self.writer = await asyncio.open_unix_connection(abstract_path)
        except Exception as e:
            msg = f"Failed to connect to socket: {e}"
            raise ConnectionError(msg) from e

    async def disconnect(self):
        """Close the socket connection."""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            self.reader = None
            self.writer = None

    async def send_text(self, data: str):
        """Send a data packet to the socket. Does not wait for response."""
        if not self.writer:
            return

        # Ensure data ends with newline
        if not data.endswith("\n"):
            data += "\n"

        self.writer.write(data.encode("utf-8"))
        await self.writer.drain()

    def process_packet(self, line: str):  # noqa: ARG002
        """Stub function to process received packets.
        Override this in subclasses."""
        msg = "Not implemented"
        raise NotImplementedError(msg)

    async def _read_loop(self):
        """Continuously read from the socket and process complete lines."""
        self._running = True

        try:
            while self._running and self.reader:
                # Read available data
                data = await self.reader.read(1024)
                if not data:
                    break

                # Add to buffer
                self.buffer += data.decode("utf-8", errors="replace")

                # Process complete lines
                while "\n" in self.buffer:
                    line, self.buffer = self.buffer.split("\n", 1)
                    if line:  # Skip empty lines
                        self.process_packet(line)

        except (OSError, UnicodeDecodeError, ConnectionError) as e:
            from wayland.log import log

            log.warning(f"Debug socket error: {e}")
        finally:
            self._running = False

    async def start(self):
        """Start watching for incoming data."""
        if not self.reader:
            await self.connect()

        # Start the read loop as a background task
        self.read_task = asyncio.create_task(self._read_loop())

    async def stop(self):
        """Stop watching for data and disconnect."""
        self._running = False
        if hasattr(self, "read_task"):
            self.read_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.read_task

        await self.disconnect()
