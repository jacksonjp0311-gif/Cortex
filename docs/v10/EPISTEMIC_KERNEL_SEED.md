# Cortex v10.0.0-alpha.16 — Epistemic Kernel Seed

Alpha.16 implements the smallest falsifiable slice of the proposed governed
epistemic control runtime. It does **not** claim a general theory of
intelligence and does not add autonomous authority.

## The state object

The working research model is:

\[
\mathcal C_t=(E_t,B_t,G_t,W_t,P_t,A_t,R_t)
\]

Alpha.16 implements only the first narrow edge: immutable evidence history
\(E_t\), a derived support state \(B_t\), and a bounded working projection
\(W_t\). The graph, predictive, authority, and action-result planes remain
separate existing Cortex subsystems rather than being renamed into this module.

## History is primary

Every epistemic event is append-only, hash-linked, repository-bound, and
bitemporal:

- **valid time** says when the evidence claims to apply;
- **system time** says when Cortex learned it.

Current state is reconstructed rather than overwritten:

\[
B_t=\Pi(E_{\le t})
\]

A retraction binds the exact event hash it retracts. It changes the projection,
not history.

## Four-valued support

Support and opposition are independent bits:

| bits | state | meaning |
|---|---|---|
| `(1,0)` | `TRUE` | supporting evidence exists |
| `(0,1)` | `FALSE` | opposing evidence exists |
| `(0,0)` | `NEITHER` | no active evidence / unknown |
| `(1,1)` | `BOTH` | conflict is preserved |

These are evidence states, not metaphysical truth. Source-lineage diversity is
reported, but independence remains `UNTESTED` until a canonical dependence
verifier resolves it.

## Action-sufficient context

For the current two-bit support semantics, one supporting representative and
one opposing representative are sufficient to preserve the decision-relevant
state of each requested claim. The compiler therefore minimizes context while
retaining conflict and proof roots:

\[
C^*=\arg\min_C L(C)
\quad\text{subject to}\quad
\Pi(C)=\Pi(E)\text{ for requested claims.}
\]

This is an exact minimum only under the declared Boolean-presence semantics.
It is not a claim of global semantic optimality. The result always says
`SEPARATE_CANONICAL_GATE_REQUIRED`; context can inform an action but cannot
authorize it.

## Continuation debt

Alpha.16 also provides a policy-driven advisory recurrence:

\[
D_{t+1}=\rho D_t+\alpha U_t+\beta C_t+\gamma\Delta_t+\eta S_t-\delta V_t.
\]

Cortex invents no coefficients or thresholds. Missing host policy yields
`UNKNOWN`. An explicit policy maps debt into `CONTINUE`, `REANCHOR`, or
`QUARANTINE`; the result still grants no execution authority.

## Modern source-experience commissioning

The zero-paid-call commissioning pulse creates a fresh canonical circulation,
competence candidate, independent semantic distillation witness, and epistemic
event in an isolated store. The fixture remains machine-typed `synthetic`.

Result: `EPISTEMIC_KERNEL_SEED_PASS` for mechanism reconstruction. This is not
empirical transfer and cannot qualify a production distribution.

The next empirical action remains narrow: calibrate held-out tasks with a
non-ceiling baseline, then compare task-only, irrelevant-sham, and relevant
verified semantic context. No live call is justified merely by this structural
pass.
