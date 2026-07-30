# Cortex Constitutional Tesseract Hypothesis v0.1

**Status:** Directed research hypothesis  
**Label:** Directed tesseract hypothesis (software state model, not physics)

## Intent

Name the four-axis coordinate \(q=(e,a,t,w)\) as a **directed tesseract hypothesis**: sixteen vertices of boolean state, edges as single-axis legal steps, faces as compound transitions, and illegal diagonals as free multi-axis jumps without internal receipts.

This is **not**:

- a claim of physical higher-dimensional structure;
- a consciousness model;
- a universal law.

It **is**:

- a finite, enumerable state space for consequential participation;
- a vocabulary for illegal composition;
- a compiler target for legal next steps.

## Vertices

All 16 bit-strings of length 4. Enumerated deterministically in Cortex via `enumerate_coordinates()`.

## Edges

Single-axis \(0 \to 1\) steps map to named operations:

| Axis | Step |
|------|------|
| evidence | VERIFY_EVIDENCE |
| authority | ISSUE_CAPABILITY |
| epoch | VERIFY_EPOCH |
| witness | COMMIT_WITNESS |

Clearing a bit (\(1 \to 0\)) requires explicit revoke/compound recovery.

## Diagonals

Hamming distance \(> 1\) without compound declaration is denied. Compound transitions must list internal steps equal to at least the Hamming distance.

## Relation to planes

```text
E Evidence     → feeds e
A Adaptation   → must not mint e or a alone
I Immunity     → repair path under a,t
C Constitutional → capability + policy under a,t
W Witness      → feeds w
```

## Claim boundary

See Cortex v7.1 claim boundary in `CHANGELOG.md` and `constitutional_geometry.CLAIM`.
