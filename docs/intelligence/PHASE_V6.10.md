# Phase plan — Spectral prune & graph hygiene (→ v6.10)

**Authority:** recommend-only · one SQLite body · prune never deletes evidence  
**Baseline body (CortexTeach @ durable home, post-cadence stop):**  

| Metric | Value |
|--------|--------|
| Nodes | ~1751 |
| Synapses | ~6822 |
| weak_unused (hygiene &lt;0.12) | ~2207 (all **integrate**) |
| Default prune `min_weight=0.08` dry | **0 candidates** |
| Prune `min_weight=0.12` dry | **~1423** candidates |
| Spectral share | retain ~**68%** · integrate ~**32%** · reset ~0 |
| Ranker train_count | ~**33** (warm) |
| Stream | continuous spine · hundreds of frames |

**Theme:** Make the graph **honestly prunable**, **class-aware**, and **measurable** — not a second brain, not mass delete.

**Glyph:** ✂ prune · ≋ kernels · ⧉ mesh  

---

## 1. Problem (why this phase)

Cadence + decay **softened integrate edges** (good). Hygiene now says `prune_weak_unused_synapses`, but:

1. **Default prune floor (0.08)** uses integrate threshold `0.08×0.75=0.06` → almost nothing at the floor is selected (`would_prune=0`).
2. **Hygiene weak count** uses a flat `weight < 0.12` → reports 2207 weak, which **disagrees** with default prune.
3. Operator sees “prune!” but `cortex prune --dry-run` says **nothing to do** → trust fracture.
4. Graph is large (Aria region ~941 path nodes); without class-aware cadence, decay can **over-shift** mass to retain and leave a long tail of soft integrate edges.

This phase **harmonizes hygiene, prune, spectral kernels, and graph reporting**.

---

## 2. Goals

| ID | Goal |
|----|------|
| G1 | **Aligned telemetry:** hygiene weak ≈ prune-eligible under a named policy profile |
| G2 | **Safe prune ladder:** dry-run profiles (`safe` / `integrate_soft` / `aggressive`) with protect flags explicit |
| G3 | **Graph report:** one `cortex graph` or `hygiene --graph` surface: class counts, weight histogram, orphan multi-res nodes |
| G4 | **Surgical apply:** one measured prune pass on integrate soft edges only; retain + hierarchical never default-killed |
| G5 | **Cadence fix:** progress log every N cycles; hygiene tick uses same policy as CLI (no silent no-ops) |
| G6 | **Prove no retrieval harm:** before/after activate probe on HIGH tasks + optional harness Δ |

Non-goals: delete memories/files, auto-ARIA, v7 AST, 1000-cycle thrash, Perci dependency.

---

## 3. Work packages

### WP-A — Policy profiles (prune + hygiene)

Define named policies (code + docs):

| Profile | min_weight | protect_retain | keep_hierarchical | Intent |
|---------|------------|----------------|-------------------|--------|
| **safe** (default) | 0.08 | true | true | Current behavior; rarely prunes post-decay |
| **integrate_soft** (recommended post-cadence) | 0.12 | true | true | Cut soft integrate tail; keep retain |
| **aggressive** | 0.15–0.20 | false* | true | Lab only; requires `--authorize-aggressive` |

\* aggressive may allow non-hierarchical weak retain if misclassified — still never evidence rows.

**Deliverables**

- `prune_graph(..., policy="safe"|"integrate_soft"|...)` or CLI `--policy`
- `body_hygiene` reports `prune_policy_preview` with would_prune per profile
- Advice string only if **safe or integrate_soft** would_prune &gt; 0

### WP-B — Graph census surface

**Deliverables**

- Extend `neural_graph_state` / `hygiene` / new `cortex graph --stats`:
  - nodes by region (repo vs aria substrate)
  - synapses by `kernel_class` + relation
  - weight percentiles (p10/p50/p90)
  - weak counts **per class** at thresholds 0.08 / 0.12 / 0.15
  - orphan multi-res nodes (optional detect; prune orphans only if no synapses)
- Sample of top weakest integrate edges (path pair) for operator review

### WP-C — Measured prune apply

**Procedure (operator / automation)**

```text
1. cortex hygiene --repo R --json
2. cortex prune --repo R --policy integrate_soft --dry-run --json
3. snapshot: kernels_status + activate probe task set (HIGH)
4. cortex prune --repo R --policy integrate_soft --json   # apply
5. re-probe + optional harness 2 families
6. remember + ritual seal note
```

**Success criteria**

- would_prune applied within ±5% of dry-run
- mesh still green; no immune block induced
- HIGH domain expand still works (evidence / interconnect)
- sparse ratio not worse by &gt;2× on same tasks
- ranker not frozen

### WP-D — Cadence graph hygiene

**Deliverables**

- Progress file every 25 cycles: `logs/cadence-progress-{repo}.jsonl`
- Hygiene tick: dry-run **integrate_soft**; apply only if would_prune &gt; K (e.g. 50) and not read_only
- Cap decay frequency (already every 50); never decay retain
- Stop 1000-cycle default; document recommended `cycles=50..100` for interactive, 1000 only with progress log

### WP-E — Doctrine + phase seal

**Deliverables**

- Card or doctrine line: “Prune is class-aware; large≠unhealthy; weak integrate is post-decay normal”
- Update `EVOLVE_PLAN.md` phase row
- Tests: policy dry-run counts stable on fixture graph; hygiene advice matches policy preview

---

## 4. Execution order

```text
WP-A (policy alignment)     → unblocks operator trust
WP-B (graph census)         → see before cut
WP-C (one measured apply)   → real topology evolution
WP-D (cadence progress)     → no more silent long runs
WP-E (docs/tests)           → seal phase
```

Ship as **v6.10.0** when A+B+C done; D/E same tag if small.

---

## 5. Observed numbers to target (CortexTeach)

From live measure (post-cadence stop):

| Policy | Expected would_prune (approx) |
|--------|-------------------------------|
| safe (0.08) | 0 |
| integrate_soft (0.12) | ~1400 |
| 0.15 | ~2100 |
| 0.20 | ~2300 |

**Recommended first apply:** `integrate_soft` (~20% of edges) — cuts decay tail, keeps retain hierarchy.

Do **not** jump to 0.20 on first pass.

---

## 6. Refuse list

| Refuse | Why |
|--------|-----|
| Prune evidence memories / files | Covenant |
| Default protect_retain=false | Teaching mass loss |
| Auto-aggressive prune in cadence | Needs human authorize flag |
| Another 1000 cadence without progress log | Lost reports already happened |
| New organs while graph policy broken | Topology first |

---

## 7. Exit criteria (v6.10.0)

- [x] Hygiene advice and prune dry-run agree under named policies  
- [x] Graph census CLI/JSON available (`graph --stats`)  
- [x] One integrate_soft prune applied on durable CortexTeach  
- [x] HIGH pack enter still expands correctly after prune  
- [x] Cadence writes progress every ≤25 cycles  
- [x] Tests green; claim boundary unchanged  

---

## 8. Operator commands (phase validation)

```powershell
$env:CORTEX_HOME = "$env:USERPROFILE\.cortex"
python -m cortex hygiene --repo CortexTeach --json
python -m cortex prune --repo CortexTeach --dry-run --json
# after WP-A:
python -m cortex prune --repo CortexTeach --policy integrate_soft --dry-run --json
python -m cortex prune --repo CortexTeach --policy integrate_soft --json
python -m cortex kernels --repo CortexTeach --json
python -m cortex activate --repo CortexTeach --task "evidence falsify sparse" --json
```

---

## 9. Bottom line

**v6.10 = make the graph surgically evolvable.**  
Cadence proved the body can learn and decay; now **align cut policy with spectral classes**, **show the census**, **apply one soft integrate prune**, and **never again lose a long run without a progress trail.**

Not more cards. Not more organs. **Topology truth + safe cut.**
