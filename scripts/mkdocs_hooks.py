# Generate a JSON schema of the Python handler configuration.
from __future__ import annotations

from typing import TYPE_CHECKING

from mkdocs.plugins import get_plugin_logger

if TYPE_CHECKING:
    from mkdocs.config.defaults import MkDocsConfig

# TODO: Update when Pydantic supports Python 3.14 (sources and duties as well).
try:
    from pydantic import TypeAdapter
except ImportError:
    TypeAdapter = None  # type: ignore[assignment,misc]


_logger = get_plugin_logger(__name__)


def on_config(config: MkDocsConfig) -> MkDocsConfig | None:
    config.plugins["autorefs"].record_backlinks = True
    return config
