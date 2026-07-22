from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from harness_mcp.catalog import (
    EnvVarSpec,
    ExternalFileCatalogSource,
    McpServer,
    load_catalog,
)
from harness_mcp.catalog_data.builtin import BUILTIN_SERVERS
from harness_mcp.harnesses.opencode import OpenCodeHarness


class TestMcpServer:
    def test_create_local_server(self):
        s = McpServer(
            id="test",
            name="Test",
            description="A test server",
            type="local",
            command=["npx", "-y", "test-pkg"],
            env_vars=[EnvVarSpec(name="KEY", description="API key", required=True)],
            tags=["test"],
        )
        assert s.id == "test"
        assert s.type == "local"
        assert s.command == ["npx", "-y", "test-pkg"]

    def test_create_remote_server(self):
        s = McpServer(
            id="test-remote",
            name="Test Remote",
            description="A test remote",
            type="remote",
            url="https://example.com/mcp",
            tags=["test", "remote"],
        )
        assert s.type == "remote"
        assert s.url == "https://example.com/mcp"

    def test_local_requires_command(self):
        with pytest.raises(ValueError, match="requires a 'command'"):
            McpServer(id="bad", name="Bad", description="bad", type="local")

    def test_remote_requires_url(self):
        with pytest.raises(ValueError, match="requires a 'url'"):
            McpServer(id="bad", name="Bad", description="bad", type="remote")

    def test_to_dict_roundtrip(self):
        s = McpServer(
            id="test",
            name="Test",
            description="desc",
            type="local",
            command=["npx", "test"],
            env_vars=[EnvVarSpec(name="X", description="desc", required=True)],
            tags=["a", "b"],
        )
        d = s.to_dict()
        assert d["id"] == "test"
        assert d["command"] == ["npx", "test"]

        s2 = McpServer.from_dict(d)
        assert s2.id == s.id
        assert s2.command == s.command
        assert len(s2.env_vars) == 1
        assert s2.env_vars[0].name == "X"


class TestBuiltinCatalog:
    def test_all_entries_valid(self):
        for s in BUILTIN_SERVERS:
            assert s.id
            assert s.name
            if s.type == "local":
                assert s.command is not None
            elif s.type == "remote":
                assert s.url is not None

    def test_no_duplicate_ids(self):
        ids = [s.id for s in BUILTIN_SERVERS]
        assert len(ids) == len(set(ids))


class TestCatalog:
    def test_search(self):
        catalog = load_catalog(BUILTIN_SERVERS)
        results = catalog.search("github")
        assert len(results) >= 1
        assert any(s.id == "github" for s in results)

    def test_by_tag(self):
        catalog = load_catalog(BUILTIN_SERVERS)
        results = catalog.by_tag("search")
        assert len(results) >= 1

    def test_get(self):
        catalog = load_catalog(BUILTIN_SERVERS)
        s = catalog.get("github")
        assert s is not None
        assert s.id == "github"
        assert catalog.get("nonexistent") is None


class TestExternalCatalogSource:
    def test_load_yaml(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(
                """
servers:
  - id: custom-one
    name: Custom One
    description: A custom server
    type: local
    command:
      - npx
      - -y
      - custom-pkg
    tags:
      - custom
"""
            )
            path = Path(f.name)

        try:
            source = ExternalFileCatalogSource(path)
            entries = source.load()
            assert len(entries) == 1
            assert entries[0].id == "custom-one"
            assert entries[0].command == ["npx", "-y", "custom-pkg"]
        finally:
            path.unlink(missing_ok=True)

    def test_load_json(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(
                {
                    "servers": [
                        {
                            "id": "custom-json",
                            "name": "Custom JSON",
                            "description": "A JSON-defined server",
                            "type": "remote",
                            "url": "https://example.com/mcp",
                            "tags": ["custom"],
                        }
                    ]
                },
                f,
            )
            path = Path(f.name)

        try:
            source = ExternalFileCatalogSource(path)
            entries = source.load()
            assert len(entries) == 1
            assert entries[0].id == "custom-json"
        finally:
            path.unlink(missing_ok=True)


class TestOpenCodeHarness:
    def test_parse_jsonc_with_comments(self):
        harness = OpenCodeHarness()
        config = harness._parse_jsonc(
            """
{
    // This is a line comment
    "$schema": "https://opencode.ai/config.json",
    /* Block comment
       spanning multiple lines */
    "model": "test-model",
    "mcp": {
        "test-server": {
            "type": "local",
            "command": ["npx", "-y", "test-pkg"],
            "enabled": true
        }
    }
}
"""
        )
        assert config["$schema"] == "https://opencode.ai/config.json"
        assert config["model"] == "test-model"
        assert "mcp" in config

    def test_get_mcp_entries(self):
        harness = OpenCodeHarness()
        config = {
            "mcp": {
                "server-a": {
                    "type": "local",
                    "command": ["npx", "a"],
                    "enabled": True,
                },
                "server-b": {
                    "type": "remote",
                    "url": "https://example.com",
                    "enabled": False,
                },
            }
        }
        entries = harness.get_mcp_entries(config)
        assert len(entries) == 2
        assert entries["server-a"].type == "local"
        assert entries["server-b"].type == "remote"
        assert not entries["server-b"].enabled

    def test_get_mcp_entries_empty(self):
        harness = OpenCodeHarness()
        assert harness.get_mcp_entries({}) == {}

    def test_set_mcp_entries(self):
        harness = OpenCodeHarness()
        config = {}
        entries = {
            "new-server": harness.entry_from_catalog(
                McpServer(
                    id="new-server",
                    name="New",
                    description="desc",
                    type="local",
                    command=["npx", "-y", "new-pkg"],
                    env_vars=[EnvVarSpec(name="TOKEN", description="desc", required=True)],
                ),
                env_overrides={"TOKEN": "secret"},
            )
        }
        config = harness.set_mcp_entries(config, entries)
        assert "mcp" in config
        assert "new-server" in config["mcp"]
        assert config["mcp"]["new-server"]["command"] == ["npx", "-y", "new-pkg"]
        assert config["mcp"]["new-server"]["environment"]["TOKEN"] == "secret"

    def test_entry_from_catalog_local(self):
        harness = OpenCodeHarness()
        server = McpServer(
            id="test",
            name="Test",
            description="desc",
            type="local",
            command=["npx", "test"],
        )
        entry = harness.entry_from_catalog(server)
        assert entry.type == "local"
        assert entry.command == ["npx", "test"]

    def test_entry_from_catalog_remote(self):
        harness = OpenCodeHarness()
        server = McpServer(
            id="test",
            name="Test",
            description="desc",
            type="remote",
            url="https://example.com",
        )
        entry = harness.entry_from_catalog(server)
        assert entry.type == "remote"
        assert entry.url == "https://example.com"

    def test_env_var_to_placeholder(self):
        harness = OpenCodeHarness()
        assert harness.env_var_to_placeholder("MY_KEY") == "{env:MY_KEY}"

    def test_read_write_roundtrip(self, tmp_path: Path):
        harness = OpenCodeHarness()
        config = {
            "$schema": "https://opencode.ai/config.json",
            "model": "test",
            "mcp": {
                "test-srv": {
                    "type": "local",
                    "command": ["npx", "test"],
                    "enabled": True,
                }
            },
        }
        path = tmp_path / "opencode.json"
        harness.write_config(path, config)
        read = harness.read_config(path)
        assert read["model"] == "test"
        assert read["mcp"]["test-srv"]["command"] == ["npx", "test"]

    def test_strip_comments_preserves_strings(self):
        harness = OpenCodeHarness()
        text = """{
            "key": "value with // not a comment",
            "url": "https://example.com"
        }"""
        result = harness._strip_comments(text)
        assert '"value with // not a comment"' in result
        assert '"https://example.com"' in result

    def test_strip_block_comments(self):
        harness = OpenCodeHarness()
        text = """{
            "key": "value",
            /* block comment */
            "other": 1
        }"""
        result = harness._strip_comments(text)
        assert '"key"' in result
        assert '"other"' in result
        assert "block comment" not in result

    def test_detect_project_config(self, tmp_path: Path):
        harness = OpenCodeHarness()
        config = {"$schema": "https://opencode.ai/config.json"}
        (tmp_path / "opencode.json").write_text(json.dumps(config))
        detected = harness.detect(tmp_path)
        assert detected is not None
        assert detected.name == "opencode.json"
