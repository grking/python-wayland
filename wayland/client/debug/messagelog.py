# Copyright (c) 2024-2025 Graham R King
# Licensed under the MIT License. See LICENSE file for details.

from __future__ import annotations

import datetime

from textual.widgets import DataTable

from wayland.serialiser import MessageType


class MessageLog(DataTable):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.border_title = "Wayland Protocol Messages"
        self.add_columns("Time", "ID", "Type", "Object", "Method", "Arguments")
        self.cursor_type = "row"
        self.zebra_stripes = True
        self.selected_index = None
        self.selected_row_key = None
        self.show_cursor = False

    def on_data_table_row_highlighted(self, event):
        self.selected_index = event.cursor_row
        self.selected_row_key = event.row_key.value if event.row_key else None

    def update_messages(self, messages: list) -> None:
        self.clear()

        for msg in messages:
            timestamp = datetime.datetime.fromtimestamp(
                msg.timestamp, tz=datetime.timezone.utc
            )
            time_str = timestamp.strftime("%M:%S.%f")[:-3]

            if msg.msgtype == MessageType.REQUEST:
                type_str = "[bright_blue]req[/bright_blue]"
            else:  # MessageType.EVENT
                type_str = "[bright_magenta]evt[/bright_magenta]"

            obj_str = f"{msg.interface}[bright_black]@{msg.object_id}[/bright_black]"
            method_str = msg.method_name

            args_list = []
            for name, info in msg.args.items():
                if isinstance(info, dict) and "value" in info:
                    args_list.append(f"{name}=[green]{info['value']}[/green]")
                else:
                    args_list.append(f"{name}=[magenta]{info}[/magenta]")
            args_str = ", ".join(args_list)

            # wrapped_args = textwrap.fill(args_str, width=80, break_long_words=False)

            self.add_row(
                f"[bright_black]{time_str}[/bright_black]",
                f"[bright_black]{msg.key}[/bright_black]",
                type_str,
                f"[white]{obj_str}[/white]",
                f"[white]{method_str}[/white]",
                f"[white]{args_str}[/white]",
                key=msg.key,
            )

    def is_at_last_row(self) -> bool:
        return self.cursor_row == self.row_count - 1

    def is_at_first_row(self) -> bool:
        return self.cursor_row == 0
