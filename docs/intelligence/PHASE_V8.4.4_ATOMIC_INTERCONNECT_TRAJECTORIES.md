# Phase v8.4.4 — Atomic Interconnect Trajectories

## Purpose

v8.4.3 gave Cortex a **shared heartbeat** per turn.

v8.4.4 gives it a **verified pulse wave**:

```text
turn-bound frames
  → atomic frame capture
  → frame transitions
  → verified trajectories
```

## Atomic capture

`capture_atomic_interconnect_frame` reads surfaces under `BEGIN IMMEDIATE` when
the store supports it, recording:

```text
snapshot_transaction_id
snapshot_started_at / snapshot_completed_at
atomic_snapshot
database_wal_frame
surfaces[name].{digest, schema_version, captured_at, freshness_ms, status}
```

Stale surfaces remain visible as `present_but_stale` and fail freshness.

## Validity planes

```text
structural_state
epoch_state
schema_state
cohort_state
freshness_state
measurement_state
chain_state
overall_state   # min(fail < unknown < pass)
```

```text
structurally_valid ≠ measurement_complete ≠ temporally_coherent
compatible := structural only (legacy name)
```

## Transition + trajectory ledger

`InterconnectTransitionReceipt` binds:

```text
prior_frame_hash → next_frame_hash
proposal / evaluation / joint_action / outcome hashes
changed_surface_mask, transition_class, causal_status
```

Tables:

```text
interconnect_frames
interconnect_transitions
interconnect_trajectory_tips
```

## Context delta

`CortexContextDeltaReceipt` records new/invalidated information and
resolved/unresolved questions so \(C_{k+1} = C_k \oplus \Delta C_k\) is inspectable.

## Claim boundary

No frame, transition, readiness plane, or trajectory class authorizes execution
or learning. Causal status is temporal adjacency / outcome binding, not full
causal proof.

## Next

v8.4.5 — distillation candidate extraction from verified transitions.  
v8.5.0 — authenticated principal will.
