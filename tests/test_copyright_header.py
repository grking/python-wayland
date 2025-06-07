from __future__ import annotations

import os
import unittest
from pathlib import Path
from typing import ClassVar


class TestCopyrightHeader(unittest.TestCase):
    """Tests for copyright header presence in all Python files."""

    EXPECTED_HEADER: ClassVar[list[str]] = [
        "# Copyright (c) 2024-2025 Graham R King",
        "# Licensed under the MIT License. See LICENSE file for details.",
    ]

    def test_all_python_files_have_copyright_header(self):
        """Tests that all Python files in wayland/ directory have the required copyright header."""
        wayland_dir = Path("wayland")

        python_files = [
            Path(root) / file
            for root, _dirs, files in os.walk(wayland_dir)
            for file in files
            if file.endswith(".py")
        ]

        assert len(python_files) > 0, "No Python files found in wayland directory"

        missing_header_files = []

        for py_file in python_files:
            with open(py_file, encoding="utf-8") as f:
                lines = f.readlines()

            if len(lines) < 2:
                missing_header_files.append(str(py_file))
                continue

            # Handle files that start with shebang
            start_idx = 0
            if lines[0].startswith("#!"):
                start_idx = 1
                if len(lines) < 3:
                    missing_header_files.append(str(py_file))
                    continue

            first_header_line = lines[start_idx].rstrip()
            second_header_line = lines[start_idx + 1].rstrip()

            if (
                first_header_line != self.EXPECTED_HEADER[0]
                or second_header_line != self.EXPECTED_HEADER[1]
            ):
                missing_header_files.append(str(py_file))

        if missing_header_files:
            self.fail(
                f"The following files are missing the required copyright header:\n"
                f"{chr(10).join(missing_header_files)}\n\n"
                f"Expected header:\n{chr(10).join(self.EXPECTED_HEADER)}"
            )


if __name__ == "__main__":
    unittest.main()
