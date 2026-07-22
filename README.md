# harness-mcp

Add high-quality MCP servers to any AI harness. Start with OpenCode, extend to Claude Code, Cursor, and more.

## Quick Start

```bash
pip install harness-mcp

# See what's available
harness-mcp list

# Add a server
harness-mcp add github

# Add multiple
harness-mcp add github playwright brave-search

# See what's configured
harness-mcp status

# Remove a server
harness-mcp remove github
```

## Commands

| Command | Description |
|---------|-------------|
| `list` | Browse the MCP server catalog |
| `add <names...>` | Add servers by name or tag |
| `remove <names...>` | Remove servers from config |
| `status` | Show configured MCP servers |
| `search <query>` | Search the catalog |
| `init` | Interactive selection wizard |

## Harness Support

| Harness | Status |
|---------|--------|
| OpenCode | Supported |
| Claude Code | Coming soon |
| Cursor | Coming soon |

## OpenCode Plugin

Use harness-mcp directly within OpenCode:

```json
{
  "plugin": ["@harness-mcp/opencode-plugin"]
}
```
