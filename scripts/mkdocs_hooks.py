# Generate a JSON schema of the Python handler configuration.

import json
from dataclasses import dataclass, fields
from os.path import join
from typing import Any

from mkdocs.config.defaults import MkDocsConfig
from mkdocs.plugins import get_plugin_logger

from mkdocstrings_handlers.python import PythonInputConfig, PythonInputOptions

# TODO: Update when Pydantic supports Python 3.14 (sources and duties as well).
try:
    from pydantic import TypeAdapter
except ImportError:
    TypeAdapter = None  # type: ignore[assignment,misc]


_logger = get_plugin_logger(__name__)


def on_config(config: MkDocsConfig) -> MkDocsConfig | None:
    config.plugins["autorefs"].record_backlinks = True
    return config
