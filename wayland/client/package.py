# Copyright (c) 2024-2025 Graham R King
# Licensed under the MIT License. See LICENSE file for details.

import subprocess
from os import path

from wayland.__about__ import __version__


def get_package_root() -> str:
    """Get the root directory of the package.

    Returns:
        Absolute path to the wayland package directory.
    """
    package_name = __package__.split(".")[0]
    package_module = __import__(package_name)
    return path.abspath(package_module.__path__[0])


def get_package_version() -> str:
    """Get the version of the python-wayland package.

    Note:
        Will include the git commit hash or tag if the package
        is being run from a git repository.

    Examples:
        Print the current library version

        >>> print(wayland.client.get_package_version())
        1.0.0

        Print the current library version from a local git repo

        >>> print(wayland.client.get_package_version())
        1.0.0+b347d2e-dirty

    Returns:
        The package version identifier.

    """
    version = __version__

    try:
        result = subprocess.run(
            ["git", "describe", "--dirty", "--alway"],  # noqa: S607
            capture_output=True,
            text=True,
            check=True,
            cwd=get_package_root(),
        )
        commit = result.stdout.strip()

        version += f"+{commit}"

    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        pass

    return version
