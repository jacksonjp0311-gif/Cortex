# Phase v8.2.4 — Selective Admission and Ranker Attribution

Status: implemented, shadow-only, promotion blocked pending calibration and replication.

## Why this phase exists

v8.2.3 found that a widened pool could reach 84.38% expected-source coverage while final top-five recall remained 50%. The system therefore needs to distinguish candidate admission from ranker loss and abstain when a reserve candidate is ambiguous.

## Selective field

The existing admission triad remains:

\[
A(q,v)=(L(q,v)\,S(q,v)\,E(v))^{1/3}.
\]

v8.2.4 adds a dimensionless margin:

\[
M(q)=\frac{A_1-A_2}{A_1},\qquad
C(q)=0.70A_1+0.30M(q).
\]

The reserve abstains unless the top eligible candidate clears the alignment and margin priors. `C` is a bounded risk proxy, not a calibrated probability; a separate calibration corpus is required before promotion.

## Attribution arms

Every case records:

- baseline, widened, selective source-reserve, random-source, and documentation-suppression pools;
- pre-ranker hybrid results;
- current-ranker results;
- source-pool ranker loss (`hybrid recall − ranked recall`).

All hits are copied. Live query order, ranker weights, topology, policy, and authority remain unchanged.

## Promotion requirements

Promotion remains false until 64+ cases show bounded selection (5–50%), zero harmful replacements, positive pool and final recall, non-inferior MRR, control superiority, bounded latency, available attribution, a calibrated risk model, and three naturally distinct epoch/graph replications. The ranker attribution is signed: positive means the current ranker improves top-five recall over hybrid order; negative means it loses recall. Calibration must be fit on a corpus separate from the frozen `bridge64` exam.

Run:

```bash
python -m cortex interlock source-trial --repo CortexTeach --suite bridge64 --limit 24 --top-k 5 --json
```

The first sealed run selected 37.5% of cases, with three helpful and zero harmful replacements. Final source-reserve recall improved from 46.88% to 51.56%; the ranker added a signed +29.69 percentage-point top-five lift over hybrid order. Promotion remains blocked because the risk proxy is not yet calibrated and only two natural contexts are present.
