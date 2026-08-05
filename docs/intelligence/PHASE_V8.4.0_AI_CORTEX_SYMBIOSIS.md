# Phase v8.4.0 — AI–Cortex Symbiotic Runtime

## Center of the architecture

```text
AI model  ⟷  Cortex
```

not human ↔ Cortex.

The organism layer already encoded this bond: the active AI agent is **temporary
working cortex**; Cortex is the **durable body**. They are separable. Neither is
host authority.

## Two-timescale law

Let \(q_t\) be the AI’s fast working state and \(c_t\) Cortex’s slow durable state.

\[
|\Delta q_t| \gg |\Delta c_t|
\]

\[
\Delta c_t = 0 \quad\text{whenever}\quad \Gamma_t\,\Xi_t\,W_t\,O_t\,S_t = 0
\]

Fast intelligence explores. Slow intelligence preserves only what survives
verification.

## Typed receipt chain

| Receipt | Role |
|---|---|
| `AgentInstantiationReceipt` | One bounded model instantiation |
| `CortexContextReceipt` | Exactly what Cortex gave the AI |
| `AgentProposalReceipt` | Inspectable proposal + public rationale |
| `CortexEvaluationReceipt` | allow / constrain / ask / abstain / hold |
| `JointActionReceipt` | proposal + evaluation + tool action + measured result |
| `SymbioticConsolidationReceipt` | what may be retained under slow gates |

CLI:

```powershell
python -m cortex symbiosis status --repo YourProject --json
python -m cortex symbiosis open --repo YourProject --task "..." --provider xai --model grok --json
python -m cortex symbiosis propose --repo YourProject --objective "..." --action-text "..." --citations path/a.py --json
python -m cortex symbiosis action --repo YourProject --json
python -m cortex symbiosis consolidate --repo YourProject --json
python -m cortex symbiosis next --repo YourProject --json
```

## Symbiotic learning (still gated)

Cortex may later learn which evidence helps which models. The model may learn
how to query Cortex within a session. Neither path is automatic authority.

Complementarity surplus:

\[
S_{AC}=\bigl[I(A,C;O)-\max\{I(A;O),I(C;O)\}\bigr]_+
\]

remains **unmeasured** until calibrated outcome mutual-information estimators
exist.

## Claim boundary

```text
The model may generate the future;
Cortex must preserve why that future was allowed to count.
```

No symbiotic receipt can move a constitutional bit, mutate host source, or
authorize learning by fluency alone.
