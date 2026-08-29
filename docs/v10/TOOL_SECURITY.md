# Tool Security

The local Cortex UI defaults to a repository-scoped proposal profile and lets
the operator reduce it to read-only or turn it off. Other runtime callers receive only the
`CapabilityGrant` they explicitly construct. The host grant contains allowed
tool names, a workspace root, optional exact command-vector allowlist, and
resource limits. The model cannot widen it.

Native tools:

- `filesystem.list`: read-only, workspace-contained, bounded directory listing;
  generated/runtime-heavy directories are excluded.
- `filesystem.read`: read-only, workspace-contained, bounded bytes.
- `workspace.propose_patch`: records a bounded unified diff and target preimage
  hashes for review. It cannot apply its own proposal. Application is a
  separate loopback operator action that reloads the exact canonical proposal,
  verifies a session-bound approval challenge, checks freshness, and evaluates
  the diff in an isolated Git worktree under a host-owned command contract. A
  second operator decision is required to promote a verified candidate into
  the active checkout. Repository HEAD and target preimages are rechecked;
  failed active-tree checks roll back.
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

The model never receives `workspace.apply`, arbitrary command execution, or a
reusable write grant. One operator approval covers one exact proposal hash.
