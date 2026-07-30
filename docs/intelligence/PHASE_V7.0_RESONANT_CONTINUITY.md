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
```

## Claim boundary

> Resonant Continuity ensures independently valid Cortex operations compose only when identity, authority, evidence, time (epoch), ancestry, and witness state are mutually compatible. It does not establish biological life, consciousness, or autonomous host authority.
