# Tool Security

The local Cortex UI defaults to a repository-scoped read-only profile and lets
the operator turn that profile off. Other runtime callers receive only the
`CapabilityGrant` they explicitly construct. The host grant contains allowed
tool names, a workspace root, optional exact command-vector allowlist, and
resource limits. The model cannot widen it.

Native tools:

- `filesystem.list`: read-only, workspace-contained, bounded directory listing;
  generated/runtime-heavy directories are excluded.
- `filesystem.read`: read-only, workspace-contained, bounded bytes.
- `terminal.execute`: argument-vector execution without a shell, contained
  working directory, exact host-approved argument vector, timeout, and bounded
  output. Granting an executable does not grant arbitrary arguments.

Tool output is marked `trusted=false`. Success means only that the executor
completed under its local contract; it does not establish task success or
truth. The runtime trajectory keeps `host_mutate_authorized=false`,
`memory_admission_authorized=false`, `policy_effect=false`, and
`execution_authorized=false`. A per-call capability decision is not durable
Cortex execution authority.

Path traversal, shell command strings, ungranted tools, executable mismatch,
oversized output, duplicate call IDs, and timeouts fail closed.
