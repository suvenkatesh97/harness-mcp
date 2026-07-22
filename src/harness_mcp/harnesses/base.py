from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class McpConfigEntry:
    type: str
    command: list[str] | None = None
    url: str | None = None
    enabled: bool = True
    environment: dict[str, str] = field(default_factory=dict)
    headers: dict[str, str] | None = None
    cwd: str | None = None
    timeout: int | None = None


class AbstractHarness(ABC):
    name: str

    @abstractmethod
    def detect(self, cwd: Path) -> Path | None:
        """Find the config file path for this harness, or None if not found."""

    @abstractmethod
    def read_config(self, path: Path) -> dict[str, Any]:
        """Parse the config file into a dict."""

    @abstractmethod
    def write_config(self, path: Path, config: dict[str, Any]):
        """Write the config dict back to the config file."""

    @abstractmethod
    def get_mcp_entries(self, config: dict[str, Any]) -> dict[str, McpConfigEntry]:
        """Extract MCP server entries from the config dict."""

    @abstractmethod
    def set_mcp_entries(
        self, config: dict[str, Any], entries: dict[str, McpConfigEntry]
    ) -> dict[str, Any]:
        """Set MCP server entries in the config dict."""

    @abstractmethod
    def entry_from_catalog(self, catalog_entry) -> McpConfigEntry:
        """Convert a catalog McpServer into a harness-specific McpConfigEntry."""

    def resolve_config_paths(self, cwd: Path, scope: str) -> list[Path]:
        """Return the list of possible config file paths in priority order."""
        return []
