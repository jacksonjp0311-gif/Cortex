# Phase v8.2.3 — Source Admission Field

Status: implemented, shadow-only, promotion blocked pending replicated evidence.

## Purpose

v8.2.2 showed that geometric reranking cannot recover an implementation file that never enters the candidate set. v8.2.3 therefore separates retrieval into two measured events:

\[
P(\text{top-5 hit}) = P(\text{expected source enters pool})
\times P(\text{top-5 hit}\mid\text{source entered pool}).
\]

This is an operational decomposition, not a consciousness claim.

## Triadic admission geometry

For query `q` and source path `v`:

\[
A(q,v)=(L(q,v)\,S(q,v)\,E(v))^{1/3}.
\]

- `L`: lexical/path alignment, including bounded lexical rank.
- `S`: best indexed source-chunk cosine mapped from `[-1,1]` into `[0,1]`.
- `E`: evidence reliability (`1.0` host source, `0.90` tests, `0.82` scripts).

All axes have independent hard floors. A high value on one axis cannot hide a failure on another.

## Frozen matched experiment

`bridge64-v1-2026-08-02` remains an evaluation-only exam and never feeds ranker training or threshold selection. Each case records both pool-stage and top-5 ranks for five arms:

1. baseline pool of 24;
2. widened pool of 48;
3. fixed-cardinality query-conditioned source reserve;
4. fixed-cardinality deterministic random-source reserve;
5. documentation/card suppression.

All arms are built from copied hits and reranked by the same existing ranker with spectral enrichment disabled. The live query response is never replaced.

## Replication and promotion gate

Promotion is false unless all gates pass on at least 64 cases, including positive pool recall lift, non-inferior final recall and MRR, superiority to random source, zero harmful replacements, bounded selection and latency, fixed cardinality, policy inertness, and three consistent distinct epoch/graph contexts. Trial identity binds the full corpus, body epoch, graph fingerprint, and parameter map.

Run:

```bash
python -m cortex interlock source-trial --repo Cortex --suite bridge64 --limit 24 --top-k 5 --json
```

The ARIA glyph `⟢` names `SourceAdmissionField`: an evidence gate with reset semantics. It grants no authority.

## First sealed Cortex measurement

On body epoch `a9fdcdab…` and 64 frozen cases:

| Arm | Pool recall | Final top-5 recall |
|---|---:|---:|
| baseline | 64.06% | 48.44% |
| widened | 84.38% | 50.00% |
| source reserve | 71.88% | 51.56% |
| random source | 62.50% | 46.88% |
| documentation suppression | 81.25% | 50.00% |

The source reserve produced three helpful and one harmful final replacement. Its 100% selection rate also exceeded the bounded-admission gate. Promotion is therefore false. The decomposition exposes two distinct constraints: implementation evidence is frequently absent from the 24-item pool, and final ranking discards much of the evidence recovered by widening. The next experiment should add calibrated abstention/margin logic and a ranker-stage lesion, not enable the current reserve in live routing.
