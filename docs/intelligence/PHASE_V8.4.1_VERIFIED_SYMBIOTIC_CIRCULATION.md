# Phase v8.4.1 — Verified Symbiotic Circulation

## Purpose

v8.4.0 instrumented the AI ↔ Cortex seam with typed receipts. v8.4.1 makes that
circulation **verifiable**:

1. Exactly-once canonical SQLite ledger for every receipt kind  
2. Independent receipt and session-chain verification  
3. Evaluation gates bound to **real** Cortex measurements  
4. Typed, independently witnessed **outcome** receipts  

No additional cognitive metaphors.

## Ledger

Table `symbiotic_circulation_receipts` stores immutable rows:

```text
UNIQUE(repository_id, session_id, kind)
hash chain via previous_receipt_hash + chain_sequence
tip row advances under BEGIN IMMEDIATE
```

Scientific subject hash is independent of the ledger envelope hash.

## Measurement-bound evaluation

`measure_evaluation_gates` reads:

- current epoch verification  
- measured-event completeness  
- task outcome history count  
- activation conformance / residual status  
- self-sensing and binding classifications  
- resonance / interlock surfaces  

`allow` remains review-only (`execution_authorized=false`).

## Outcome receipt

```text
outcome_subject + OUTCOME|MEASUREMENT witness → witnessed/closed
```

Consolidation defaults `witness_present` and `outcome_closed` from the outcome
receipt. \(\Gamma\Xi WOS=0 \Rightarrow\) no durable retention.

## CLI

```powershell
python -m cortex symbiosis verify --repo YourProject --json
python -m cortex symbiosis outcome --repo YourProject --success --witnessed --json
```

## Claim boundary

Still not a validated intelligence platform. v8.4.2 (cross-instantiation trial)
is required before any claim that \(U_D > U_C > U_B > U_A\).
