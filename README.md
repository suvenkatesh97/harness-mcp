# harness-mcp

Add high-quality MCP servers to any AI harness. Start with OpenCode, extend to Claude Code, Cursor, and more.

## Install

```bash
# Python (pip)
pip install harness-mcp

# Node.js (npm) — auto-installs Python deps
npm install -g harness-mcp

# Node.js (npx) — no install
npx harness-mcp list

# Single binary (no Python needed)
# Download from: https://github.com/suvenkatesh97/harness-mcp/releases
```

## Quick Start

```bash
# See what's available
harness-mcp list

# Add a server
harness-mcp add github

# Add multiple
harness-mcp add github playwright brave-search

# Add all with a tag
harness-mcp add --tag browser

# See what's configured
harness-mcp status

# Remove a server
harness-mcp remove github
```

## Harness Support

| Harness | Status |
|---------|--------|
| OpenCode | Supported |
| Claude Code | Coming soon |
| Cursor | Coming soon |

## Interactive Mode

```bash
pip install harness-mcp[interactive]
harness-mcp init
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

## Global Flags

- `--harness` - Target harness (opencode, claude, cursor). Auto-detected.
- `--scope` - `project` (default) or `global`
- `--cwd` - Working directory for project scope
- `--dry-run` - Preview changes without writing

## Custom Catalog Entries

Add your own MCP servers without code changes:

```yaml
# ~/.config/harness-mcp/catalog/my-servers.yaml
servers:
  - id: my-custom-server
    name: My Custom MCP Server
    description: Does something useful
    type: local
    command:
      - npx
      - -y
      - my-mcp-server
    env_vars:
      - name: API_KEY
        description: Your API key
        required: true
    tags:
      - custom
```

Or project-level: `.harness-mcp/catalog/*.yaml`

## OpenCode Plugin

Use harness-mcp directly within OpenCode:

```json
{
  "plugin": ["@harness-mcp/opencode-plugin"]
}
```

Then ask OpenCode to `use harness_mcp_list` or `use harness_mcp_add to add github`.

## Built-in Catalog

| Server | Type | Category |
|--------|------|----------|
| GitHub | local | git, code-review |
| Filesystem | local | files, system |
| Playwright | local | browser, testing |
| Brave Search | local | search, web |
| Memory | local | knowledge, persistence |
| Sequential Thinking | local | reasoning |
| Fetch | local | web, http |
| Context7 | remote | docs, libraries |
| Sentry | remote | monitoring, errors |
| Grep (Vercel) | remote | code-search |
| Serena | local | code-analysis |
| PostgreSQL | local | database |
| Slack | local | communication |
| Linear | local | project-management |
| Docker | local | containers |
| Puppeteer | local | browser, automation |
| GitLab | local | git, ci-cd |
| Notion | local | docs, knowledge |
| SerpAPI | local | search, web |
