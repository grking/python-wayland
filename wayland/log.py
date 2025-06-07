# Copyright (c) 2024-2025 Graham R King
# Licensed under the MIT License. See LICENSE file for details.

from __future__ import annotations

import logging
import os
from typing import Any

# Custom log levels
CUSTOM_LEVELS = {"PROTOCOL": 7}

for name, level in CUSTOM_LEVELS.items():
    logging.addLevelName(level, name)


class WaylandLogger(logging.Logger):
    def __init__(self, name: str):
        super().__init__(name)
        self._enabled_flags: dict[str, bool] = {
            name.lower(): True for name in CUSTOM_LEVELS
        }

    def _log_if_enabled(self, level: int, msg: str, *args: Any, **kwargs: Any) -> None:
        level_name = logging.getLevelName(level).lower()
        if self.isEnabledFor(level) and self._enabled_flags.get(level_name, True):
            self.log(level, msg, *args, **kwargs)

    def protocol(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._log_if_enabled(CUSTOM_LEVELS["PROTOCOL"], msg, *args, **kwargs)

    def toggle_level(self, level_name: str, enable: bool) -> None:
        self._enabled_flags[level_name.lower()] = enable

    def enable(self, level: int = logging.INFO) -> None:
        self.setLevel(level)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        formatter = logging.Formatter("%(levelname)s - %(message)s")
        console_handler.setFormatter(formatter)
        self.addHandler(console_handler)


logging.setLoggerClass(WaylandLogger)
log = logging.getLogger("wayland")

if not log.hasHandlers() and os.getenv("WAYLAND_DEBUG") == "1":
    log.enable(CUSTOM_LEVELS["PROTOCOL"])
