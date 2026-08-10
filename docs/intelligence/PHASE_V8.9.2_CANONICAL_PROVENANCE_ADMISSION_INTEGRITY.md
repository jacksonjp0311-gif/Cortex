# Cortex v8.9.2 — Canonical Provenance & Admission Integrity

## Purpose

v8.9.2 closes the evidence boundary between trajectory-derived candidates,
durable memories, and model-facing projection.  The release verifies that a
memory can be reconstructed from canonical receipts; it does not claim better
task performance, cognition, consciousness, agency, or authority.

The release law is:

```text
assertion → resolve → verify → gate → admit
```

Never:

```text
assertion → trust → persist
```

## Prior wound

Earlier surfaces trusted caller booleans for ΓΞWOS, tolerated a forged memory
receipt hash, and allowed a read path to seed `active` or append `epoch_stale`.
Canonical “latest” settings could also be written after an immutable append
failed.  Those paths made a stored claim look stronger than its evidence.

## Canonical locks

- A membrane admission must be backed by an already persisted candidate batch.
- The candidate ID and core material must match the canonical batch and the
  membrane's admitted candidate.
- Transition, prior frame, next frame, repository, session, turn, and epoch
  bindings are resolved from the immutable ledgers.
- `deep_verify_admitted_memory()` recomputes the immutable memory receipt hash;
  any hash-covered mutation is structurally invalid.
- Canonical append failures are explicit (`failed` or `partial`). Mutable
  compatibility tips never turn a failed append into success.
- Duplicate identity is reported as `duplicate`, not as a second row.

## Provenance chain

```text
memory
  → membrane admission
  → candidate ID / candidate batch
  → interconnect transition
  → prior frame + next frame
  → outcome / witness (when claimed)
  → authenticated principal will
```

The reusable verifier is [`cortex/provenance.py`](../../cortex/provenance.py).
It returns typed diagnostic planes and a lineage state:
`pass`, `fail`, `unknown`, or `legacy_partial`.  Missing modern fields in an
older receipt are reported as `legacy_partial`; they remain closed to
model-facing guidance until revalidated.  A shallow mapping cannot manufacture
canonical lineage.

## Gate derivation

The gate resolver derives constitutional (Γ), epoch/cohort (Ξ), witness (W),
outcome (O), stability (S), and principal-will verification from canonical
evidence.  Its law is:

```text
if any plane == fail:      overall = fail
elif every plane == pass:  overall = pass
else:                      overall = unknown
```

Durable admission requires `overall == pass`.  A caller-provided `True` is a
request only; a caller-provided `False` may close a gate.  `W_receipt` means
the authenticated principal will receipt. `W_gate` means the independent
measurement/outcome witness gate. They are not interchangeable.

The durable-memory condition is:

```text
Durable(M)=1
    ⇒
VerifyLineage(M)=1
∧ VerifyWill(W)=1
∧ Γ=1
∧ Ξ=1
∧ W=1
∧ O=1
∧ S=1
```

## Principal authentication

Will verification is bound to the registered principal, HMAC supplied by the
caller, payload hash, immutable canonical will receipt, repository, legal
scopes, and the active time window.  A cryptographically valid but expired
receipt is not current authority.  Historical admission fields such as
`memory_write_authorized=true` mean only that the write was authorized at
admission time; projection translates them to
`historically_admitted` / `admission_was_authorized` and keeps current host,
execution, and memory-write authority false.

## Read/write separation

Observational operations:

- will status and verification;
- memory verification and eligibility;
- `project_memories(..., persist=False)`;
- interconnect and provenance inspection.

Canonical writes are explicit: issuing a will, persisting a candidate batch,
membrane admission, admitted-memory commit, explicit state transition, or a
projection receipt with `persist=True`.  Projection never appends an active,
epoch-stale, contested, or superseded state while reading.  A projection
receipt is the only permitted write on its `persist=True` path.

## Deep memory verification

The deep verifier checks the memory receipt hash, forbidden authority bits,
trajectory origin, canonical membrane presence, candidate membership, batch
identity/material, frame-transition links, current will binding and time
window, and current memory applicability.  It reports per-plane errors rather
than collapsing an unresolved edge into pass.  The verifier does not infer
task utility or prediction accuracy.

## Failure modes

The v8.9.2 adversarial tests cover naked candidates, caller-true gate
overrides, missing membrane/batch/frame rows, candidate and transition
mismatches, receipt-hash tampering, stale epochs, expired wills, append
failure, duplicate retry, and read-only state-ledger invariance.

Partial admission is not claimed atomic across the historical candidate,
membrane, and memory tables: each canonical append is transactional, and a
failed later append is reported as `partial`/`failed` without advancing its
mutable latest tip.  Recovery tooling can therefore detect a membrane with no
corresponding memory row instead of treating it as a complete commit.

## Tests

Focused v8.9.2 tests:

```powershell
python -m pytest -q tests/test_v892_provenance.py
python -m compileall -q cortex tests
```

The focused suite exercises canonical admission, deep lineage, projection
purity, epoch exclusion, hash tamper rejection, expiry, and exactly-once
replay.  The complete repository suite remains the compatibility audit; older
tests that expect caller booleans to open gates must be updated to the new
constitutional rule rather than restoring the unsafe behavior.

## Claim boundary

Canonical identity ≠ provenance. Receipt existence ≠ receipt validity.
Historical authorization ≠ present capability. Unknown ≠ pass.

No receipt, residual, witness, or projection rank can change routing, learning,
cadence, policy, plasticity, promotion, host source, or execution authority.
Across this phase:

```text
host_mutate_authorized = false
execution_authorized    = false
```

Counterevidence and failed-hypothesis records remain historically inspectable
in the admitted-memory ledger even when the will does not select them for
active guidance.  The will cannot delete, rewrite, or mutate their immutable
source, support, or outcome fields.

## Remaining evidence

This phase establishes provenance and admission integrity, not usefulness.  A
future outcome cohort must independently measure whether model-coupled use of
selected memories improves a declared task, with counterevidence preserved and
the same epoch/schema boundary.  No current receipt proves cognition or
consciousness.

## Next phase

Only after this integrity path is mechanically maintained should Cortex enter
v9.0 — Model-Coupled Cognitive Circulation.  v9.0 is intentionally not part of
this release.
