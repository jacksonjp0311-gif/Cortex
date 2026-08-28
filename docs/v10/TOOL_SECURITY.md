# Tool Security

Tools are unavailable by default. The host constructs a `CapabilityGrant`
containing allowed tool names, a workspace root, optional executable allowlist,
and resource limits. The model cannot widen it.

Alpha 1 tools:

- `filesystem.read`: read-only, workspace-contained, bounded bytes.
- `terminal.execute`: argument-vector execution without a shell, contained
  working directory, explicit executable allowlist, timeout, bounded output.

Tool output is marked `trusted=false`. Success means only that the executor
completed under its local contract; it does not establish task success or
truth. The runtime trajectory keeps `host_mutate_authorized=false`,
`memory_admission_authorized=false`, `policy_effect=false`, and
`execution_authorized=false`. A per-call capability decision is not durable
Cortex execution authority.

Path traversal, shell command strings, ungranted tools, executable mismatch,
oversized output, duplicate call IDs, and timeouts fail closed.
