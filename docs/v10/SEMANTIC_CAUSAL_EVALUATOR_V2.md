# Cortex v10.0.0-alpha.22 — Semantic Causal Evaluator v2

Alpha.22 repairs the exact-phrase measurement wound exposed by the first live
open-response screen. It does not rescore alpha.21 and does not invoke a model.

## Evaluation law

```text
Pass = ResponseShape
       ∧ CauseSemanticAtoms
       ∧ RepairSemanticAtoms
       ∧ ¬NegatedRequiredAtoms
       ∧ ExactEvidenceOrder
       ∧ ¬ForbiddenClaims
       ∧ ValidUncertainty
```

The lexicon is host-controlled, versioned, and hash-bound. It recognizes only
declared surface variants for causal objects and relations. Model identity,
provider family, fluency, token overlap, caller scores, and response metadata
cannot open a gate.

The semantic atoms include relations, not just bags of words. In the level-
three cache case, for example, `pre_commit`, `concurrent_reader`,
`cache_write`, and `stale_value` must all appear in the causal explanation.
The repair must express post-commit invalidation or the independently declared
versioning alternative.

## Private boundary

The public evaluator manifest contains only the source corpus identity,
lexicon hash, case IDs, and private-key commitment. Compiled per-case semantic
contracts remain in the operating-system credential vault. The artifact does
not contain reference answers or private semantic groups.

## Adversarial commissioning

The zero-call self-test covers:

- every canonical reference response;
- a held-out surface paraphrase;
- wrong temporal order;
- negated required semantics;
- reversed evidence;
- caller-supplied success;
- forbidden retry advice;
- contract and bundle tampering.

All checks are deterministic. Failure prevents the v2 preflight from sealing.

## Historical boundary

The four alpha.21 trajectories may be evaluated in shadow mode to confirm that
the new instrument handles the observed language. This is post-hoc development
evidence because the evaluator was built after those outputs existed.

```text
historical v1 score       remains immutable
v2 shadow verdict         diagnostic only
baseline difficulty       unresolved
semantic transfer         not executed
```

A new four-call task-only screen requires separate authorization after the v2
manifest, private vault contract, source commit, and preflight receipt are
sealed.

## Commissioning result

The committed alpha.22 implementation produced:

```text
state                       SEMANTIC_CAUSAL_EVALUATOR_V2_READY
self-test                   67 / 67 passed
historical shadow           4 / 4 passed
model calls                 0
preflight receipt           8fabbecc9484a6238e97e61c71c4e73c5774d472a25aff345f7987906c97f252
```

The historical shadow result is deliberately non-authorizing and post-hoc.
It proves that v2 accepts those four observed paraphrases under its declared
atoms. It does not prove general semantic entailment, baseline difficulty, or
Cortex-caused improvement.
