# Cortex v10.0.0-alpha.36 — Contract-Aligned Repair Forge

Alpha.36 repairs the evaluator, not the model.

The alpha.35 raw result remains an immutable `3/4`. Its zero-call audit found
that the sole failing private evaluator required a concrete snapshot mapping
after the public task had promised only an opaque snapshot. That observation
cannot be interpreted as model failure or as calibrated difficulty.

## The closed seam

Every fresh case now declares a public requirement set `R`, a private assertion
set `A`, and a host-authored mapping `mu`:

```text
for every a in A: mu(a) is non-empty and mu(a) is a subset of R
for every r in R: some a in A has r in mu(a)
```

The forge rejects:

- a private assertion with no public requirement;
- a reference to an unknown requirement;
- a public requirement with no executable coverage;
- an assertion or explicit raise hidden in private setup;
- duplicate requirement or assertion identities;
- malformed source, setup, or assertion syntax;
- mutation of either side after the salted alignment commitment is created.

The model-visible task contains the exact requirement IDs and readable text.
Private setup, assertion code, and reference patches stay outside Git and in the
host calibration vault. The ordinary executable-corpus commitment remains
intact beneath the alignment layer.

## Dual representation

```text
PUBLIC                                  HOST PRIVATE
requirement ID + readable semantics     hidden inputs + assertion code
                \                      /
                 salted commitment
                        |
              frozen executable test
                        |
        baseline failure / reference pass
```

Public semantics are cognitive form. Private executable checks are measurement
form. Hashes bind the two but do not replace either.

## Evidence boundary

The new gate proves structural traceability and reference-patch
discriminability. It does **not** prove that a host-authored assertion
semantically entails the public requirement it cites. It does not establish
baseline calibration, semantic transfer, general model improvement, or
autonomous self-improvement.

The external specification remains at:

```text
~/.cortex/private_experiments/alpha36_contract_aligned_tasks.json
```

It is deliberately outside the repository. The committed result contains only
the public corpus and commitments.

## Commissioning disposition

```text
cases                                      4
public requirements                       11
private executable assertion groups       10
unchanged baselines failing                4 / 4
host reference repairs passing             4 / 4
model calls                                0
authority granted                          none
state                         CONTRACT_ALIGNED_REPAIR_FORGE_READY
```

The next valid experiment is a separately preregistered, four-call maximum,
task-only baseline using the same structured edit transport and a canonical
binding to this forge. No call is authorized merely because the forge is ready.
