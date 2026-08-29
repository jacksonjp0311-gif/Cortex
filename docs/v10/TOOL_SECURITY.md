# Tool Security

Alpha.6 represents every native tool with a versioned, content-addressed
manifest. The manifest defines its conservative input/output schema, authority
class, declared side effects, network/secret access, and cancellation support.
The catalog is host-owned: provider output and model tool calls can reference a
registered identity but cannot register or modify one.

The local Cortex UI defaults to a repository-scoped proposal profile and lets
the operator reduce it to read-only or turn it off. Other runtime callers receive only the
`CapabilityGrant` they explicitly construct. The host grant contains allowed
tool names, a workspace root, optional exact command-vector allowlist, and
resource limits, principal, purpose, issue time, expiry, call budget, and total
tool-time budget. The model cannot widen it. Caller-shaped fields such as
`approved=true` are rejected by the tool schema rather than interpreted as
evidence.

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

Every tool observation is sealed as a `cortex-tool-execution-receipt/1.0`
object. Its identity covers the exact manifest, grant, arguments, output,
status, and chronology; the containing trajectory binds the receipt back to
the corresponding request and event. Tool output is marked `trusted=false`.
Success means only that the executor
completed under its local contract; it does not establish task success or
truth. The runtime trajectory keeps `host_mutate_authorized=false`,
`memory_admission_authorized=false`, `policy_effect=false`, and
`execution_authorized=false`. A per-call capability decision is not durable
Cortex execution authority.

Path traversal, shell command strings, ungranted or unregistered tools,
unexpected arguments, inactive grants, exhausted budgets, executable mismatch,
oversized output, duplicate call IDs, and timeouts fail closed. Cooperative
cancellation terminates a running subprocess and seals a `cancelled` result.

The model never receives `workspace.apply`, arbitrary command execution, or a
reusable write grant. One operator approval covers one exact proposal hash.
