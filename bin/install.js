#!/usr/bin/env node

import { execSync } from "child_process"

const python = (() => {
  try {
    execSync("which python3", { stdio: "ignore" })
    return "python3"
  } catch {
    return "python"
  }
})()

try {
  execSync(`${python} -c "import harness_mcp"`, { stdio: "ignore" })
  console.log("[harness-mcp] Python package already installed.")
} catch {
  console.log("[harness-mcp] Installing Python dependencies...")
  try {
    execSync(`${python} -m pip install harness-mcp`, { stdio: "inherit" })
    console.log("[harness-mcp] Installed successfully!")
  } catch {
    console.error("[harness-mcp] Could not auto-install Python package.")
    console.error("Run: pip install harness-mcp")
    console.error("Or: python3 -m pip install harness-mcp")
  }
}
