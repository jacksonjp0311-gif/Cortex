# Alpha.27 — Intermediate Relational Task Forge

Status: zero-call task commissioning

Alpha.27 creates a new development corpus between the level-three ceiling and
the instrument-confounded level-four floor. It does not rescore old answers and
does not invoke a model.

## Controlled geometry

The corpus contains three panels of four cases:

| Band | Causal relations | Repair relations | Evidence policy |
|---|---:|---:|---|
| `bridge_low` | 4 | 2 | constant |
| `bridge_mid` | 5 | 2 | constant |
| `bridge_high` | 7 | 3 | constant |

All panels accept the same independently frozen proof sets:

```text
P1 = {E1, E2, E3, E4}
P2 = {E2, E3, E4, E5}
```

The task changes relational depth, not evidence-list strictness. Valid
corroborating supersets remain acceptable and are recorded as nonminimal.

## Answer boundary

The public corpus includes events, entity identifiers, response shape, panel
identity, and salted contract commitments. Required causal and repair graphs,
reference responses, and private contracts remain in the host credential
vault. Model and provider identity never participate in scoring.

## Sequential screen law

A later phase may separately freeze four calls for `bridge_low`:

```text
0.30 <= success_rate <= 0.70  -> informative band; stop
success_rate > 0.70           -> move one band higher
success_rate < 0.30           -> stop; geometry remains too hard
```

No panel may open from this forge receipt alone. A new authorization must bind
the exact corpus, evaluator, model boundary, call count, and stop rule.

## Claim boundary

This phase verifies corpus construction, private/public separation, progressive
relation counts, constant evidence policy, reference evaluator compatibility,
and canonical alpha.26 lineage. It does not establish task calibration,
semantic transfer, Cortex improvement, consciousness, or autonomous authority.
