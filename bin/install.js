#!/usr/bin/env node

// Pre-download the binary during npm install so it's ready at runtime.
// This avoids a network request on first `npx harness-mcp`.

import { spawnSync } from "child_process";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const runner = join(__dirname, "harness-mcp.js");

process.env.HARNESS_MCP_INSTALL_ONLY = "1";

try {
  spawnSync(process.execPath, [runner], {
    stdio: "ignore",
    cwd: process.cwd(),
  });
} catch {
  // Silently ignore — binary will be downloaded on first run
}
