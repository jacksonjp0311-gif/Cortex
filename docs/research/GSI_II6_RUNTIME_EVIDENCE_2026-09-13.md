# GSI-II.6 initial slice: explicit runtime evidence

Reviewed runtime checkout: `8b92b1f092e90f3400f6ca4cd7a228c8da6a07fc`.
Public main: `5cdd924` at review; successors change star metrics only.

The empirical path previously inspected the candidate receipt envelope for
runtime identity, then substituted the expected identity when absent. Episode
inspection likewise substituted expected identity for missing candidate evidence.
Both now inspect candidate objects through `candidate_runtime_matches`, requiring
nonempty candidates and explicit matching runtime identities. No archived receipt
is rewritten. This is stricter inspection, not provider attestation.

Eight new zero-provider controls include a canonical candidate with its runtime
field removed and its object hash recomputed. The empirical path must HOLD.
The new panel and existing II.4 suite passed together. The initial II.5 suite
encountered a Store receipt-session collision in the assignment mismatch control;
that control passed when rerun alone. Suite-order/timing sensitivity remains
unresolved and is not attributed to model behavior. `git diff --check` passed.

This completes only the runtime-presence slice. Budget reservation before
dispatch, receipt-derived usage, enforced holdout isolation, independent episode
reconstruction, CI wiring and full phase qualification remain outstanding.
No provider calls, source promotion or live utility experiment occurred.

## Follow-up: session collision and usage domains

The prior collision is now reproducible with a frozen clock: two opens for the
same repository/task generated identical session IDs because the input included
only a millisecond timestamp. New opens include a random invocation nonce.
Stored session identities and replay rules remain unchanged. The frozen-clock
control checks both distinct IDs and valid receipt chains.

Search-episode usage now rejects negative, fractional or boolean counts and
negative, boolean or non-finite durations before rate calculation. This validates
input domains; it does not establish that caller-supplied usage is observed usage,
nor reserve provider budgets before dispatch.

Validation: 34 controls passed across the ledger, II.5 and initial II.6 suites
after the session correction. The expanded II.6 suite passes 20 controls. Ruff
passes for changed Python files. CI now includes II.6 and ledger controls; the
uncommitted revision has no remote CI result. Full phase closure remains HELD.

Final combined validation after usage changes: **46 passed in 41.71s** across
`test_symbiosis_ledger.py`, `test_gsi_ii5.py`, and `test_gsi_ii6.py`.
Documentation validation and diff whitespace checks passed. Reviewed implementation
fingerprints were refreshed in the knowledge map.

## Candidate dispatch reservation

The empirical coordinator now appends `cortex-gsi-dispatch-reservation/1.0`
before entering `_run`. Store verifies canonical execution/assignment references,
checks prior reservation count against the frozen candidate budget, and appends
under the same `BEGIN IMMEDIATE` transaction. The reservation binds the execution,
assignment, lock and experiment; the generated candidate links its reservation.
Each assignment permits one dispatch. A crash consumes capacity conservatively;
there is no automatic refund or live-provider authorization.

Controls exercise interruption before `_run`, duplicate assignment dispatch,
concurrent reservations through separate Store connections (same and different
assignments), and reading consumed capacity through a reopened connection.
The first concurrency test failed because its fixture supplied a string where
Store requires a Path; the fixture was corrected without changing Store semantics.

This slice reserves candidate slots only. It does not meter callback-internal
calls, tokens or time; independent provider usage and enforced process isolation
remain HELD. The callback must remain the existing trusted deterministic surface.

## Call accounting API

`reserve_measured_call` appends a call reservation under Store's write transaction.
Each attempt reserves one call and an explicit total-token ceiling. Limits come
from the canonical execution receipt, and the reservation requires an existing
candidate dispatch reservation. Retry attempts consume additional capacity.
Reservations are never refunded by outcome recording.

`record_call_outcome` appends one immutable outcome in the reservation's session.
`reconstruct_call_usage` derives reserved attempts, recorded outcomes, tokens and
duration from canonical receipts. Missing outcomes, unknown usage and exceeded
limits HOLD accounting. Empty accounting is not evidence of successful execution.
The initial expanded panel passed 29 controls, with zero provider calls.

These are accounting APIs, not a newly authorized provider path. Outcome usage
is still supplied by a trusted caller. Actual adapter observation, cancellation,
hard wall-time enforcement, request identity and isolation require further work.
PASS here describes accounting conformance, not candidate success or authority.

The broader pre-accounting regression run completed with **234 passed in
316.35s**, covering GSI-II through II.6 and the symbiosis ledger. After the call
accounting addition, the expanded II.6 plus ledger panel passed **34 controls**.
Ruff, documentation validation and diff checks passed. Remote CI remains pending
until this branch's commit is evaluated; no live effect claim follows.
