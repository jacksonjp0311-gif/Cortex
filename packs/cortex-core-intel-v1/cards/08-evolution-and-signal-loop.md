# Evolution and signal loop (taught)

## Closed loop ⟲
```text
probe(before) → outcome → ranker(path features) + plasticity → probe(after) → causal
```
CLI: `cortex evolve` · suite: `cortex harness`

## When to evolve
After **verified** work (tests green, real change) — not after null treatment.
Inconclusive / Δ≈0 under no change is **healthy honesty**.

## Ranker
Trains on fired activation paths. Monitor train_count over real tasks.
Unsafe outcomes freeze ranker. Never treats pack expand as host edit rights.

## Evolution law
Measure → prune → distill → seal. Prefer steady-state over new organs.
Packs evolve by **better cards + reinstall**, not silent self-rewrite mid-chat.
