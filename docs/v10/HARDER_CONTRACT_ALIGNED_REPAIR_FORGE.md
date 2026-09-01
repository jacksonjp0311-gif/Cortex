# Cortex v10.0.0-alpha.38 — Harder Contract-Aligned Repair Forge

Alpha.38 changes task difficulty only after reconstructing alpha.37's canonical
contract-aligned `4/4` ceiling.

## Transition gate

```text
canonical alpha.37 result receipt
  AND screen state = screening_ceiling
  AND success count = 4 / 4
  AND contract-alignment binding valid
  -> move_harder
```

The resulting artifact binds the prior result and preregistration receipts,
prior model identity, prior alignment-result hash, fresh public corpus, private
bundle commitment, reference-repair commissioning result, and exact source
commit. A caller label or unrelated valid circulation cannot substitute.

## Fresh task geometry

The outside-Git corpus contains four new executable defects:

1. idempotent transfers with exact transaction fingerprints;
2. per-key revision-aware positive and negative caching;
3. owned stable snapshots with per-key optimistic conflict detection;
4. atomic multi-key expiring reservations with per-key fencing tokens.

Each private assertion group cites explicit public requirement IDs. Every
public requirement has executable coverage. The private setup, assertion code,
and reference patches remain outside Git and model context.

## Commissioning law

Every unchanged baseline must fail and every host reference repair must pass
the same frozen private evaluator. Commissioning uses zero model calls and
grants no execution, mutation, policy, or memory authority.

## Claim boundary

Forge readiness proves a discriminative, structurally aligned development
instrument. It does not establish frontier-model difficulty, baseline
calibration, semantic transfer, model improvement, or autonomous self-improvement.
A new four-call task-only screen requires a separate freeze after this artifact
is committed.
