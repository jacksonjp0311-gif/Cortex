# GSI-II.3 — empirical readiness and measurement closure

September 8, 2026. Product remains `10.0.0a39`. Zero provider calls.

Implementation start HEAD: `f673c3ef327f8f1c44750e9396492fbcd8518cce`
(star-lattice metrics only). Product source remains
`9408f976706d6ba2822b387b90f7662cf2059981`, whose exact-head CI completed
success as run 34181576991. GSI-II.3 itself has no exact-head CI until pushed.

This phase does not run a live history experiment. It closes measurement
ambiguities so a future same-model A/B/C study can be reconstructed.

## Canonical generation effect

```text
Delta_candidate = U(candidate_worktree) - U(S_t)
Delta_generation = U(S_{t+1}) - U(S_t)
```

Only `Delta_generation` is taken from the post-promotion measurement receipt.
Candidate deltas remain diagnostic. A Store chain whose copied generation
deltas disagree with reconstructed promoted-state deltas is `CHAIN_INVALID`.

## Utility family versus evaluation partition

`cortex-improvement-utility-family/1.0` binds the measurement construct.
`cortex-evaluation-partition/1.0` binds one-use development/holdout content.

Fresh partitions may share a family. Unrelated task families remain a vector.

## Holdout content identity

Human `holdout_id` is metadata. The reservation key is

```text
H(canonical holdout contract, evaluator identity, utility family)
```

Same withheld content under a new label is rejected.

## Derived constitution and authority state

Constitutional evidence is reconstructed from receipts: signed host policy,
frozen policy hash, zero candidate policy mutation, authority-state identity
before and after, protected-surface hashes, and actual claim flags.
`allow_recursive_generation in (True, False)` is not authorization evidence.

`cortex-gsi-authority-state/1.0` must be unchanged across a normal generation.

## Capability threat model

Deterministic callbacks are `INTERFACE_ENFORCED`. Tool-using agents remain
`HELD`. `live_provider_holdout_eligible` is false.

## Claim ceiling

GSI empirical measurement and causal-contrast mechanics verified in
deterministic controls.

Not established: inherited-history utility, live cumulative self-improvement,
or any broader intelligence claim.
`cumulative_self_improvement_established = false`
`history_utility_established = false`

See [GSI-III preregistration](GSI_III_HISTORY_UTILITY_PREREG_2026-09-08.md).
That experiment is frozen and not executed here.
