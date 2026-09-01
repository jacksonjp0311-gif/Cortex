# Alpha.26 — Relational Causal Proof and Evidence Minimality

Status: zero-call evaluator commissioning

Alpha.25 showed that the apparent level-four floor mixed model difficulty with
two measurement artifacts: exact evidence-list equality and phrase-shaped
repair semantics. Alpha.26 changes the future instrument without rewriting a
single historical score.

## Dual representation

Every future answer contains two distinct surfaces:

```text
public prose       human-readable rationale; retained, never scored
typed causal graph machine-verifiable directed relations
```

The model does not decide whether either surface succeeds. Cortex resolves the
private contract and evaluates the submitted graph independently.

## Relational law

For required relations `R`, allowed relations `A`, submitted relations `S`,
and independently frozen minimal evidence proof sets `P_i`:

```text
RelationalPass = (R ⊆ S) ∧ (S ⊆ A)
EvidencePass   = ∃ P_i : P_i ⊆ submitted_evidence
GatePass       = RelationalPass ∧ EvidencePass ∧ ValidShape
```

Evidence order must agree with the canonical event order. A minimal proof is
preferred but a valid corroborating superset remains a PASS. This separates
proof sufficiency from proof minimality.

## Adversarial boundary

The frozen self-test proves:

- two different public paraphrases receive the same verdict;
- either independently frozen minimal proof path passes;
- a corroborating evidence superset passes but is marked nonminimal;
- insufficient or reversed evidence fails;
- missing, reversed, or unsupported relations fail;
- caller-supplied success fields fail;
- malformed output resolves UNKNOWN.

Provider family and model identity are provenance only. They never participate
in scoring.

## Historical and authority boundary

Alpha.24 remains an immutable 0/4 result under evaluator v2. Alpha.25 remains
its zero-call instrument audit. Alpha.26 independently reconstructs both before
commissioning evaluator v3; it does not rescore either run.

No live inference executes in this phase. Baseline difficulty, semantic
transfer, and model improvement remain unestablished. Host mutation, execution,
memory admission, and policy effect all remain false.

The next valid action is to forge intermediate relational cases without model
calls, then freeze a separate bounded screen before any new inference.
