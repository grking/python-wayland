# Copyright (c) 2024-2025 Graham R King
# Licensed under the MIT License. See LICENSE file for details.

from __future__ import annotations

from typing import Any

from textual.reactive import reactive
from textual.widgets import Static


class SummaryPanel(Static):
    summary_data: reactive[dict[str, Any]] = reactive({})

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def watch_summary_data(self, summary_data: dict[str, Any]) -> None:
        if not summary_data:
            return

        if "error" in summary_data:
            content = f"[red]Error: {summary_data['error']}[/red]"
        elif "Status" in summary_data:
            status_msg = summary_data.get("Status", "No debug messages received")
            content = f"[yellow]Status: {status_msg}[/yellow]"
        elif (
            "total_count" in summary_data
            or "event_count" in summary_data
            or "request_count" in summary_data
        ):
            total_messages = summary_data.get("total_count", "0")
            rate = summary_data.get("msg_rate", "N/A")
            last_message = int(summary_data.get("last_msg", 0))
            first_key = summary_data.get("first_key", "")
            last_key = summary_data.get("last_key", "")

            recent_threshold = 2
            if last_message < recent_threshold:
                listen = "[green](receiving)[/green]"
            else:
                listen = f"[green](listening {last_message}s)[/green]"

            content = (
                f"[green]{total_messages}[/green] "
                f"Messages [gray](keys {first_key}-{last_key}, {rate})[/gray] {listen}\n"
            )
        else:
            content = "[yellow]Received summary data, but not in the expected format.[/yellow]"
            content += f"\n[dim]Raw data: {summary_data!r}[/dim]"

        self.update(f"{content}")
