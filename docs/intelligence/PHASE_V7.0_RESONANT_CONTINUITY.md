# Phase v7.0 — Resonant Continuity

**Tagline:** Different organs. Different rhythms. One governed continuity.

## Planes

```text
E — Evidence
A — Adaptation
I — Immunity
C — Constitutional control
W — Independent witness
```

Forbidden flows: `A ↛ rewrite E`, `A ↛ manufacture C`, `A ↛ inspect hidden W`, `I ↛ mutate A without C`, `W ↛ certify wrong epoch`.

## Body Epoch

Deterministic `epoch_id = SHA256(identity material)` — no timestamps in identity.

Sealed on: manifest, evidence root, certificate, schema, constitution, version, adaptive/lineage roots, repair, promotion.

## Runtime phases

`QUIESCENT → OBSERVE → INDEX | EVIDENCE_FREEZE | ADAPT → … → WITNESS → PROMOTE → FEDERATE`  
plus `QUARANTINE / REPAIR / VERIFY_REPAIR / ROLLBACK`.

## CLI

```bash
python -m cortex epoch --repo CortexTeach --json
python -m cortex epoch seal --repo CortexTeach --reason promote --json
python -m cortex continuity --repo CortexTeach --json
python -m cortex continuity --repo CortexTeach --phase OBSERVE --json
python -m cortex continuity --repo CortexTeach --mesh --json
python -m cortex continuity --repo CortexTeach --with-repo OtherHost --json
python -m cortex interconnect --repo CortexTeach --json
python -m cortex host-mesh --primary CortexTeach --json
```

## Interconnect expansion (v7.0.1 surface)

Continuity is folded into operational mesh surfaces:

| Surface | What expanded |
|---------|----------------|
| `interconnect` / `mesh_status` | `continuity` slice: body_epoch_id, runtime_phase, epoch_verified, plane roots; bottlenecks for stale/unbound epoch |
| `host-mesh` | Per-host epoch + phase; `epoch_alignment` (version + constitution; **never** merge repo epochs) |
| `continuity --mesh` | Multi-host continuity rollup |
| `continuity --with-repo` | Epoch-compatible influence gate (version + constitution + verified roots) |
| `self-org` | Promote bound to verified epoch; post-pulse epoch seal + capability revoke on drift |
| `promote_gate` | Optional `body_epoch_id` / `epoch_verified` deny when stale |

Executable, not decorative: no coherence self-scores; alignment is version/constitution compatibility with independent per-repo receipts.

## Claim boundary

> Resonant Continuity ensures independently valid Cortex operations compose only when identity, authority, evidence, time (epoch), ancestry, and witness state are mutually compatible. It does not establish biological life, consciousness, or autonomous host authority.
