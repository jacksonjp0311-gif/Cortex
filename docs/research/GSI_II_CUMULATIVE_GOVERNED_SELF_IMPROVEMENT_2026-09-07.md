# GSI-II — cumulative governed self-improvement

September 7, 2026. Product remains `10.0.0a39`. Zero provider calls.
Source-improvement v1 (`cortex-source-improvement-preregistration/1.0` and
`cortex-source-improvement-result/1.0`) and autonomous-improvement policy remain
reconstructable. GSO-IIb stays intact and separate.

Public HEAD at implementation start: `dc5bebc564b0d2de70224681060f067ff2bb9f6d`.
Exact-head CI for that commit must be re-checked at report time and must not be
treated as passed from this file.

## Loop

```
S_t -> D_t -> H_t -> C_t -> V_t -> M_t -> R_t -> S_{t+1}
```

Implemented as:

```
diagnose -> freeze experiment -> one candidate callback ->
execute_bound_transduction -> inspect/attest -> matched compare ->
recycle success or scoped constraint -> optional generation record
```

`cortex/self_improvement.py` composes existing Store receipts, signed
`AutonomyPolicyEnvelope`, `TransductionPolicy`, bounded capture, and independent
`attest_transduction_receipt`. It does not replace source-improvement v1,
Storm, canary, rollback, or promotion.

Authority is invariant: `Authority_{t+1} = Authority_t` unless an externally
authenticated host policy changes it. `EvidenceStrength != Authority`.
`BetterCandidate != MoreAuthority`. Policy precedes candidate generation.

## First experimental target

A ranking-fixture worktree (`app/value.txt`) outside the governance plane.
The evaluator, scoring rule, holdout identity, and protected prefixes are
frozen before the callback. Storm/native-agent generation is not invoked;
the host callback is a deterministic stand-in. Production promotion is not
authorized.

## Schemas

| Schema | Role |
|---|---|
| `cortex-improvement-opportunity/1.0` | Evidence-derived diagnosis |
| `cortex-self-improvement-experiment/1.0` | Frozen before generation |
| `cortex-source-improvement-preregistration/2.0` | V2 contract identity on the experiment |
| `cortex-source-improvement-result/2.0` | Matched trial result |
| `cortex-improvement-comparison/1.0` | Noncompensatory disposition |
| `cortex-improvement-constraint/1.0` | Scoped failure recycled into search |
| `cortex-verified-improvement/1.0` | Historical success; `active_guidance=false` |
| `cortex-improvement-generation/1.0` | Adjacent generation evidence |
| `cortex-gsi-reservation/1.0` | One-shot experiment reservation |
| `cortex-gsi-candidate/1.0` | Recorded callback payload |

`cortex-generation-transition/1.0` remains reconstructable and is not rewritten.

## Deterministic result

A ranking-fixture worktree with exact UTF-8/LF bytes can produce
`REPAIR_MEASURED` under declared development and holdout contracts. The
verified-improvement object has `active_guidance=false` and
`authority_effect=false`. Failed holdout does not become general improvement.
Failed candidates become `HELD_CONSTRAINT` objects whose applicability is
subject/environment/instrument scoped; unknown applicability does not
generalize. The next frozen experiment may consume applicable constraints.
Generation records without external `allow_recursive_generation` remain HELD.
`cumulative_improvement_established` is false.

Representation-unsupported (CRLF) is transduction failure, not reasoning
failure. Performance cannot compensate for a failed hard gate.

## Claim ceiling

GSI-II mechanism verified in deterministic controls.

Not claimed: general self-improvement, live provider trials, production
activation, recursive self-improvement, or cumulative `U(G2)>U(G1)>U(G0)`.

## Remaining gaps

- Live model/provider trial unauthorized; Storm candidate generation is not
  wired through this coordinator.
- OS isolation, process-tree completeness, and full environment applicability
  remain UNKNOWN / UNENFORCED / DECLARATIVE_ONLY.
- Verified-improvement objects are historical evidence only; they do not
  bypass governed memory admission.
- One-generation fixture repair is not cumulative improvement.
- Canary, rollback, and promotion remain on the existing authenticated
  autonomy path and were not exercised here.

## Recommended GSI-III threshold

Do not commission GSI-III until:

1. Exact-head CI for the GSI-II revision is `PASS_WITHIN_DECLARED_MATRIX`.
2. A live provider trial is separately authorized with a frozen experiment,
   withheld holdout, and `call_budget > 0`.
3. At least two successive generations are independently measured on the
   same declared workload without the candidate rewriting the evaluator.
4. Failures remain scoped constraints; successes remain historical until
   admitted through existing memory governance.
5. Authority, protected prefixes, and promotion criteria are unchanged by
   measured quality.

A two-generation live result may support only
"cumulative governed self-improvement observed within the declared workload".
It would not establish general recursive self-improvement.
