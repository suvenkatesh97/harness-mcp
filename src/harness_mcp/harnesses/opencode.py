from __future__ import annotations

from pathlib import Path
from typing import Any

import json5

from harness_mcp.catalog import McpServer
from harness_mcp.harnesses.base import AbstractHarness, McpConfigEntry


class OpenCodeHarness(AbstractHarness):
    name = "opencode"

    def detect(self, cwd: Path) -> Path | None:
        for name in ("opencode.jsonc", "opencode.json"):
            path = cwd / name
            if path.exists():
                return path
        global_path = Path.home() / ".config" / "opencode" / "opencode.json"
        if global_path.exists():
            return global_path
        global_path_jsonc = Path.home() / ".config" / "opencode" / "opencode.jsonc"
        if global_path_jsonc.exists():
            return global_path_jsonc
        return None

    def resolve_config_paths(self, cwd: Path, scope: str) -> list[Path]:
        paths = []

        if scope == "global":
            paths.append(Path.home() / ".config" / "opencode" / "opencode.json")
            paths.append(Path.home() / ".config" / "opencode" / "opencode.jsonc")
        elif scope == "project":
            paths.append(cwd / "opencode.jsonc")
            paths.append(cwd / "opencode.json")

        return paths

    def _parse_jsonc(self, text: str) -> dict[str, Any]:
        stripped = self._strip_comments(text)
        return json5.loads(stripped)

    def _strip_comments(self, text: str) -> str:
        result = []
        in_string = False
        string_char = None
        in_line_comment = False
        in_block_comment = False
        i = 0
        while i < len(text):
            ch = text[i]

            if in_line_comment:
                if ch == "\n":
                    in_line_comment = False
                    result.append(ch)
                i += 1
                continue

            if in_block_comment:
                if ch == "*" and i + 1 < len(text) and text[i + 1] == "/":
                    in_block_comment = False
                    i += 2
                    continue
                if ch == "\n":
                    result.append(ch)
                i += 1
                continue

            if in_string:
                result.append(ch)
                if ch == "\\" and i + 1 < len(text):
                    result.append(text[i + 1])
                    i += 2
                    continue
                if ch == string_char:
                    in_string = False
                    string_char = None
                i += 1
                continue

            if ch == '"' or ch == "'":
                in_string = True
                string_char = ch
                result.append(ch)
                i += 1
                continue

            if ch == "/" and i + 1 < len(text):
                next_ch = text[i + 1]
                if next_ch == "/":
                    in_line_comment = True
                    i += 2
                    continue
                if next_ch == "*":
                    in_block_comment = True
                    i += 2
                    continue

            if ch == "#":
                in_line_comment = True
                i += 1
                continue

            if ch == ",":
                next_non_ws = i + 1
                while next_non_ws < len(text) and text[next_non_ws] in " \t\r\n":
                    next_non_ws += 1
                if next_non_ws < len(text) and text[next_non_ws] in "}]":
                    pass

            if ch == "\\" and i + 1 < len(text):
                next_ch = text[i + 1]
                if next_ch == "\n":
                    i += 2
                    continue

            result.append(ch)
            i += 1

        return "".join(result)

    def read_config(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        text = path.read_text()
        return self._parse_jsonc(text)

    def write_config(self, path: Path, config: dict[str, Any]):
        import json

        path.parent.mkdir(parents=True, exist_ok=True)
        json_text = json.dumps(config, indent=2, ensure_ascii=False)
        path.write_text(json_text + "\n")

    def get_mcp_entries(self, config: dict[str, Any]) -> dict[str, McpConfigEntry]:
        mcp_section = config.get("mcp", {})
        if not mcp_section:
            return {}

        entries: dict[str, McpConfigEntry] = {}
        for name, data in mcp_section.items():
            if not isinstance(data, dict):
                continue
            entries[name] = McpConfigEntry(
                type=data.get("type", "local"),
                command=data.get("command"),
                url=data.get("url"),
                enabled=data.get("enabled", True),
                environment=data.get("environment", {}),
                headers=data.get("headers"),
                cwd=data.get("cwd"),
                timeout=data.get("timeout"),
            )
        return entries

    def set_mcp_entries(
        self, config: dict[str, Any], entries: dict[str, McpConfigEntry]
    ) -> dict[str, Any]:
        mcp_section: dict[str, Any] = {}
        for name, entry in entries.items():
            item: dict[str, Any] = {
                "type": entry.type,
                "enabled": entry.enabled,
            }
            if entry.command:
                item["command"] = entry.command
            if entry.url:
                item["url"] = entry.url
            if entry.environment:
                item["environment"] = entry.environment
            if entry.headers:
                item["headers"] = entry.headers
            if entry.cwd:
                item["cwd"] = entry.cwd
            if entry.timeout:
                item["timeout"] = entry.timeout
            mcp_section[name] = item

        config["mcp"] = mcp_section
        return config

    def entry_from_catalog(
        self, server: McpServer, env_overrides: dict[str, str] | None = None
    ) -> McpConfigEntry:
        entry = McpConfigEntry(
            type="local" if server.type == "local" else "remote",
            enabled=server.enabled,
        )

        if server.type == "local" and server.command:
            entry.command = list(server.command)

        if server.type == "remote" and server.url:
            entry.url = server.url
            if server.headers:
                entry.headers = dict(server.headers)

        env = {}
        if env_overrides:
            env.update(env_overrides)
        for ev in server.env_vars:
            if ev.default and ev.name not in env:
                env[ev.name] = ev.default

        if env:
            entry.environment = env

        return entry

    def env_var_to_placeholder(self, env_var_name: str) -> str:
        return f"{{env:{env_var_name}}}"
