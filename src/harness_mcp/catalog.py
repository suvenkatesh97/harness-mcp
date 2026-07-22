from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol

try:
    import yaml as _yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False


@dataclass
class EnvVarSpec:
    name: str
    description: str
    required: bool = False
    default: str | None = None


@dataclass
class McpServer:
    id: str
    name: str
    description: str
    homepage: str = ""
    type: Literal["local", "remote"] = "local"
    command: list[str] | None = None
    url: str | None = None
    env_vars: list[EnvVarSpec] = field(default_factory=list)
    headers: dict[str, str] | None = None
    enabled: bool = True
    tags: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.type == "local" and not self.command:
            raise ValueError(f"Local MCP server '{self.id}' requires a 'command'")
        if self.type == "remote" and not self.url:
            raise ValueError(f"Remote MCP server '{self.id}' requires a 'url'")

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "homepage": self.homepage,
            "type": self.type,
            "tags": self.tags,
            "enabled": self.enabled,
        }
        if self.command:
            d["command"] = self.command
        if self.url:
            d["url"] = self.url
        if self.env_vars:
            d["env_vars"] = [
                {
                    "name": e.name,
                    "description": e.description,
                    "required": e.required,
                    "default": e.default,
                }
                for e in self.env_vars
            ]
        if self.headers:
            d["headers"] = self.headers
        return d

    @classmethod
    def from_dict(cls, d: dict) -> McpServer:
        env_vars = [
            EnvVarSpec(
                name=e["name"],
                description=e.get("description", ""),
                required=e.get("required", False),
                default=e.get("default"),
            )
            for e in d.get("env_vars", [])
        ]
        return cls(
            id=d["id"],
            name=d["name"],
            description=d.get("description", ""),
            homepage=d.get("homepage", ""),
            type=d.get("type", "local"),
            command=d.get("command"),
            url=d.get("url"),
            env_vars=env_vars,
            headers=d.get("headers"),
            enabled=d.get("enabled", True),
            tags=d.get("tags", []),
        )


class CatalogSource(Protocol):
    def load(self) -> list[McpServer]: ...


class BuiltinCatalogSource:
    def __init__(self, entries: list[McpServer]):
        self._entries = entries

    def load(self) -> list[McpServer]:
        return self._entries


class ExternalFileCatalogSource:
    def __init__(self, path: Path):
        self._path = path

    def load(self) -> list[McpServer]:
        if not self._path.exists():
            return []
        with open(self._path) as f:
            content = f.read()
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            if not HAS_YAML:
                return []
            data = _yaml.safe_load(content)
        if not data or not isinstance(data, dict):
            return []
        entries = data.get("servers", [])
        if not isinstance(entries, list):
            return []
        return [McpServer.from_dict(e) for e in entries]


class Catalog:
    def __init__(self, builtin_entries: list[McpServer]):
        self._sources: list[CatalogSource] = [BuiltinCatalogSource(builtin_entries)]

    def add_external_path(self, path: Path):
        self._sources.append(ExternalFileCatalogSource(path))

    def add_external_dir(self, directory: Path):
        if not directory.exists():
            return
        for f in sorted(directory.iterdir()):
            if f.suffix in (".yaml", ".yml", ".json"):
                self.add_external_path(f)

    def all(self) -> dict[str, McpServer]:
        seen: dict[str, McpServer] = {}
        for source in self._sources:
            for server in source.load():
                seen[server.id] = server
        return seen

    def get(self, server_id: str) -> McpServer | None:
        return self.all().get(server_id)

    def search(self, query: str) -> list[McpServer]:
        q = query.lower()
        results = []
        for server in self.all().values():
            if (
                q in server.id.lower()
                or q in server.name.lower()
                or q in server.description.lower()
            ):
                results.append(server)
            elif any(q in tag.lower() for tag in server.tags):
                results.append(server)
        return results

    def by_tag(self, tag: str) -> list[McpServer]:
        tag_lower = tag.lower()
        return [s for s in self.all().values() if any(tag_lower in t.lower() for t in s.tags)]


def load_catalog(builtin_entries: list[McpServer]) -> Catalog:
    catalog = Catalog(builtin_entries)

    config_home = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    catalog.add_external_dir(Path(config_home) / "harness-mcp" / "catalog")

    cwd = Path.cwd()
    catalog.add_external_dir(cwd / ".harness-mcp" / "catalog")

    return catalog
