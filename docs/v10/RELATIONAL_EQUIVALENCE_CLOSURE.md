# Alpha.29 — Deterministic Relational Equivalence Closure

Alpha.29 is the final evaluator-hardening phase for the synthetic relational
calibration line.

## Proposition semantics

An exact graph is replaced by required propositions with finite, host-frozen
encodings:

```text
P_i = {edge_i1, edge_i2, ...}
Satisfied(P_i, G) iff P_i intersects G
GatePass(G) iff every required P_i is satisfied
                 and G contains no frozen contradiction
                 and every edge is grounded in the public vocabulary
```

Examples include snapshot-to-source age versus generation-to-generation age,
and validation-before-derived-object versus validation-before-publication.
These alternatives are declared before any future response exists.

## Open-world but noncompensatory

A grounded additional edge is retained as an unscored addendum. It cannot
replace a missing proposition. Unknown predicates, unknown entities, or frozen
inverse temporal edges fail closed.

Evidence follows the same law:

```text
EvidencePass = exists frozen proof P where P is a subset of submitted evidence
```

Known extras are retained and mark the proof nonminimal. An unknown evidence ID
or reversed canonical order fails.

## Scientific boundary

The alpha.28 outputs are evaluated only as a disclosed post-hoc shadow. Their
immutable v3 scores remain 0/4. Shadow success can validate the new policy's
coverage but cannot establish baseline difficulty.

The commissioned zero-call shadow accepted 4/4 historical answers and the
deterministic adversarial panel passed 9/9 checks. No historical score changed,
no model call ran, and no private contract entered the public artifact. This is
evidence that the exact-edge ruler rejected bounded relational equivalence; it
is not prospective performance evidence.

Ruler building is now closed. Cortex may execute one final fresh preregistered
screen. If that screen is still dominated by representation or evaluator
collapse, the synthetic semantic benchmark is retired in favor of externally
executable code tasks with frozen tests.
