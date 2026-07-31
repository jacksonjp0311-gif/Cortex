# Phase v7.1.1 — Geometry Seal

**Tagline:** Measured truth only. Bound phases only. Audited evidence edges.

## Scope (narrow)

1. **Hard CI gate** — `scripts/ci/release_receipt_v711.py` (no `continue-on-error`).
2. **Axis truth sources** — `MEASURED`, `RECEIPT_VERIFIED`, `OPERATOR_ASSERTED`, `SIMULATED`, `UNKNOWN`.  
   Live promote / repair_readmit / federate accept **only** `MEASURED` and `RECEIPT_VERIFIED`.
3. **Phase binding** — `BOUND`, `BOOTSTRAP_UNBOUND`, `STALE`, `MISMATCHED`, `UNKNOWN`.  
   Only **`BOUND`** is constitutionally compatible.
4. **Evidence refresh edge** — audited path:  
   `observe_drift → authorize_evidence_refresh → refresh_evidence_only → recompute_epoch_controller → select_path`  
   (`cortex/evidence_refresh.py`)
5. **Foreign prediction test** — geometry detects unencoded authority/epoch/witness/provenance gaps on a foreign host.

## Claim boundary

> Geometry Seal strengthens falsifiable admission control. It does not grant host mutation authority or claim consciousness.
