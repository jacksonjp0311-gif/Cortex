# Phase v8.2.8 — Evidence Runway (within `⟁`)

The next evolution is an evidence-first readiness layer for the informational
interlock. Earlier probes showed that Cortex could align evidence and geometry
while temporal and outcome axes remained under-observed. v8.2.8 makes that
boundary operationally explicit.

`cortex interlock status --repo <name> --json` now includes a `readiness` plan
with:

- current cohort observations, resolved outcomes, valid witnessed outcomes,
  outcome classes, and same-epoch frame count;
- remaining deficits against the 16-frame temporal window, 32 valid samples
  per task family, two outcome classes, and 128-sample overall release floor;
- per-task-family readiness and the next measurement actions.

The plan is a diagnostic, not an executor. It does not fabricate temporal
frames, mark outcomes verified, repair witnesses, alter ranking, open the
learning gate, or mutate the host repository. A zero alignment remains an
honest lack of valid E–L–O evidence, not a command to adapt.

For the current CortexTeach epoch, the runway says to collect same-epoch
frames, resolve independent outcomes, create verified outcome variation, and
grow the valid cohort before any promotion or holdout claim is possible.

## Claim boundary

The Evidence Runway reports deficits in recorded measurements. It is not
intentional communication, subjective sensing, consciousness, authority, or
permission to mutate Cortex or its host.
