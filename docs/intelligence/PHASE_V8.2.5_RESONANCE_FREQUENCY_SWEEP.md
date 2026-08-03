# Phase v8.2.5 — Resonance Frequency Sweep

Status: implemented, read-only, advisory-only.

The field now evaluates a bounded set of cycles-per-frame-window against sealed Resonant Frame metrics from one latest body epoch. Cross-epoch frames are excluded so a repository transition cannot masquerade as resonance. Each typed signal is centered, transformed into a complex phase response, and combined into a response amplitude and cross-signal phase-lock score:

\[
R(f)=\frac{1}{2}\operatorname{mean}_j\left(\frac{|Z_j(f)|}{\|x_j-\bar{x}_j\|_1}\right)+\frac{1}{2}\left|\operatorname{mean}_j\frac{Z_j(f)}{|Z_j(f)|}\right|.
\]

A candidate peak requires at least 16 sealed frames, coherence ≥0.25, and a ≥0.03 gap over the next frequency. The system only recommends observing that frequency; it never changes cadence, appends samples, seals an epoch, alters retrieval, or grants authority.

Run it directly:

```bash
python -m cortex interlock resonance --repo CortexTeach --json
```

The interconnect dashboard exposes the same read-only panel as `resonance_sweep`. “No stable peak” is a valid result: the correct response is to hold cadence and collect more same-epoch frames.
