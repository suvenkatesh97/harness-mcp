from __future__ import annotations

from pathlib import Path
from typing import Any

from harness_mcp.catalog import Catalog, McpServer, load_catalog
from harness_mcp.catalog_data.builtin import BUILTIN_SERVERS
from harness_mcp.harnesses.base import AbstractHarness, McpConfigEntry
from harness_mcp.harnesses.opencode import OpenCodeHarness

HARNESS_REGISTRY: dict[str, type[AbstractHarness]] = {
    "opencode": OpenCodeHarness,
}


def get_harness(name: str | None = None, cwd: Path | None = None) -> AbstractHarness | None:
    if cwd is None:
        cwd = Path.cwd()

    if name:
        cls = HARNESS_REGISTRY.get(name.lower())
        if cls:
            return cls()
        return None

    for cls in HARNESS_REGISTRY.values():
        harness = cls()
        if harness.detect(cwd):
            return harness

    return None


def get_catalog() -> Catalog:
    return load_catalog(BUILTIN_SERVERS)


def add_servers(
    harness: AbstractHarness,
    catalog: Catalog,
    server_ids: list[str],
    scope: str = "project",
    cwd: Path | None = None,
    env_overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    if cwd is None:
        cwd = Path.cwd()

    paths = harness.resolve_config_paths(cwd, scope)
    config_path = None
    config: dict[str, Any] = {}
    for p in paths:
        if p.exists():
            config_path = p
            config = harness.read_config(p)
            break

    if config_path is None:
        config_path = paths[0] if paths else (cwd / "opencode.json")
        config = {"$schema": "https://opencode.ai/config.json"}

    existing = harness.get_mcp_entries(config)
    added = []
    skipped = []

    for sid in server_ids:
        server = catalog.get(sid)
        if server is None:
            skipped.append(sid)
            continue

        if sid in existing:
            skipped.append(sid)
            continue

        existing[sid] = harness.entry_from_catalog(server, env_overrides)
        added.append(sid)

    config = harness.set_mcp_entries(config, existing)
    harness.write_config(config_path, config)

    return {"added": added, "skipped": skipped, "path": str(config_path)}


def remove_servers(
    harness: AbstractHarness,
    server_ids: list[str],
    scope: str = "project",
    cwd: Path | None = None,
) -> dict[str, Any]:
    if cwd is None:
        cwd = Path.cwd()

    paths = harness.resolve_config_paths(cwd, scope)
    config_path = None
    config: dict[str, Any] = {}
    for p in paths:
        if p.exists():
            config_path = p
            config = harness.read_config(p)
            break

    if config_path is None:
        return {"removed": [], "not_found": list(server_ids), "path": None}

    existing = harness.get_mcp_entries(config)
    removed = []
    not_found = []

    for sid in server_ids:
        if sid in existing:
            del existing[sid]
            removed.append(sid)
        else:
            not_found.append(sid)

    config = harness.set_mcp_entries(config, existing)
    harness.write_config(config_path, config)

    return {"removed": removed, "not_found": not_found, "path": str(config_path)}


def get_status(
    harness: AbstractHarness,
    scope: str = "project",
    cwd: Path | None = None,
) -> dict[str, Any]:
    if cwd is None:
        cwd = Path.cwd()

    paths = harness.resolve_config_paths(cwd, scope)
    entries: dict[str, McpConfigEntry] = {}

    for p in reversed(paths):
        if p.exists():
            config = harness.read_config(p)
            entries.update(harness.get_mcp_entries(config))

    return {
        "servers": {name: {"type": e.type, "enabled": e.enabled} for name, e in entries.items()},
        "count": len(entries),
    }


def search_catalog(
    catalog: Catalog,
    query: str,
    tag: str | None = None,
) -> list[McpServer]:
    if tag:
        return catalog.by_tag(tag)
    return catalog.search(query)
