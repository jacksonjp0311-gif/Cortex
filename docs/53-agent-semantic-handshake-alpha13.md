# Agent Semantic Handshake alpha.13

ARIA now exposes one deterministic discovery surface for an unfamiliar AI:

```powershell
.\aria.cmd handshake --json
```

The result is not a prompt and does not depend on a particular model provider.
It is a content-addressed description of the repository identity, connection
protocol, machine and human guides, manifest identity and state, read order,
valid commands, next synchronization boundary, and absence of initial
authority.

## Organic integration, formalized

“Organic” means that connection follows a stable sequence with minimal hidden
inference:

```text
discover → orient → verify → align → propose
```

Each phase has a defined meaning and completion condition in
`ARIA-CONNECT.json`. An AI does not need to guess which file is authoritative
or invent its own onboarding order.

The handshake is deterministic for the same repository state:

```text
H = SHA-256(canonical(
  protocol,
  repository identity,
  resource identities,
  manifest state,
  session boundary,
  read order,
  commands
))
```

The machine reads exact records. The human sees the same lifecycle explained in
the README and agent guide.

## Connection boundary

The initial authority is always `none`. A successful handshake means only that
the participant can identify and interpret ARIA’s declared connection surface.
It does not mean:

- the participant is trusted;
- repository mutation is authorized;
- a proposal is approved;
- a capability is active;
- an interpretation is correct.

Authority still requires explicit human consent, admitted capability, policy,
and deterministic execution. The handshake makes connection effortless without
making it permissive.
