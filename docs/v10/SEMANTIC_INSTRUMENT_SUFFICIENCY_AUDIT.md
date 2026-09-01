# Cortex v10.0.0-alpha.25 — Semantic Instrument Sufficiency Audit

Alpha.25 is a zero-call correction to the proposed difficulty interpolation
phase.

## Why interpolation is held

The canonical alpha.24 result is a valid 0/4 under the frozen v2 contract. That
does not by itself prove the model lacked the causal mechanism. Cortex reloads
the result, preregistration, case receipts, trajectories, and private contracts,
then classifies the rejection surfaces without changing any score.

```text
canonical level-four floor
  -> reconstruct every historical verdict
  -> parse public response shape
  -> compare reported and required evidence IDs
  -> expose missing semantic clause groups
  -> preserve original PASS / FAIL / UNKNOWN
  -> decide whether difficulty inference is confounded
```

The audit is diagnostic only. It cannot call a model, broaden the frozen
evaluator, or convert a historical failure into PASS.

## Promotion law

Difficulty interpolation may proceed only when the apparent floor is not
explained by unresolved instrument/task confounding. If evidence minimality or
semantic clause coverage is unresolved, the correct state is HELD.

All authority remains false. Semantic transfer and Cortex improvement remain
unestablished.

## Result

The canonical audit executed with zero model calls:

```text
state                              DIFFICULTY_INTERPOLATION_HELD
cases reconstructed                4 / 4
evidence-binding rejections        3
semantic-clause rejections         1
historical scores rewritten        NO
additional model calls             0
difficulty interpolation ready     NO
audit receipt                       06cc350d6b29cbe7d6e47961acb80e711a5b09d95652c0f65587fae8106a420e
```

Three responses reported `E1..E4` while the frozen contract required
`E1..E5`. The remaining response reported the complete evidence sequence but
missed repair group 1 under the frozen atom vocabulary. These are real contract
failures and remain FAIL. They also prevent Cortex from treating 0/4 as clean
evidence of model difficulty.

The next valid action is to freeze an evidence-minimality law and a versioned
repair-semantics policy before forging an intermediate task band. No historical
receipt may be rewritten.
