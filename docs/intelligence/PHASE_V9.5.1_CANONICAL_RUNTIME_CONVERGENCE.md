# Phase v9.5.1 — Canonical Runtime Convergence

**Status:** implemented
**Boundary:** operational hardening; no new cognition, authority, or empirical-transfer claim

## Purpose

v9.5 completed the governed return path from exact package-use evidence to an
explicitly verified competence successor. v9.5.1 makes the runtime that
inspects and measures that architecture obey the same evidentiary discipline.

The release law is:

```text
inspection != initialization
cached drift observation != host-immutability proof
rendering failure != system state
unknown repository != implicit repository creation
```

## Prior wounds

Four operational seams remained:

1. `ranker_status()` called the ranker initialization path. A read could insert
   a model, migrate its feature schema, or fail a foreign key when the
   repository name was wrong.
2. `mesh_status()` entered repository-bound subsystems before establishing
   that the repository identity existed.
3. glyph-bearing CLI help could raise `UnicodeEncodeError` when Windows or a
   redirected stream selected a legacy code page.
4. an attempted desktop optimization reused one manifest observation as both
   sides of the activation immutability projection. That would turn an
   independently measured invariant into asserted equality.

The generated agent protocol also required agents to read the emergence log,
while its repository wrappers did not expose that command.

## Read-only interconnect

Interconnect now resolves repository identity first. An unknown name returns a
typed `unknown_repository` report with a failed readiness state and all
authority flags false. It does not initialize a ranker, create repository
identity, or enter downstream telemetry.

Ranker inspection directly loads the existing canonical row. If none exists,
the result is `available=false`. If its feature schema is old, status reports
`migration_required=true`; inspection does not repair it. Ranker creation and
migration remain write-path operations.

Every interconnect report states:

```text
advisory_only = true
policy_effect = false
update_authorized = false
host_mutate_authorized = false
execution_authorized = false
```

## Independent host measurement

Activation may pass its already captured drift observation into the explicit
evidence-refresh edge. After refresh, the edge uses the manifest returned by
the indexer when available. This removes redundant scans from the routing
decision.

That optimization stops at the metrology boundary. Activation still performs:

```text
host_manifest_before = scan(host, after optional refresh)
activation pathway
host_manifest_after  = scan(host, at finalization)
host_immutable       = host_manifest_before == host_manifest_after
```

The before value is never reused as the after value. A concurrent host-source
change therefore fails the named `host_immutable` invariant and prevents a
`conformance_measured` receipt.

## Windows output boundary

The CLI configures stdout and stderr for UTF-8 with a non-throwing error policy
before argument parsing. This includes `--help`, where glyphs occur in parser
descriptions. Embedded streams that cannot be reconfigured retain their host
contract.

This changes presentation only. Glyphs remain labels, never executable
instructions or authority.

## Agent-wrapper parity

Generated PowerShell and Bash wrappers now route `emergence-log` to the
canonical CLI. The mandatory startup instruction and the installed executable
surface therefore agree.

## Tests

Focused adversarial coverage proves:

- an unknown repository produces a closed report with zero database writes;
- known-repository interconnect does not initialize a missing ranker;
- direct ranker status does not initialize a missing model;
- `cortex --help` succeeds with `PYTHONIOENCODING=cp1252:strict` and preserves
  its UTF-8 glyph;
- a host-source mutation injected during activation is detected by independent
  before/after manifests and fails `host_immutable`;
- existing observation-nonmutation and activation-conformance tests remain
  intact.

## Claim boundary

v9.5.1 establishes operational convergence and read-path integrity. It does
not establish consciousness, subjective sensing, improved reasoning, causal
competence benefit, real-model transfer, or distributed intelligence gain.

The v9.5 competence ledgers remain unpopulated until real, host-registered
model circulation and exact package-use evidence are deliberately produced.

## Next evidence

The next bounded step is live evidence commissioning under one current sealed
epoch:

1. register a genuine host-controlled live adapter;
2. run independently evaluated model circulation;
3. distill and transfer one competence under matched controls;
4. project one exact target-bound package;
5. collect independently witnessed package-use outcomes;
6. freeze and analyze the first empirical v9.5 cohort;
7. verify one scoped successor and require fresh transfer before redistribution.

Only after multiple independent competence lineages survive that loop should
Cortex consider governed competence composition.
