#!/usr/bin/env node

import { execSync } from "child_process"
import { spawnSync } from "child_process"

function which(cmd) {
  try {
    execSync(`which "${cmd}"`, { stdio: "ignore" })
    return true
  } catch {
    return false
  }
}

function runCmd(cmd, args) {
  // Try the pip-installed entry point first
  if (which("harness-mcp")) {
    const result = spawnSync("harness-mcp", args, { stdio: "inherit" })
    process.exit(result.status || 0)
  }

  // Fall back to python -m
  const python = which("python3") ? "python3" : "python"
  try {
    execSync(`${python} -c "import harness_mcp"`, { stdio: "ignore" })
    const result = spawnSync(python, ["-m", "harness_mcp", ...args], { stdio: "inherit" })
    process.exit(result.status || 0)
  } catch {
    // Not installed yet, try to install
    console.error("[harness-mcp] Python package not found.")
    console.error("Install it: pip install harness-mcp")
    console.error("Or: npm install -g harness-mcp (auto-installs via pip)")
    process.exit(1)
  }
}

runCmd(process.argv.slice(2))
