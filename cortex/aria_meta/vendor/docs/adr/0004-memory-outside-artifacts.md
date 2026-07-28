# ADR 0004: Mutable Memory Outside Compiled Artifacts

**Status:** Accepted

Compiled memory defaults are deterministic. Live memory is stored under `.aria/state` and excluded from `.ariac`. This preserves reproducibility, privacy boundaries, and erasure without recompilation.
