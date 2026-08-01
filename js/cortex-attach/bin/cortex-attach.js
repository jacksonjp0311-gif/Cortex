#!/usr/bin/env node
/**
 * Thin npx wrapper — zero Node runtime logic for Cortex body.
 * Delegates to Python: uvx → pipx → python -m cortex.attach_main
 */
const { spawnSync } = require("child_process");
const path = require("path");

const hostArgs = process.argv.slice(2);
const spec = "git+https://github.com/jacksonjp0311-gif/Cortex@main";

function tryRun(cmd, args) {
  const r = spawnSync(cmd, args, { stdio: "inherit", shell: process.platform === "win32" });
  if (r.error && r.error.code === "ENOENT") return null;
  return r.status === 0 ? 0 : r.status == null ? 1 : r.status;
}

let code = tryRun("uvx", ["--from", spec, "cortex-attach", ...hostArgs]);
if (code === 0) process.exit(0);
if (code !== null && code !== 0) {
  // uvx existed but failed — still try fallbacks
}

code = tryRun("pipx", ["run", "--spec", spec, "cortex-attach", ...hostArgs]);
if (code === 0) process.exit(0);

const py = process.platform === "win32" ? "python" : "python3";
code = tryRun(py, ["-m", "pip", "install", "-q", "--user", spec]);
code = tryRun(py, ["-m", "cortex.attach_main", ...hostArgs]);
if (code === null) {
  console.error(
    "Cortex attach requires Python 3.10+ (or uv). See https://github.com/jacksonjp0311-gif/Cortex"
  );
  process.exit(1);
}
process.exit(code);
