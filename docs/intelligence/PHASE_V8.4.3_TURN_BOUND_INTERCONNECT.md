# Phase v8.4.3 — Turn-Bound Interconnect Frames

## Purpose

v8.4.2 made circulation **recurrent in storage**. v8.4.3 makes it **recurrent in
cognition** by binding every turn to one synchronized interconnect heartbeat.

```text
InterconnectFrame(k)
        ↓
CortexContext(k)          ← reciprocal pulse C_k
        ↓
AgentProposal(k)
        ↓
CortexEvaluation(k)
        ↓
JointAction(k)
        ↓
Outcome(k)
        ↓
InterconnectFrame(k+1)
```

## InterconnectFrameReceipt

Captures turn identity and digests:

```text
frame_id, repository_id, body_epoch_id, session_id, turn_id,
case_id, invocation_id, measurement_cohort_id, coordinate_schema_digest,
continuity_digest, measured_state_digest, self_sensing_digest,
binding_digest, resonance_digest, information_interlock_digest,
ostt_digest, symbiosis_chain_tip, compatibility_results
```

A proposal must cite:

```text
context_receipt_hash
interconnect_frame_hash
```

## Readiness panel

`mesh_green` means only:

> constitutional and continuity path appears open

Overall readiness is a non-compensatory panel:

```text
constitutional_ready
continuity_ready
measurement_ready
circulation_ready
temporal_ready
distillation_ready
overall_ready = min(planes)
```

## Defect repairs

- Assumption classification now executes before return
- Structural verification groups by `turn_id`
- Consolidation treats missing stability as **unknown**, not pass

## Claim boundary

Still advisory. Frames do not grant authority. Authenticated will remains v8.5.0.
