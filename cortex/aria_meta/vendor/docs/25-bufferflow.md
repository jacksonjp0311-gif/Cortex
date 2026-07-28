# Bufferflow: truthful live waiting

Bufferflow is ARIA's visual contract for a live pending operation.

```text
⧖· pending   github.push ⟦∙∙∙·⧖·∙∙∙⟧ elapsed:1.8s
```

Earlier Bufferflow releases rotated through `mesh`, `transmit`, `align`, and
`verify` according to a timer. Signal Integrity Closure alpha.6.1 removes that
behavior because elapsed time is not evidence that any of those transitions
occurred.

The live contract is:

```text
operation start event
→ pending heartbeat while process.HasExited == false
→ measured completion or fracture event
```

The heartbeat:

- moves only while the underlying process remains alive;
- reports measured elapsed time;
- increments a bounded heartbeat count for the final receipt;
- makes no percentage, acceptance, convergence, or verification claim;
- freezes when the operation closes.

A producer may name a richer phase only by recording the actual transition.

## Process membrane

`Invoke-AriaBufferedProcess` owns stdout/stderr capture, the live predicate,
terminal status, measured duration, byte counts, and one typed result. It starts
a semantic event operation and projects the final receipt through Event Spine
v3. Receipt coherence names the observed exit code; it does not infer broader
semantic alignment from process success.

Raw provider output remains available only with `ARIA_VERBOSE=1` and is excluded
from persisted event data.

Motion is suppressed in CI, redirected output, reduced-motion mode,
`ARIA_NO_ANIMATION=1`, `ARIA_ANIMATION=0`, or `ARIA_MOTION=off`. Static output
retains the same pending, completion, fracture, metric, and cue identities.
