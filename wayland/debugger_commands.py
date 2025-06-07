# Copyright (c) 2024-2025 Graham R King
# Licensed under the MIT License. See LICENSE file for details.
from __future__ import annotations

import shlex
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from wayland.log import log

if TYPE_CHECKING:
    import socket

    from wayland.debugger import Debugger


class DebuggerCommandHandler:
    """Handles debugger client commands."""

    def __init__(self, debugger: Debugger):
        self.debugger = debugger
        self._commands = {
            "help": self._cmd_help,
            "summary": self._cmd_summary,
            "stream": self._cmd_stream,
            "get": self._cmd_get,
            "quit": self._cmd_quit,
        }

    def handle_command(self, client_sock: socket.socket, command_line: str) -> bool:
        """Handle a command."""
        command_line = command_line.strip()
        if not command_line:
            return True

        try:
            parts = shlex.split(command_line)
        except ValueError as e:
            self.debugger.send_text(client_sock, f"Error parsing command: {e}")
            return True

        if not parts:
            return True

        command = parts[0]
        args = parts[1:]

        handler = self._commands.get(command)
        if handler:
            return handler(client_sock, args)

        self.debugger.send_text(client_sock, f"Unknown command: {command}")
        self.debugger.send_text(client_sock, "Type 'help' for available commands.")
        return True

    def _cmd_help(self, client_sock: socket.socket, args: list[str]) -> bool:
        """Show help for commands."""
        if args:
            command = args[0]
            if command == "summary":
                help_text = (
                    "summary - Get a summary of recorded messages\n"
                    "\n"
                    "Shows statistics about the recorded Wayland protocol messages including:\n"
                    "- Total message count\n"
                    "- Event and request counts\n"
                    "- Message rate\n"
                    "- Time since last message\n"
                )
            elif command == "stream":
                help_text = (
                    "stream - Start receiving the message stream\n"
                    "\n"
                    "Begins streaming live Wayland protocol messages to this client.\n"
                    "Messages will be sent as they occur until the connection is closed.\n"
                )
            elif command == "get":
                help_text = (
                    "get - Retrieve messages\n"
                    "\n"
                    "Subcommands:\n"
                    "  get last N        - Get the last N recorded messages\n"
                    "  get range A,B     - Get messages where key >= A and key <= B\n"
                    "  get msg N         - Get the message with key N\n"
                    "\n"
                    "Examples:\n"
                    "  get last 10       - Get the last 10 messages\n"
                    "  get last 100      - Get the last 100 messages\n"
                    "  get range 5,15    - Get messages with keys from 5 to 15\n"
                    "  get range 100,200 - Get messages with keys from 100 to 200\n"
                    "  get msg 42        - Get the message with key 42\n"
                )
            elif command == "quit":
                help_text = (
                    "quit - Disconnect from the debugger\n"
                    "\n"
                    "Closes the connection to the debugger.\n"
                )
            else:
                help_text = f"No help available for '{command}'\n"
        else:
            help_text = (
                "Available commands:\n"
                "  help [command]    - Show help (optionally for a specific command)\n"
                "  summary           - Get a summary of recorded messages\n"
                "  stream            - Start receiving the message stream\n"
                "  get last N        - Get the last N messages\n"
                "  get range A,B     - Get messages where key >= A and key <= B\n"
                "  get msg N         - Get the message with key N\n"
                "  quit              - Disconnect from the debugger\n"
                "\nType 'help <command>' for more information on a specific command.\n"
            )

        self.debugger.send_text(client_sock, help_text)
        log.info(f"Sent help message to client for: {args[0] if args else 'general'}")
        return True

    def _cmd_summary(self, client_sock: socket.socket, _args: list[str]) -> bool:
        """Get a summary of recorded messages."""
        self._handle_summary(client_sock)
        return True

    def _cmd_stream(self, client_sock: socket.socket, _args: list[str]) -> bool:
        """Start receiving the message stream."""
        self._handle_stream(client_sock)
        return True

    def _cmd_get(self, client_sock: socket.socket, args: list[str]) -> bool:
        """Retrieve messages."""
        if not args:
            self.debugger.send_text(
                client_sock, "Error: get command requires arguments"
            )
            self.debugger.send_text(client_sock, "Usage: get last N | get range A,B")
            return True

        subcommand = args[0]
        if subcommand == "last":
            return self._handle_get_last_command(client_sock, args)
        if subcommand == "range":
            return self._handle_get_range_command(client_sock, args)
        if subcommand == "msg":
            return self._handle_get_msg_command(client_sock, args)

        self.debugger.send_text(
            client_sock, f"Error: unknown get subcommand '{subcommand}'"
        )
        self.debugger.send_text(
            client_sock, "Usage: get last N | get range A,B | get msg N"
        )
        return True

    def _handle_get_last_command(
        self, client_sock: socket.socket, args: list[str]
    ) -> bool:
        """Handle 'get last N' command."""
        expected_args = 2
        if len(args) != expected_args:
            self.debugger.send_text(client_sock, "Error: 'get last' requires a count")
            self.debugger.send_text(client_sock, "Usage: get last N")
            return True
        try:
            count = int(args[1])
        except ValueError:
            self.debugger.send_text(client_sock, "Error: count must be an integer")
            return True
        else:
            self._handle_get_last(client_sock, count)
            return True

    def _handle_get_range_command(
        self, client_sock: socket.socket, args: list[str]
    ) -> bool:
        """Handle 'get range A,B' command."""
        expected_args = 2
        if len(args) != expected_args:
            self.debugger.send_text(
                client_sock, "Error: 'get range' requires a range specification"
            )
            self.debugger.send_text(client_sock, "Usage: get range A,B")
            return True

        def _raise_range_format_error():
            error_msg = "Range must be in format A,B"
            raise ValueError(error_msg)

        try:
            range_parts = args[1].split(",")
            expected_range_parts = 2
            if len(range_parts) != expected_range_parts:
                _raise_range_format_error()
            start_key = int(range_parts[0])
            end_key = int(range_parts[1])
        except ValueError:
            error_msg = "Error: range must be in format A,B where A and B are integers"
            self.debugger.send_text(client_sock, error_msg)
            return True
        else:
            self._handle_get_range(client_sock, start_key, end_key)
            return True

    def _handle_get_msg_command(
        self, client_sock: socket.socket, args: list[str]
    ) -> bool:
        """Handle 'get msg N' command."""
        expected_args = 2
        if len(args) != expected_args:
            self.debugger.send_text(
                client_sock, "Error: 'get msg' requires a message key"
            )
            self.debugger.send_text(client_sock, "Usage: get msg N")
            return True
        try:
            msg_key = int(args[1])
        except ValueError:
            self.debugger.send_text(
                client_sock, "Error: message key must be an integer"
            )
            return True
        else:
            self._handle_get_msg(client_sock, msg_key)
            return True

    def _cmd_quit(self, client_sock: socket.socket, _args: list[str]) -> bool:
        """Disconnect from the debugger."""
        self._handle_quit(client_sock)
        return False

    def _handle_summary(self, client_sock: socket.socket):
        if len(self.debugger) == 0:
            self.debugger.send_text(client_sock, "Status: No debug messages recorded\n")
            return

        total_messages = len(self.debugger)
        event_count = self.debugger.get_event_count()
        request_count = total_messages - event_count

        first_timestamp = self.debugger[0].timestamp
        last_timestamp = self.debugger[-1].timestamp
        duration = last_timestamp - first_timestamp if total_messages > 1 else 0.0

        rate_str = f"{total_messages / duration:.1f} msgs/s" if duration > 0 else "N/A"
        time_since_last = datetime.now(timezone.utc).timestamp() - last_timestamp

        summary = {
            "total_count": total_messages,
            "event_count": event_count,
            "request_count": request_count,
            "duration": f"{duration:.3f}s",
            "msg_rate": rate_str,
            "last_msg": int(time_since_last),
            "last_key": self.debugger[-1].key,
            "first_key": self.debugger[0].key,
        }

        self.debugger.send_data(client_sock, summary, "summary")

    def _handle_stream(self, client_sock: socket.socket) -> bool:
        if self.debugger.set_client_streaming(client_sock, streaming=True):
            log.info("Client issued 'start stream' command. Streaming started.")
        else:
            log.warning("Client not found in clients on 'start stream'.")
        return True

    def _handle_quit(self, client_sock: socket.socket) -> bool:
        self.debugger.send_text(client_sock, "Goodbye.\n")
        log.info("Client requested disconnect via 'quit' command.")
        return False

    def _handle_get_last(self, client_sock: socket.socket, count: int):
        if count <= 0:
            self.debugger.send_text(
                client_sock,
                "Error: Count must be a positive integer.\n",
            )
            log.warning(f"Client requested non-positive count for 'get last': {count}")
            return False

        messages_to_send = self.debugger[-count:]

        for msg in messages_to_send:
            self.debugger.send_data(client_sock, msg)
        return True

    def _handle_get_msg(self, client_sock: socket.socket, msg_key: int) -> bool:
        """Get a specific message by key."""
        for msg in self.debugger:
            if msg.key == msg_key:
                self.debugger.send_data(client_sock, msg)
                return True

        self.debugger.send_text(
            client_sock,
            f"No message found with key {msg_key}.\n",
        )
        return True

    def _handle_get_range(
        self, client_sock: socket.socket, start_key: int, end_key: int
    ):
        if start_key > end_key or not end_key:
            self.debugger.send_text(
                client_sock,
                "Error: Start key must be less than or equal to end key.\n",
            )
            log.warning(f"Client requested invalid range: {start_key} > {end_key}")
            return False

        messages_to_send = self.debugger.get_message_data_by_range(start_key, end_key)

        if not messages_to_send:
            self.debugger.send_text(
                client_sock,
                f"No messages found in range {start_key}-{end_key}.\n",
            )
            return True

        for msg in messages_to_send:
            self.debugger.send_data(client_sock, msg)
        return True
