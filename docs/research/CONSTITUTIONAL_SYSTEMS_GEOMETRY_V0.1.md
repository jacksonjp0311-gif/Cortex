# Constitutional Systems Geometry v0.1

**Status:** Experimental research note  
**Cortex version:** 7.1.0  
**Not a universal law. Not consciousness. Not physical geometry.**

## Model

A constitutional system geometry is a six-tuple:

\[
G = (X, R, B, T, A, W)
\]

| Symbol | Meaning |
|--------|---------|
| \(X\) | Typed entities (artifacts, receipts, capabilities, epochs) |
| \(R\) | Typed relations (lineage, influence, provenance) |
| \(B\) | Boundaries (planes E/A/I/C/W; repository identity) |
| \(T\) | Permitted transformations (legal phase/epoch steps) |
| \(A\) | Delegated authority (ExecutionCapability) |
| \(W\) | Independent witness (commit-before-reveal) |

## Consequential coordinate

For operational participation:

\[
q = (e, a, t, w) \in \{0,1\}^4
\]

- \(e\) — evidence valid  
- \(a\) — authority valid  
- \(t\) — current epoch compatible  
- \(w\) — independently witnessed  

Planes locate an artifact. The four bits decide whether it may enter an operation.

## Candidate law (conjecture)

> A persistent adaptive system remains coherent under change only when consequential state transitions preserve typed boundaries, derive from valid authority, remain causally traceable, and admit verification or recovery.

This is a **falsifiable systems conjecture**, not a law of nature.

## Operations (Cortex mapping)

| Operation | Required bits (e,a,t,w) |
|-----------|-------------------------|
| retrieve | (1, ·, 1, ·) |
| adapt | (1, 1, 1, ·) |
| promote | (1, 1, 1, 1) |
| repair | (·, 1, 1, ·) |
| repair_readmit | (1, 1, 1, 1) |
| federate | (1, 1, 1, ·) |

## Diagonals

Multi-axis jumps without declared compound steps are denied. Named illegal patterns include stale authority after epoch change, witness surviving adaptive-root change, learned→evidence without reconstruction, and foreign→local authority.

## Implementation

- `cortex/constitutional_geometry.py`
- `cortex/constitutional_requirements.py`
- `cortex/constitutional_transition.py`
- `cortex/diagonal.py`
- `cortex/constitutional_path.py`
