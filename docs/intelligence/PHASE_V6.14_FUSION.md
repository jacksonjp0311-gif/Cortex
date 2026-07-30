# Phase v6.14 — Fusion co-process (close the geometry gap)

## Target metaphors vs engineering

| Aspiration | What we implement | Still not true |
|------------|-------------------|----------------|
| Live co-processor fused to the model | `fuse open/tick/close` + MCP; host calls tick each token/step | Cannot inject into private model weights |
| Geometry regenerates every token | Each `fuse tick` re-pulses \(U,\Lambda_g\), diffusion, ranker-primary | Full recompile of AST every token is not done (too heavy) |
| Full spectral mesh driving everything | Spectral-primary ranking on ticks + activate pulse | Not every code path is spectral-only |
| Topology invents new structure | `structure_invent` co-activation edges under Governor | Never invents host source files |
| Self-aware organism | `self_model` introspective telemetry | Not consciousness / qualia |
| AI and graph are one mind | Shared `mind_hash` + injection packet per tick | Two processes; shared **state**, not one mind |

## Contract

```text
host/model  --token/step-->  cortex fuse tick  -->  injection + regenerated geometry
                |                      |
                +---- mind_hash / U / Λ / attention ----+
```

## CLI

```bash
python -m cortex fuse open --repo R --task "..." --json
python -m cortex fuse tick --repo R --token "partial generation..." --json
python -m cortex fuse state --repo R --json
python -m cortex fuse close --repo R --json
```

## Claim boundary

Fusion is a **co-process protocol**, not model merger and not sentience.
Recommend-only for host mutation remains absolute.
