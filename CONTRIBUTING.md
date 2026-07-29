# Contributing

Read [`docs/COVENANT.md`](docs/COVENANT.md) before expanding surface area.

## Required checks

1. Create a focused branch.
2. Preserve the **single-substrate** invariant: no competing repository, episodic, or consolidation database.
3. Add or update tests for behavior changes.
4. Run `python -m compileall -q cortex thalamus tests`.
5. Run `python -m pytest tests -q`.
6. Run `python -m cortex mirror --json` and require `"glow": true` for changes that touch bootstrap, retrieval, ARIA, governor, or continuation.
7. Run `python -m cortex benchmark --verify --json` when benchmarks or thresholds change.
8. Run Bash syntax checks on `cortex.sh`, `cortex-all-one.sh`, and `scripts/bash/*.sh` when those files change.
9. Preserve the authority boundary: Cortex may retrieve, route, and verify memory but may not authorize source mutation.
10. Keep parsers and environment detectors bounded, failure-tolerant, and explicit about unsupported syntax.
11. Keep neural plasticity bounded and restricted to existing compiled relationships.

## Vocabulary freeze (aligned geometry)

Do **not** introduce new biological organ names, second ledgers, or parallel “brains” unless the change is a forced reduction of tension on an existing covenant axis (Authority, Evidence, Activation, Language, Economics). Prefer:

- harder gates on existing surfaces
- clearer packet telemetry
- better foreign-host behavior

## ARIA vendor bumps

Never mix ad-hoc edits of `cortex/aria_meta/vendor` into unrelated core commits. Use:

```powershell
.\scripts\powershell\Bump-AriaSnapshot.ps1 -Source <ARIA-root> -SourceCommit <sha>
```

```bash
./scripts/bash/bump-aria-snapshot.sh /path/to/ARIA <sha>
```

Prefer a dedicated `chore: bump INTERNAL ARIA snapshot` commit.

## Interlock matrix

| If you change… | Re-verify… |
|---|---|
| `query` / verify probes | Deferred survives bootstrap |
| Wake cues | Fluency corpus 0 false / 0 missed wakes |
| Bootstrap / indexer tiers | Work-proxy + mirror economics |
| Continuation / promote | Authority monotonicity tests |
| Vendor ARIA | `verify_bundle` + manifest |
| Governor modes | `read_only` under drift still binds |
