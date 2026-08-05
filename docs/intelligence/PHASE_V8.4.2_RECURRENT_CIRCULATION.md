# Phase v8.4.2 — Recurrent Circulation Hardening

## Purpose

v8.4.1 proved a single circulation arc. v8.4.2 makes that circulation **recurrent
and honest under partial measurement** before any will protocol is added.

```text
agent_instantiation → cortex_context →
  [ proposal → evaluation → joint_action → outcome ]* →
  consolidation
```

## Ledger identity

Exactly-once uniqueness:

```text
UNIQUE(repository_id, session_id, turn_id, kind)
UNIQUE(repository_id, session_id, event_id)
```

Every receipt carries `turn_id`, `event_id`, `case_id`, and `invocation_id`.

## Tri-state gates

Evaluation measurements are `pass | fail | unknown`.

- **fail** holds or constrains  
- **unknown never allows**  
- `host_immutable` and `authority_scope_ok` no longer default to pass  

## Mask-aware prediction

Predictive scoring uses only valid coordinates:

\[
E_t=\frac{\sum_i m_i |y_i-\hat y_i|}{\sum_i m_i+\epsilon}
\]

Null is absent from the sum — not imputed as zero.

## Assumption taxonomy

Next-session brief separates:

```text
assumptions_disconfirmed
assumptions_unverified
assumptions_blocked
assumptions_supported
```

Held or asked proposals do not label assumptions as failed.

## Acceptance

- At least two dialogue turns ledgered in one session  
- Independent chain verification after process restart  
- No optimistic gate defaults  
- No null→zero authority in residual scoring  

## Explicit non-goals

- Origin-bound will (v8.5.0)  
- Distillation membrane unification (v8.5.1)  
- Empirical \(U_E > U_C\) trials (v8.5.2+)  

Claim boundary unchanged: measurement ≠ authority; AI may not author will.
