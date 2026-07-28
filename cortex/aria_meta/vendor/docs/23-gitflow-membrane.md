# Gitflow Membrane alpha.11

Gitflow Membrane treats Git as a transport provider behind ARIA's operator surface.

## Default surface

Native Git stdout and stderr are buffered. Object enumeration, delta compression, transfer rates, and remote progress are hidden. A single PASS event is emitted only after commit identity verification succeeds.

Examples:

```text
◆ github.pull │ 🜂 transport │ ∿ origin/main · 5794305 │ 🜄 remote identity verified
◆ github.push │ 🜂 transport │ ∿ origin/main · a13f920 │ 🜄 remote identity verified
```

## Verification

Pull uses fetch plus a fast-forward-only merge. PASS requires local `HEAD` to equal `origin/main`.

Push uses a normal non-forced push. PASS requires `git ls-remote` to report the same SHA as local `HEAD`.

Sync performs pull and push internally but emits one final verified sync frame.

Raw Git output remains available through `-VerboseOutput` or `ARIA_VERBOSE=1`.

The membrane never force-pushes and never rewrites shared `main` history.