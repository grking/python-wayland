# Copyright (c) 2024-2025 Graham R King
# Licensed under the MIT License. See LICENSE file for details.

from __future__ import annotations

import argparse
import asyncio
import sys
from typing import TYPE_CHECKING, ClassVar

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header

from wayland.client.debug.debugclient import DebugClient
from wayland.client.debug.messagelog import MessageLog as BaseMessageLog
from wayland.client.debug.summarypanel import SummaryPanel

if TYPE_CHECKING:
    from textual.timer import Timer


class MessageLog(BaseMessageLog):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app_ref = None

    def on_key(self, event):
        if (
            self.app_ref
            and hasattr(self.app_ref, "handle_navigation_key")
            and self.app_ref.handle_navigation_key(event, self)
        ):
            return
        if hasattr(super(), "on_key"):
            return super().on_key(event)
        return None


class DebuggerClient(App):
    REFRESH_INTERVAL = 0.05
    ICON_STREAM = "⇉"
    ICON_PAUSE = "⏸"
    ICON_APP = "🔍"
    ICON_RUN = "▶"
    ICON_MANUAL = "⌨"

    CSS: ClassVar[str] = """
    SummaryPanel {
        height: 3;
        border: none;
        background: $surface;
        margin: 0;
        padding: 1;
    }

    MessageLog {
        border: solid $primary;
        margin: 1;
        height: 1fr; /* Allow MessageLog to take remaining vertical space */
    }

    """

    BINDINGS: ClassVar = [
        ("q", "quit", "Quit"),
        ("r", "reconnect", "Reconnect"),
        ("c", "clear", "Clear log"),
        ("s", "toggle_stream", "Stream"),
    ]

    def __init__(self, socket_name: str = "python-wayland-debug", **kwargs):
        super().__init__(**kwargs)
        self.socket_name = socket_name
        self.client: DebugClient | None = None
        self.connected = False
        self._stream = True
        self.want_start_row = 0
        self.want_end_row = 0
        self.viewing_start_row = 0
        self.viewing_end_row = 0
        self.last_requested_range: tuple[int, int] | None = (0, 0)
        self.update_timer: Timer | None = None
        self._background_tasks: set[asyncio.Task] = set()
        self.title = "Wayland Protocol Debugger"
        self.sub_title = self.get_status()

    @property
    def stream(self):
        return self._stream

    @stream.setter
    def stream(self, value):
        self._stream = value
        message_log = self.query_one("#messages", MessageLog)
        message_log.show_cursor = not self._stream
        self.sub_title = self.get_status()

    def compose(self) -> ComposeResult:
        yield Header(id="header", icon=self.ICON_APP)
        yield SummaryPanel(id="summary")
        yield MessageLog(id="messages")
        yield Footer()

    def on_mount(self) -> None:
        message_log = self.query_one("#messages", MessageLog)
        message_log.app_ref = self
        self.connect()

    def connect(self):
        task = asyncio.create_task(self._async_connect())
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    def disconnect(self):
        task = asyncio.create_task(self._async_disconnect())
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def _async_connect(self) -> None:
        try:
            if self.client is None:
                self.client = await DebugClient.create(self.socket_name)
            else:
                await self.client.connect()
            self.connected = True
            self.last_requested_range = None
            self.start_updates()
        except (ConnectionError, OSError):
            self.connected = False

    async def _async_disconnect(self) -> None:
        try:
            if self.client is not None:
                await self.client.disconnect()
            self.connected = False
            self.stop_updates()
        except (ConnectionError, OSError):
            self.connected = False
            self.stop_updates()

    def start_updates(self) -> None:
        if self.update_timer:
            self.update_timer.stop()
        self.update_timer = self.set_interval(self.REFRESH_INTERVAL, self.update_data)

    def stop_updates(self) -> None:
        if self.update_timer:
            self.update_timer.stop()
            self.update_timer = None

    def update_data(self) -> None:
        task = asyncio.create_task(self._async_update_data())
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    def get_available_rows(self):
        message_log = self.query_one("#messages", MessageLog)
        content_height = message_log.scrollable_content_region.height
        return max(1, content_height - 1)

    async def update_summary_panel(self):
        await self.client.get_summary()
        summary_data = self.client.summary
        summary_panel = self.query_one("#summary", SummaryPanel)
        summary_panel.summary_data = summary_data

    async def update_debug_data(self):
        if self._has_range_changed():
            already_requested = self.last_requested_range == (
                self.want_start_row,
                self.want_end_row,
            )

            messages = await self.client.get_messages_by_range(
                self.want_start_row, self.want_end_row, check_only=already_requested
            )
            if not already_requested:
                self.last_requested_range = (self.want_start_row, self.want_end_row)
                return

            if messages:
                message_log = self.query_one("#messages", MessageLog)
                self.viewing_start_row = self.want_start_row
                self.viewing_end_row = self.want_end_row
                # Preserve the row selection
                selection = message_log.selected_index
                # Update the actual data table rows
                message_log.update_messages(messages)
                if selection:
                    message_log.cursor_coordinate = (selection, 0)

    async def _async_update_data(self) -> None:
        try:
            await self.update_summary_panel()

            if self.client is None:
                return

            available_rows = self.get_available_rows()
            # Initial startup case, no data, don't know what we want
            if (
                not self.want_end_row or not self.want_start_row
            ) and not self.client.has_data():
                await self.client.get_last_messages(available_rows)
                return

            # Startup case where we don't know what we want but
            # there is data available
            if (
                not self.want_end_row or not self.want_start_row
            ) and self.client.has_data():
                if not self.stream:
                    self.want_start_row = self.client.range_start
                    self.want_end_row = self.client.range_start + available_rows - 1
                else:
                    # Stream mode views the most recent messages
                    self.want_start_row = self.client.range_end - available_rows + 1
                    self.want_end_row = self.client.range_end

            # Case where window size has changed
            if (self.viewing_end_row - self.viewing_start_row) + 1 != available_rows:
                self.want_end_row = self.want_start_row + available_rows - 1

            await self.update_debug_data()

            if self.stream:
                self.want_end_row = 0
                self.want_start_row = 0
                # Only request more data if there is some
                if self.viewing_end_row != self.client.summary.get("last_key"):
                    await self.client.get_last_messages(available_rows)

        except (ConnectionError, OSError):
            self.disconnect()

    def action_reconnect(self) -> None:
        self.connect()

    def get_status(self):
        return f"Streaming {self.ICON_STREAM}" if self.stream else ""

    def action_toggle_stream(self) -> None:
        """Toggle the stream state."""
        self.stream = not self.stream
        self.sub_title = self.get_status()

    def action_clear(self) -> None:
        message_log = self.query_one("#messages", MessageLog)
        message_log.clear()

    def handle_navigation_key(self, event, message_log) -> bool:
        """Handle navigation keys at the MessageLog level. Returns True if handled."""

        # Disable stream mode automatically
        self.stream = False

        delta_map = {
            "ctrl+home": -sys.maxsize,
            "ctrl+end": sys.maxsize,
            "up": -1,
            "down": 1,
            "pageup": -self.get_available_rows(),
            "pagedown": self.get_available_rows(),
        }

        if event.key in delta_map:
            event.prevent_default()
            # up and down arrow only fetch data at the top/bottom extremes
            if event.key == "up" and not message_log.is_at_first_row():
                return False
            if event.key == "down" and not message_log.is_at_last_row():
                return False
            if self.scroll_viewport(delta_map[event.key]):
                return True

        return False

    def scroll_viewport(self, delta):
        # Request a new range of rows to view relative to the current ones
        start_row = self.want_start_row + delta
        end_row = self.want_end_row + delta

        # Moving back?
        if delta < 0:
            # Start can't be lower than the lowest msg key
            first_key = self.client.summary.get("first_key", 1)
            if start_row < first_key:
                adjustment = first_key - start_row
                delta = delta + adjustment
        elif delta > 0:
            # End row can't be higher than the last msg key
            last_key = self.client.summary.get("last_key", 1)
            if end_row > last_key:
                adjustment = last_key - end_row
                delta = delta + adjustment

        # Do actual change
        start_row = self.want_start_row + delta
        end_row = self.want_end_row + delta
        if start_row != self.want_start_row or end_row != self.want_end_row:
            self.want_start_row = start_row
            self.want_end_row = end_row
            return True
        return False

    def _has_range_changed(self) -> bool:
        if not self.client or not self.client.messages:
            return False

        if (
            self.want_end_row != self.viewing_end_row
            or self.want_start_row != self.viewing_start_row
        ):
            return True
        return False

    def on_unmount(self) -> None:
        self.stop_updates()
        if self.client:
            task = asyncio.create_task(self.client.stop())
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

        for task in self._background_tasks:
            task.cancel()


def main():
    parser = argparse.ArgumentParser(
        description="Python Wayland debug client (Textual UI)",
        prog="python -m wayland.client.debug.app",
    )
    parser.add_argument(
        "socket_name",
        nargs="?",
        default="python-wayland-debug",
        help="Name of the socket to connect to (default: python-wayland-debug)",
    )

    args = parser.parse_args()
    app = DebuggerClient(socket_name=args.socket_name)
    app.run()
