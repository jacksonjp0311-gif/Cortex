# Phase v6.17 — Host mesh (one body, many hosts)

**Glyph:** ⧉⬡  

The “whoa” moment made explicit: Cortex already attaches many repositories into  
`~/.cortex/cortex.db`. Host mesh **observes** them as a mesh without merging  
identity or authority.

## Command

```bash
python -m cortex host-mesh --primary CortexTeach --json
python -m cortex host-mesh --primary CortexTeach --query "governor policy" --json
python -m cortex federated-query "governor policy" --json
```

## What you get

| Field | Meaning |
|-------|---------|
| `hosts[]` | Per-repo path, role, memories, synapses, coherence, ranker trains |
| `role` | durable_body · engine_tree · sandbox · foreign_host · … |
| `mesh_mean_coherence` | Average coh across measurable hosts |
| `directives` / `next` | Who to warm, what’s missing, hold boundaries |
| `federated_query` | Optional cross-repo hits with `boundary.repository` |

## Roles

| Role | Example |
|------|---------|
| durable_body | CortexTeach |
| engine_tree / engine_alias | Cortex (same Desktop tree) |
| foreign_host | PulseFlow |
| sandbox | CortexSandbox |

## Non-goals

- Not merging repos into one authority  
- Not host source mutation  
- Not consciousness  
- Not silent continuum on large graphs  

## Evolution path

1. Mesh observe → see cold rankers / non-emergent foreign  
2. Real task loops on cold foreign hosts  
3. Distill + self-org on durable body  
4. Raise difficulty only after foreign gradient exists  
