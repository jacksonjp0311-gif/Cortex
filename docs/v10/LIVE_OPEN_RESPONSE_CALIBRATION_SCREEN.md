# Cortex v10.0.0-alpha.21 — Live Open-Response Calibration Screen

Alpha.21 connects the answer-sealed open-response forge to the provider-neutral
native agent runtime.

## Implemented path

```text
canonical alpha.20 preflight
  -> public corpus + exact host-vault private contract
  -> host-registered live adapter
  -> four task-only native-agent calls
  -> immutable public trajectories
  -> independent atomic evaluator
  -> canonical case receipts
  -> reconstructed sequential screen
```

The frontend, model, and caller cannot provide the score. Private clauses and
reference answers never enter prompts, trajectories, Cortex evidence, or the
public result artifact.

## Tri-state outcome law

Valid JSON that fails a causal or evidence clause is FAIL. Malformed or missing
public JSON is UNKNOWN. UNKNOWN is not converted into a failed task for
difficulty estimation; it holds the screen and requests transport/contract
repair.

## Bounded execution

The initial screen is frozen to:

- level three;
- four task-only calls;
- no tools;
- one explicitly selected live adapter identity;
- the exact alpha.20 corpus and vault commitment;
- development-only evidence.

Four observations can screen a level but cannot establish calibration. No sham
or relevant semantic lesson is projected. All authority flags remain false.

## Executed result

The committed executor made exactly four task-only calls through
`OpenAI / gpt-5.6-sol`. The frozen v1 atomic evaluator returned 0/4 and the raw
screen remains immutably recorded as `screening_floor`.

A zero-call reconstruction then found that all four failures were confined to
the evaluator's required cause/repair phrase gates. Response shape, exact
evidence ordering, forbidden-claim checks, and uncertainty all passed. Two of
the four responses crossed the separately declared token-overlap diagnostic
threshold; two did not. The diagnostic therefore remains
`EVALUATOR_AUDIT_HELD`.

```text
raw v1 score                 0 / 4  (preserved)
lexical-only failures        4 / 4
strong brittleness signals   2 / 4
additional model calls       0
```

This is evidence that the exact-phrase evaluator is brittle. It is not an
alternate semantic score and does not prove that every answer was correct.
Consequently, neither `move_easier` nor a true task floor is established.
Baseline difficulty, calibration, and semantic transfer remain unresolved.

The next valid experiment must freeze a new, versioned, paraphrase-robust
evaluator before any additional live call. Historical v1 receipts and scores
must not be rewritten.
