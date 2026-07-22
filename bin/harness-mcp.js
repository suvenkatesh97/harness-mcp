#!/usr/bin/env node

import { spawnSync, execSync } from "child_process";
import { createWriteStream, existsSync, mkdirSync, chmodSync, renameSync } from "fs";
import { homedir, platform, arch } from "os";
import { join } from "path";
import { Readable } from "stream";
import { finished } from "stream/promises";

const VERSION = "0.1.1";
const REPO = "suvenkatesh97/harness-mcp";

function getPlatform() {
  const p = platform();
  const a = arch();
  if (p === "linux" && a === "x64") return { name: "linux", binary: "harness-mcp-linux" };
  if (p === "darwin" && a === "x64") return { name: "macos", binary: "harness-mcp-macos" };
  if (p === "darwin" && a === "arm64") return { name: "macos", binary: "harness-mcp-macos" };
  if (p === "win32") return { name: "windows", binary: "harness-mcp.exe" };
  console.error(`[harness-mcp] Unsupported platform: ${p}/${a}`);
  process.exit(1);
}

function getCacheDir() {
  const dir = join(homedir(), ".harness-mcp", "bin");
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
  return dir;
}

function getBinaryPath() {
  const { binary } = getPlatform();
  return join(getCacheDir(), binary);
}

async function downloadBinary(url, dest) {
  const tmp = dest + ".tmp";
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} ${response.statusText}`);
  }

  const total = parseInt(response.headers.get("content-length") || "0", 10);
  let downloaded = 0;

  process.stderr.write(`[harness-mcp] Downloading...`);
  if (total > 0) {
    process.stderr.write(` (${(total / 1024 / 1024).toFixed(1)}MB)`);
  }
  process.stderr.write(`\n`);

  const file = createWriteStream(tmp);
  const body = Readable.fromWeb(response.body);

  body.on("data", (chunk) => {
    downloaded += chunk.length;
    if (total > 0) {
      const pct = Math.min(100, Math.round((downloaded / total) * 100));
      process.stderr.write(`\r[harness-mcp] ${pct}%`);
    }
  });

  await finished(body.pipe(file));
  process.stderr.write(`\r[harness-mcp] Done!          \n`);

  renameSync(tmp, dest);
  if (platform() !== "win32") chmodSync(dest, 0o755);
}

function which(cmd) {
  try { execSync(`which "${cmd}"`, { stdio: "ignore" }); return true; } catch { return false; }
}

async function ensureBinary() {
  // Prefer pip-installed entry point
  if (which("harness-mcp")) return "harness-mcp";

  // Check for cached binary
  const dest = getBinaryPath();
  if (existsSync(dest)) return dest;

  // Download binary from GitHub releases
  const { binary } = getPlatform();
  const url = `https://github.com/${REPO}/releases/download/v${VERSION}/${binary}`;

  try {
    await downloadBinary(url, dest);
    return dest;
  } catch (e) {
    console.error(`[harness-mcp] Failed to download binary: ${e.message}`);
    console.error(`[harness-mcp] Install manually: pip install harness-mcp`);
    process.exit(1);
  }
}

async function main() {
  // For postinstall: just download, don't run
  if (process.env.HARNESS_MCP_INSTALL_ONLY === "1") {
    const dest = getBinaryPath();
    if (!existsSync(dest)) {
      try {
        const { binary } = getPlatform();
        const url = `https://github.com/${REPO}/releases/download/v${VERSION}/${binary}`;
        await downloadBinary(url, dest);
      } catch {
        // Silently ignore download errors during install
      }
    }
    return;
  }

  const binary = await ensureBinary();
  const result = spawnSync(binary, process.argv.slice(2), { stdio: "inherit" });
  process.exit(result.status || 0);
}

main();
