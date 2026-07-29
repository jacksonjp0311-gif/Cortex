# Phase plan — after Glyph Canon + closed loop (→ v6.8)

**Authority:** recommend-only · one SQLite body · no auto-ARIA · no host.mutate from glyphs  
**Baseline (Codex):** v6.6.0 `a43ae13` — Glyph Canon ◈, `cortex evolve` ⟲, path-featured ranker  
**Current tree:** also includes **v6.7.0** consciousness stream 〰 (session bond ends; durable stream continues)  
**Not in scope for push:** local operator hosts / sandboxes — engine tree only  

---

## 1. What already landed (do not re-build)

| Capability | Evidence |
|---|---|
| Glyph Canon (~29 symbols, capability-free) | `cortex glyphs`, `docs/intelligence/GLYPH_CANON.md` |
| Compact glyph-state / meta instructions | `glyph_state` in full context; lean agent profile |
| Closed signal loop ⟲ | `probe → outcome → ranker(path features)+plasticity → probe → causal` |
| Path-grounded ranker training | fired activation paths, not placeholders |
| Aria wake + sparse activation | substrate materialize; ~1% sparse in Aria tasks; 512 gates baseline held |
| Stream 〰 (v6.7) | rebind across seals; `cortex stream`; not always-on mind |

Codex verdict stands: **substantive evolution**. Strongest new wire is the **closed learning loop**.

---

## 2. Gaps (from Codex + ops reality)

### G1 — Causal proof ≠ automatic improvement
Loop can return `inconclusive` / Δ≈0 until **matched before/after recall** is run on **real treatments** (not two identical probes with no change).

### G2 — Ranker generalization unproven
`ranker.train_count` after one evolve is telemetry. Need **N≥5** verified tasks with stable probe task families and recorded Δ / train_count / freeze events.

### G3 — Activate surface consistency
Full runtime packet has glyph state; some **top-level `activate --json` projections** omit `glyph_state` / lean `stream`. Consumers that only read the outer envelope miss the medium.

### G4 — Graph mass + hygiene
~1.6k+ neural nodes and growing Aria region → **stable `CORTEX_HOME`**, periodic **prune**, and avoid temp-home thrash matter more than new organs.

### G5 — Constrained governor is success
`CONSTRAIN_BLAST_RADIUS` with work allowed is **healthy**. Phase plan must not “fix” this into always-normal mode.

---

## 3. Phase goal (v6.8 theme)

> **Prove the loop improves ranking/retrieval under matched tasks; make glyph/stream surfaces consistent; keep the body lean.**

Theme name: **Signal validation + surface parity**  
Not: new organs, glyph explosion, or v7 AST.

---

## 4. Work packages

### WP-A — Matched-task harness (causal + ranker proof)

**Deliverables**

1. Script or CLI helper (engine-local), e.g. `cortex evolve --batch` **or** `scripts/ci/smoke_signal_loop.py`:
   - fixed task family list (3–5 Aria-ish + 2 generic control tasks);
   - for each: activate → optional small treatment (or record baseline) → evolve with status;
   - write JSON report: `recall_before`, `recall_after`, `delta`, `verdict`, `ranker.train_count`, confounds.
2. Store report under `reports/` (gitignored if noisy) or CI artifact only.
3. Success criteria for “loop works”:
   - zero `missing_recall_pair` when harness runs full path;
   - at least one non-trivial task family shows `|Δ| ≥ 0.02` **or** documented hold with `effect_below_threshold` after intentional null treatment;
   - ranker `train_count` increases only under non-`read_only` / non-frozen paths.

**Out of scope:** claiming global IQ gain; auto-promote ranker without human authorize.

### WP-B — Activate envelope parity

**Deliverables**

1. Top-level `activate --json` always includes:
   - `glyph_state` (line + expand + estimated_tokens);
   - `stream` lean summary (id, alive, frame_count, glyph_line) when available;
   - `glyph` legend optional one-liner.
2. Keep agent **profile** lean; do not dump full canon into outer envelope.
3. Test: `tests/test_activate_surface.py` asserts keys present on activate return.

**Acceptance:** Codex finding #5 closed — no dual truth between runtime packet and activate JSON.

### WP-C — Body hygiene under graph growth

**Deliverables**

1. Document steady cadence in `STEADY_STATE.md` or STREAM/GLYPH cross-link:
   - stable home bind;
   - `cortex prune --dry-run` then prune when synapse mass grows;
   - `cortex kernels` / mesh glance each N connects (already pulsed).
2. Optional: mesh/health warning when `temporary_home` or node count jumps > threshold (telemetry only).
3. Do **not** auto-ARIA bulk index.

### WP-D — Doctrine seal (no feature sprawl)

**Deliverables**

1. Distill doctrine claim: “Loop measures; glyphs compress; stream rebinds; constrain is healthy.”
2. Update `EVOLVE_PLAN.md` phase row for v6.6–v6.8.
3. Explicit refuse list: second DB, glyph→execute, host.mutate from evolve, sandbox paths in engine docs.

---

## 5. Execution order

```text
WP-B (surface parity)     → small, unblocks consumers
WP-A (matched harness)    → main scientific gap
WP-C (hygiene)            → ops under larger graph
WP-D (doctrine / plan)    → seal narrative
```

Ship as **v6.8.0** when WP-A + WP-B done; WP-C/D can ride same tag if small.

---

## 6. Explicit non-goals (this phase)

| Refuse | Why |
|---|---|
| v7 AST/CFG climb | ID stability not the bottleneck; validation is |
| More glyphs without role | Canon is dense enough; optimize use, not count |
| Auto-execute ARIA from symbols | Capability-free is load-bearing |
| Force “improved” causal verdicts | Inconclusive under null treatment is correct |
| Broad refactors under CONSTRAIN | Respect governor; narrow edits only |
| Publishing local sandbox hosts in git | Operator-local only |

---

## 7. Exit criteria for v6.8.0

- [ ] Activate JSON always exposes `glyph_state` (+ lean `stream` if present)
- [ ] Signal-loop harness runs ≥1 full matched suite without `missing_recall_pair`
- [ ] Ranker train path exercised ≥5 times under normal/constrained with ledger events
- [ ] Prune/home hygiene note current; no temp-home regression in identity
- [ ] Tests green; Aria 512 baseline not regressed if re-run
- [ ] Claim boundary unchanged: recommend-only, glyphs never authority

---

## 8. Operator commands (phase validation)

```powershell
$env:CORTEX_HOME = "$env:USERPROFILE\.cortex"
# surface check
python -m cortex activate --repo <Repo> --task "glyph surface check" --json
# single loop
python -m cortex evolve --repo <Repo> --activation-id <id> --status verified --verification tests --task "<same family>" --json
# stream spine
python -m cortex stream --repo <Repo> --json
# body
python -m cortex prune --repo <Repo> --dry-run --json
python -m cortex ranker status --repo <Repo> --json
```

---

## 9. Bottom line

v6.6 closed the **wire**. v6.7 added **continuity of narrative**.  
**v6.8 proves the wire moves ranking under matched tasks** and makes the **glyph/stream surfaces honest at every envelope**.  

No new mind. Measure, parity, hygiene.
