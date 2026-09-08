# GSI-III execution preregistration

Status: **EXECUTION_DRAFT**. Protocol status: **PROTOCOL_FROZEN** in
[the protocol preregistration](GSI_III_HISTORY_UTILITY_PREREG_2026-09-08.md).

This document deliberately does not authorize execution. It becomes
`EXECUTION_FROZEN` only when canonical receipts bind every item below and the
readiness verifier returns `READY`.

| Variable | Current disposition |
|---|---|
| Exact task set and semantic holdouts | NOT FROZEN |
| Exact model/provider/runtime revision | NOT FROZEN |
| Sampling and reasoning parameters | NOT FROZEN |
| Candidate, call, token and wall-clock budgets | NOT FROZEN |
| A/B/C treatment receipts | NOT FROZEN |
| Sham matching tolerances and receipt | NOT FROZEN |
| Randomization algorithm and seed commitment | NOT FROZEN |
| Minimum confirmatory sample | NOT FROZEN |
| Analysis and exclusion rules | PROTOCOL-LEVEL ONLY |
| Exact-head implementation CI | MUST BE CURRENT AND PASS |
| Live host authorization | FALSE |

Pilot observations, if later commissioned, are plumbing evidence and may not be
silently included as confirmatory data. Any changed execution variable creates a
new execution contract and randomization identity.
