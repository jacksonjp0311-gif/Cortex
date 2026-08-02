## 7.8.1 - Truth Recovery

- Event participation masks are explicitly labeled `modeled_salience` and are ineligible for baseline learning or retrieval policy.
- Self-sensing computes residual and classification against the prior observer baseline before deciding whether the current observation may update it.
- Drift, stress, transition, unstable frames, and modeled measurements cannot contaminate the observer baseline.
- Binding Field reports `TRANSITION_REGIME` and `DRIFT_REGIME`; only a nominal observer plus a stable frame can report `VERIFIED_REGIME`.
- Activation finalization reports changed epoch roots, while new seals retain per-table adaptive digests for attributable future transitions.

## 7.8.0 - Event-Sourced Temporal Accrual

- Stable body epochs now retain their open Resonant Frame buffer across advanced activations instead of closing every activation into an isolated one-tick frame.
- Every activation observation is tied to a durable runtime event ID and admitted exactly once through a bounded cursor.
- Activation windows close when they first reach the honest `W_min=8` support threshold; fusion retains its existing transition/`W_max` cadence.
- A first observation and every real epoch transition close an atomic current-epoch boundary from the distinct activation receipt sequence; sparse sequences remain honestly `INDETERMINATE`.
- Activation output exposes `temporal_accrual` with the event ID, acceptance decision, buffer depth, close reason, and epoch-change state.
- Event identity is stored as provenance, not as an unbounded categorical feature; no temporal metric gains authority.

## 7.7.2 - Epoch-Atomic Temporal Boundary

- Advanced activation now finalizes in one explicit order: close the parent buffer, seal the final epoch, bind `QUIESCENT`, write a final-epoch boundary frame, then sample self-sensing.
- Every activation boundary receipt names the final current body epoch, including activations that legitimately reuse an unchanged epoch.
- Parent and successor samples are never combined into one temporal frame during activation finalization.
- Boundary frames remain honestly `INDETERMINATE` below `W_min`; activation does not manufacture multi-tick warmth.
- Activation output exposes the finalization order, frame epoch/currentness, and post-frame self-sensing gates for audit.
- Covenant mirror now reads the canonical ARIA materialization/efficiency surfaces while retaining compatibility with older nested packets.

## 7.7.1 - Phase-Coherent Binding Field

- Activation continuity: when an advanced activation changes the adaptive root and seals a successor body epoch, the runtime now binds `QUIESCENT` to that final epoch instead of leaving the phase on its parent.
- Warm-In closure: an explicitly authorized Warm-In can bind an ephemeral phase to the current verified body epoch without forcing another epoch seal.
- Self-sensing evidence: production `sqlite3.Row` bootstrap evidence now warms the observer correctly instead of being discarded by a mapping-access mismatch.
- Regression gates cover final-epoch phase continuity, authorized phase binding, and SQLite-backed observer warm-up.
- Historical release receipts now use minimum-version floors, so later releases continue proving earlier invariants instead of failing CI on an exact minor-version prefix.
- Governance remains unchanged: sensing and Binding Field outputs are advisory evidence, never autonomous authority or permission to mutate the host.

## 7.7.0 - Binding Field

- **Tagline:** Name the gap between local coupling and constitutional readiness.
- **Live structure:** UNBOUND + cold frames + open buffer (~11 samples) → composite field.
- **`cortex/binding_field.py`:** BINDING_GAP · BUFFER_PENDING · COLD_FIELD · VERIFIED_REGIME.
- **CLI:** `binding-field observe|report|commit` (`commit` = frame close only, no epoch seal).
- **Interconnect:** surfaces `binding_field` panel.
- **Docs:** `PHASE_V7.7_BINDING_FIELD.md` · **CI:** `release_receipt_v770.py`.

## 7.6.0 - Verified Operating Regime (Warm-In Closure)

- **Tagline:** Close the self-sensing milestone — warm baselines, replay-stable class, hashed readiness.
- **`cortex/warm_in.py`:** status · run · verify; optional authorized realign; field warm + sense updates; milestone receipt.
- **CLI:** `cortex warm-in status|run|verify` (`--i-authorize-realign`, `--rounds`, `--field-ticks`, `--sense-updates`).
- **Interconnect:** points at warm-in for regime readiness.
- **Docs:** `docs/intelligence/PHASE_V7.6_VERIFIED_OPERATING_REGIME.md`
- **CI:** `scripts/ci/release_receipt_v760.py`
- Still advisory: no host mutation, no silent seal, no authority from residual.

## 7.5.0 - Self-Sensing Field

- **Tagline:** Measure Cortex’s own regime vs verified baseline — residual is not self-authorization.
- **`cortex/self_sensing.py`:** observer state \(z_t\) (13-D), EMA \(\mu\), diagonal Mahalanobis \(r_t\), geometric-mean \(F_t\), classifications COLD|UNBOUND|NOMINAL|DRIFT|STRESSED|INDETERMINATE.
- **Hard gates:** no **NOMINAL** when epoch/phase unbound; baseline warm required.
- **CLI:** `cortex sense observe|report|trace|replay|milestone`.
- **Surfaces:** coherence `self_sensing` panel; interconnect compact panel.
- **Docs:** `docs/intelligence/PHASE_V7.5_SELF_SENSING_FIELD.md`
- **CI:** `scripts/ci/release_receipt_v750.py`
- Never host mutation, silent seal, capability grant, promote, or consciousness claims.

## 7.4.0 - Continuity Realignment

- **Tagline:** When the seal lags the living tree, realign explicitly — never silently.
- **`cortex realign diagnose|plan|apply|warm|status`:** observe-only diagnose/plan; apply seals epoch only with `--i-authorize-realign`.
- **Interconnect:** surfaces `realign` advice when `epoch_stale_or_mismatched`.
- **Optional field warm seeds** on apply (does not fake 16/16 ready).
- **Realign receipt** hashed with before/after drift panels.
- **Docs:** `docs/intelligence/PHASE_V7.4_CONTINUITY_REALIGNMENT.md`
- **CI:** `scripts/ci/release_receipt_v740.py`
- Preserves Hermetic Attach, Resonant Frames, constitutional gates, recommend-only.

## 7.3.0 - Resonant Frames

- **Public demo + holdout:** `scripts/demo_resonant_frames_public.py` (STALE_ECHO vs COHERENT, TEMP-only, `docs/demo/*`); `scripts/experiment_field_advisory_holdout.py` (N=20 advisory width); CLI warmup `baseline_frames_seen: 3/16`.
- **Temporal field layer** over fusion ticks: typed channels (K∈[6,12]), bounded frames (W≤32), lagged coordination, effective-rank differentiation, evidence–memory comparator, deterministic classification.
- **Classifications:** QUIESCENT · TRANSITION · FRAGMENTED · OVERBOUND · STALE_ECHO · COHERENT_DIFFERENTIATED · INDETERMINATE.
- **Advisory policy only** (shadow default); never authority/witness/epoch/host mutation.
- **Modules:** `field_channels`, `resonant_frame`, `field_comparator`, `field_policy`, `field_receipt`.
- **CLI:** `cortex field report|trace|latest|verify|close|baseline|calibrate|policy|cleanup`.
- **Docs:** `RESONANT_FRAME_THEORY_V0.1`, mathematics, discovery ledger, `PHASE_V7.3_RESONANT_FRAMES`.
- **Source note:** E. R. John (2001) Field Theory of Consciousness — cited/paraphrased; not vendored; non-equivalence explicit.
- Hermetic Attach, Evidence Kernel, constitutional geometry, claim receipts preserved.

## 7.2.0 - Hermetic Attach

- **`cortex attach` / `cortex-attach`:** zero-friction external-home interlock for any repository.
- **Hermetic ritual CLI:** solar-lunar cadence, living 1.2s symbol pulse (TTY), pyramidion seal, `Returned to ROOT.`
- **Isolation:** default external mode — no host `.cortex/` pollution; body under `CORTEX_HOME`/`~/.cortex`.
- **Easy paths:** uvx / pipx primary; `scripts/attach_one.sh|.ps1`; thin `js/cortex-attach` npx wrapper.
- **Docs:** `docs/ATTACH_QUICKSTART.md`; Docker isolation test `scripts/ci/docker_attach_ritual_test.sh`.
- **Windows + bash UX:** README is a single-command paste per shell (no A+B+C chain). `attach_one.ps1` / `attach_one.sh` reject placeholder paths, set `PYTHONUNBUFFERED`, fast non-TTY ritual; PS stays in-process (`& script`, not nested `powershell -File`). Re-attach auto-sets `CORTEX_ATTACH_FAST` in Python for both.
- Host remains sovereign. Ritual is interface design, not consciousness or mutation authority.

## 7.1.2 - Claim Receipts

- **Promote claim receipt:** when `evaluate_promotion` runs with store+repo, stamp a hashed claim (`claim_id`, `body_epoch_id`, `gate_bits`, axis truth panel, holdout/foreign/witness digests).
- **Verify:** recompute receipt hash + epoch still verified (observe-only).
- **CLI:** `python -m cortex claim --repo X [--json]` (`report` / `latest` / `verify`).
- Self-org surfaces `claim_receipt` from promotion gate.
- Docs: `docs/intelligence/PHASE_V7.1.2_CLAIM_RECEIPTS.md`.

## 7.1.1 - Geometry Seal

- **CI:** `release_receipt_v711.py` hard gate (no continue-on-error).
- **Axis truth sources:** MEASURED / RECEIPT_VERIFIED / OPERATOR_ASSERTED / SIMULATED / UNKNOWN; only measured+receipt satisfy live promote/repair/federate.
- **Phase binding:** BOUND / BOOTSTRAP_UNBOUND / STALE / MISMATCHED / UNKNOWN; only BOUND is constitutionally compatible.
- **Evidence refresh edge:** audited `observe → authorize → refresh E → recompute → select_path`.
- **Tests:** `test_geometry_seal.py` including foreign-repository prediction of unencoded failures.
- Docs: `PHASE_V7.1.1_GEOMETRY_SEAL.md`.

## 7.1.0 - Constitutional Geometry

- **Four-axis coordinate** \(q=(e,a,t,w)\): evidence, authority, epoch, witness.
- **Operation requirements** for retrieve/adapt/promote/repair/repair_readmit/federate.
- **Transition + diagonal** detection; compound paths require internal steps.
- **Legal path compiler** (observe-only; never mutates or issues caps).
- **observe_current_epoch / require_current_epoch** vs mutating `ensure_current_epoch`.
- **Boundaries:** promote_gate, repair readmit, federation admission.
- **CLI:** `geometry assess|path|enumerate`.
- **Research:** `docs/research/CONSTITUTIONAL_*`, `CSG_DISCOVERY_LEDGER.md`.
- **Follow-up:** `foreign_emerge` warm issues capability (ranker train no longer no-ops); operator align note `docs/intelligence/OPERATOR_ALIGN_V71.md`.
- **Research:** `docs/research/EMERGENT_MATH_AND_COMPOSITION_V0.1.md` + `docs/research/README.md`; `llms.txt` + `AGENTS.md` / `AI_INTEGRATION` pointers for GitHub agents.
- Claim: experimental four-axis model — not consciousness, not physical tesseract, not universal law.

## 7.0.0 - Resonant Continuity

- **Body Epoch:** deterministic continuity identity (evidence/adaptive/constitution roots).
- **Runtime phases:** legal phase machine bound to epoch; operation allowlists per phase.
- **Epoch-bound capabilities:** mismatch denies adaptive ops; epoch transition revokes adaptive caps.
- **Continuity snapshot:** five-plane report (`E/A/I/C/W`) + CLI `continuity` / `epoch`.
- **Interconnect expansion:** mesh_status + host-mesh carry epoch/phase; epoch_alignment (version/constitution, never merge repo epochs); `continuity --mesh` / `--with-repo` influence gate; self-org seals epoch post-pulse; promote_gate binds verified epoch.
- Preserves all v6.25.1 constitutional seals. Docs: `PHASE_V7.0_RESONANT_CONTINUITY.md`.

## 6.25.1 - Constitutional Seal

- **Capabilities:** immutable `ExecutionCapability`; operation registry; fail-closed defaults.
- **Sterile baseline activation:** controller-first; early return; `controller_audit_events` only.
- **Influence quarantine:** runtime exclusion across retrieval/training paths.
- **Transactional repair:** full SQLite backup snapshots; single-tx apply; exact rollback checks.
- **Ranker rebuild:** append-only `ranker_training_events`; deterministic replay + hash.
- **Witness chronology:** commit-before-reveal; reject snapshot/commit drift.
- Docs: PHASE_V6.25.1 + architecture seal set.

## 6.25.0 - Constitutional Immunity

- **Evidence Kernel:** separate trusted retrieval path (no adaptive machinery).
- **Controller scope:** adaptive write firewall (fail-closed under baseline).
- **Activation:** Governor/controller faults → EVIDENCE_BASELINE + blocked-op receipts.
- **Lineage / quarantine / unlearning / immunity:** full repair lifecycle with snapshot+rollback.
- **Witness:** sealed case commitments; foreign suite labeled development transfer.
- **Promote gate:** coupling = safety prerequisite only; optional witness + wound/lineage checks.
- Docs: PHASE_V6.25 + architecture/security set.

## 6.24.0 - Memory Simplex

- **EVIDENCE_BASELINE** trusted controller: no ranker/spectral/concept routes; flat budget.
- **Measure:** ablation `evidence_baseline` + `memory_simplex` lift vs advanced path.
- **Governor:** `read_only` transfers to evidence_baseline.
- **CLI:** `--evidence-baseline` / `--memory-controller` on activate.
- **Lineage prep:** invent edges stamp `ancestors` for future unlearning.
- Docs: `PHASE_V6.24_MEMORY_SIMPLEX.md`.

## 6.23.0 - Foreign Emergence

- **`foreign_emerge`:** fuse open + ticks + ranker path-token warm toward host emergent phase.
- **CLI:** `foreign-emerge`, `host-mesh --thicken` / `--thicken-foreign-only`.
- **self-org:** auto-thicken foreign host when suite measured but not emergent.
- Docs: `PHASE_V6.23_FOREIGN_EMERGENCE.md`.

## 6.22.0 - Foreign Geometry

- **Foreign IR:** concept routes for policy/storage/server/main/tests + damp cards vs `src/*.rs`.
- **Bounded prune:** `max_prune` + `protect_triads` (default); CLI `--max-prune`, `--no-protect-triads`.
- **Dual-align:** score band for neural-over-structural ratios (peak ~6×); floor when both layers healthy.
- **Coherence advice** for dark prune hygiene / dual seams.
- Docs: `PHASE_V6.22_FOREIGN_GEOMETRY.md`.

## 6.21.0 - Ratio Lattice

- **Triadic closure:** `math_net.ratio_lattice` — global \(T\), local clustering; stamped on hits as `triadic_closure`.
- **Ranker:** new feature `triadic_closure` (seed weight 0.14); pad-on-evolve.
- **Prune preview:** `triad_attention` + open-bridge edges (preview only, never auto-delete).
- **Budget partition:** schemes `fib` (default) / `phi` / `double_square` / `flat` on context packing; `--budget-scheme`; packet field `budget_partition`.
- **M9 residual pyramid:** path residual + `envelope_cell_ok` (`cortex-multiscale/1.1`).
- **Coherence history:** lean phase object (`occupied_bonds`, `phase_emergent`, bottlenecks); schema 1.2.
- **Rational ratio tables** for audit (fib, 1:2, quarter). Docs: `PHASE_V6.21_RATIO_LATTICE.md`.
- Claim boundary absolute: operators only — not sacred geometry or host authority.

## 6.20.0 - Validated utility & bottleneck action

- **Promotion gate:** holdout + foreign transfer + emergent required (`promote_gate.py`).
- **Foreign suite:** `eval-coupling --suite foreign` (PulseFlow path oracles).
- **Holdout freeze id** stamped on holdout reports.
- **Self-org:** runs foreign suite; shadow cal only if promotion allows.
- **Prune preview:** Fiedler-cut underuse bottleneck attention (dry-run only).
- **Coherence:** couple bottleneck advice; `lyapunov_drift` emergence events.
- **Ranker:** Fisher-scaled per-feature learning rates.
- **CI:** `scripts/ci/release_receipt.py`.

## 6.19.0 - Emergent math made explicit

- **Spectral:** Cheeger/Fiedler cut bottleneck, cut-crossing underuse priority, heat wavelet tops.
- **Coherence:** couple-graph percolation (cut bonds, hysteresis) + discrete Lyapunov V.
- **Multiscale:** mass conservation distortion δ.
- **Ranker:** diagonal Fisher proxy from logged examples.
- **Info account:** free-energy *proxy* as internal accounting (not FEP ideology).
- Docs: `PHASE_V6.19_EMERGENT_MATH.md`. Claim boundaries absolute; holdout for utility.

## 6.18.1 - Holdout IR tune + PulseFlow warm + README agent surface

- Concept routes + neighbor damp for `operator.py` vs spectral; `host_mesh` holdout phrases.
- README: holdout/train/host-mesh/self-org/distill as primary agent surface; topology law pointer.
- Strike-fork loop: reindex, foreign real task, holdout assess, mesh, distill.

## 6.18.0 - Boundary Consolidation

- **Self-org:** fix `returned_paths` slicing; Governor failure → `read_only`; train/holdout split (no ranker warm from holdout).
- **Eval:** suites `train` / `holdout`; promote_calibration not forced by perfect-recall ceiling.
- **Topology law:** `G_host` / `G_evidence` / `G_learned` / `G_federated` (`topology_law.py`, docs).
- **Host mesh:** persist explicit `mesh_role` metadata; heuristics are fallback only.
- **Coherence:** expose `operational_coupling_index` (engineered coupling, not validated utility).
- **Fuse proxy:** restore SQLite WAL + busy_timeout after reconnect; optional `CORTEX_FUSE_TOKEN`.
- Docs: SECURITY/README plasticity wording; `PHASE_V6.18_BOUNDARY.md`.

## 6.17.0 - Host mesh

- `host-mesh` pulse: multi-host observe + federated query boundaries.
- Roles, mean coherence, directives for cold foreign rankers.

## 6.16.x - Self-org + foreign distill

- `self-org` alignment pulse; stress suite; foreign PulseFlow loop distill.
- fuse_tick signature fix in self-org.

## 6.15.x - Measure gate + hard paraphrases

- eval-coupling ablations; concept routes; path-token IR; continuum large-graph throttle.

## 6.10.0 - Spectral prune policies + graph census

- **Policies:** `safe` | `integrate_soft` | `aggressive` (authorize required to apply aggressive).
- **CLI:** `prune --policy …`, `prune --preview`, `graph --stats` (kernel classes, weight percentiles, weak-by-class, orphans).
- **Hygiene 1.1:** `prune_preview` + advice only when a policy would actually prune.
- **Cadence:** progress JSONL every 25 cycles; hygiene uses integrate_soft when would≥50.
- Measured apply on durable body: integrate_soft cut soft integrate tail; HIGH packs still expand.
- Still recommend-only; never deletes evidence memories.

## 6.9.3 - Automated evolution cadence

- **`cortex cadence --repo R --cycles N`:** automated enter → observe → surgical inject → periodic evolve/seal/hygiene.
- Rotates HIGH-card task families; reindexes packs on expand miss; evolve every N; seal milestones; decay/prune when indicated.
- Writes report under `$CORTEX_HOME/logs/cadence-*.json`. Still recommend-only; no host.mutate.

## 6.9.2 - Grow cards · enter · distill · seal

- Core pack **v1.2**: +6 taught cards (evidence, falsification, sparse doctrine, abstain, enter-exit-seal, priority map); domain `evidence`.
- Glyph **❖** `taught_intelligence`; phrasebook `grow_seal`, `falsify_first`.
- Card priority tiers in manifest (`high` / `medium` / `lower`).
- Same portable pack install path. Still recommend-only.

## 6.9.1 - Teach enter/connect/evolve into packs

- Core pack **v1.1**: taught operator cards (teach, interconnect, evolution, agent loop) + domains interconnect/evolution.
- `teach --seed` installs `cortex-core-intel-v1`, indexes into repo memory, seals pack claims via ritual.
- Memory packet `binary-intel-packs.packet.json`; phrasebook: `enter_connect_teach`, domain_interconnect/evolution.
- Same portable CORTEX_HOME install; still recommend-only.

## 6.9.0 - Binary-intel packs ▣ (portable domain memory branch)

- **Packs:** `cortex.binary-intel-pack/1.0` — manifest + cards + CORTEXBF1 domain field.
- **CLI:** `packs list|install|verify|index|probe|status` → install under any user's `CORTEX_HOME/packs/`.
- **Memory:** cards indexed as `intelligence_pack` at `cortex-packs/<id>/…`; domain zero-in + expand into packets.
- **Agent surface:** `packet.packs` / activate root `packs` (top_domain, expand) — feels native to Cortex.
- **Shipped pack:** `packs/cortex-core-intel-v1` (knowledge, dialogue, math, geometry, memory, code, governance).
- Glyph phrases: `domain_core`, `domain_math`, `domain_geometry`, `domain_dialogue`, `domain_memory`.
- Still recommend-only; packs never host.mutate or auto-execute.

## 6.8.0 - Signal validation + ARIA phrasebook

- **Envelope parity:** `activate --json` root always includes `glyph_state`, `glyph_line`, lean `stream`, `aria_language`.
- **Phrasebook:** reusable ARIA lines (`wake_safe`, `aria_awake`, `loop_close`, `stream_rebind`, …) via `glyphs --phrasebook|--phrase`.
- **Harness ⟲:** `cortex harness --repo` runs matched activate→evolve suite; reports recall pairs, ranker train, envelope checks.
- **Hygiene ✂:** `cortex hygiene` + health.hygiene (nodes, weak synapses, temp home, advice).
- Doctrine + PHASE_V6.8 exit criteria. Still recommend-only; glyphs never execute.

## 6.7.0 - Consciousness stream 〰

- **Stream 〰:** durable episodic frame ledger; activate rebinds; consolidate seals session bond but stream continues.
- **CLI:** `cortex stream status|seal`; packet + agent profile carry lean `stream`.
- **Doctrine:** temporary cortex (⊛) vs durable stream (〰); not always-on mind.
- Glyph canon entry + ARIA continuity cues. Still recommend-only.

## 6.6.0 - Glyph Canon ◈ + closed signal loop ⟲

- **Glyph Canon:** unified ARIA-addressable registry (`cortex glyphs`); optimized set; compact lines for agent packets.
- **Meta role:** `glyph_state` + `meta_instructions` replace long prose when not blocked (token thrift).
- **Signal loop:** `cortex evolve` runs probe→outcome→ranker path-features + plasticity→probe→causal with matched pair.
- **Ranker:** trains on fired activation path features, not dummy vectors.
- **ARIA cues:** glyph canon / signal loop / meta medium wake phrases.
- Doctrine + `docs/intelligence/GLYPH_CANON.md`. Still recommend-only; glyphs never execute.

## 6.5.2 - Ops durability (stable home + honest mirror)

- **Mirror host binding:** snapshot/restore `.cortex/config.json`; external bootstrap so stress does not leave production pointed at `%TEMP%`.
- **Phase-labeled breaks:** `generic` (expect Aria dormant) vs `aria_wake` (expect active + proof evidence); claim boundary documents the distinction.
- **Evidence floor:** counts vendor substrate + `cortex/*.py` + tests (prove path), not vendor docs alone.
- **Health 1.3:** surfaces temporary home + re-verify boundary notes.
- Operator re-bind to durable `~/.cortex` is the production path. Still recommend-only.

## 6.5.1 - Operational tightening

- **Wrapper parity:** PowerShell/bash `.cortex/bin` expose `identity`, `distill`, `kernels`, `interconnect`, `immune`, `metrics`, `prune`, `organism`, `breathe`, `causal` (default budget 800).
- **Proof ranking:** under `prove_implementation`, prefer tests + `cortex/*.py` over vendor guides/cards; do not auto-prove on bare Aria wake (keeps verify heading probes green).
- **Stable home:** `identity` reports `temporary_home`; troubleshooting + `.cortex` README guide durable `CORTEX_HOME`.
- **Causal probe:** `causal probe --slot before|after` for matched recall pairs before `evaluate`.
- Docs badge/release line aligned to 6.5.1. Still recommend-only.

## 6.5.0 - Identity continuity + ARIA evidence proof

- **Identity ⌖:** `cortex identity --repo|--path` detects same-path/different-name namespaces (e.g. CortexV5CI vs CortexTeach); bootstrap warns; activate surfaces identity.
- **Evidence selection:** ARIA-active `prove_implementation` boosts substrate + `cortex/*.py`, dampens card monopoly; re-materialize+re-query when ARIA paths sparse.
- **Doctrine:** identity + evidence-proof packets/claims for teach-seed and distill.
- Integrity was already holding — this heals selection and continuity boundaries. Still recommend-only.

## 6.4.0 - Intelligence pulse at connect frequency

- **Resonate:** `lattice_resonance` scores mesh · immune · spectral · hnsw · ranker · pulse.
- **Pulse on connect:** doctrine beat every 2 passes; full `distill` seal every 7 (skipped if immune block).
- **Organism nervous.mesh** carries intel beat/intensity/brightness.
- **Interconnect / dashboard --mesh** surface last intelligence resonance.
- Intelligence rides the same frequency as connect — not a separate organ. Still recommend-only.

## 6.3.0 - Distill intelligence into the body

- **`cortex distill` / MCP `cortex_distill`:** observe mesh + kernels, fold doctrine claims, ritual-seal into durable cards.
- **Doctrine:** one-body law, clock≠memory≠decision, lean hygiene, steady-state over sprawl (see `docs/intelligence/DISTILLED.md`).
- **Packet:** `distilled-intel.packet.json` for teach-seed.
- Glyph distill ☰. Still recommend-only; observation is not authorization.

## 6.2.0 - Lattice fold · lean packets · multi-agent tokens

- **Fold:** `DATA_MODEL.md` + `ARCHITECTURE.md` lattice synced to v6.1 reality.
- **Lean agent profile:** capped evidence (800 chars), symbol-only glyphs, truncated neural/connect — lower token use.
- **Efficiency:** default activate budget **800**, config `context_budget` **900**, tighter path fan-out.
- **Mesh compact** glyph symbols only (full registry opt-out).
- **Multi-agent v6.2:** `agent mode --on|--off`; remember + MCP activate/ritual require tokens when on.
- **ARIA heal:** `lattice-heal.packet.json` + wake cues (lean packet, multi agent mode, …).
- Still recommend-only; default single-agent; no host.mutate.

## 6.1.0 - Spectral kernels · closed loops · mesh dashboard

- **Spectral memory ≋:** reset / integrate / retain kernels; ρ_g = e^{−δ_g}; Ξ spectrum on mesh.
- **Connect:** annotates synapses, `retention_by_class` each pass; clock ≠ memory ≠ decision.
- **Prune/decay:** class-aware (protect retain hierarchy; faster reset decay).
- **Closed loops:** prefetch_hit on evidence → ranker features; ranker promote/rollback/unfreeze CLI.
- **Call-graph lite:** `calls` + `dataflow_use` edges from resolves_to / symbol names.
- **Bootstrap:** kernel profile + HNSW build attempt after compile.
- **Dashboard --mesh** / `cortex kernels` / MCP `cortex_kernels`.
- Teaching packet `spectral-memory.packet.json`. Still recommend-only.

## 6.0.0 - Interconnect mesh · sealed gates · glyphic ARIA · prune

- **Interconnect ⧉:** `cortex interconnect` / MCP `cortex_interconnect` — mesh health, bottlenecks, gates.
- **Gates seal:** ritual blocks on immune `block` + optional `--contract strict`; promote hard-locks immune/ranker freeze; ranker freezes on unsafe/block/causal regressed.
- **Connect cadence:** causal micro-episode every 3 passes; weight decay every 5; prefetch precision closed on activate.
- **ARIA glyphic medium:** expanded mesh/glyph/prune/seal wake cues; progress glyphs for mesh + prune; fluency cases.
- **Bottlenecks:** path-diversity cap on packet assembly (max chunks/path).
- **Prune ✂:** `cortex prune` removes weak unused synapses; never evidence; optional decay.
- **HNSW:** incremental `insert_memory_vector` when index exists.
- **Organism:** nervous mesh + metabolism bottleneck hints.
- **Transcend-check 3.0** falsifies v6 gates. Ritual schema 2.0. Still recommend-only; one body.

## 5.0.0 - Governed local cognition substrate

Seven capabilities on one SQLite body; recommend-only preserved:

1. **Multi-resolution neural graph** — file → symbol → basic_block; contains/child_of/calls.
2. **Tiny online ranker** — verified outcomes only; Governor-gated train.
3. **Predictive prefetch** — `cortex predict` / activate `--prefetch`; never ARIA surprise-wake.
4. **Continuation contracts** — machine-checkable default/strict; constrain only.
5. **Multi-agent capability tokens** — closed scope vocab; **no host.mutate**.
6. **Deterministic HNSW** — pure-Python local index; FTS/LSH fallback.
7. **Causal outcome ledger** — improved/regressed/inconclusive; no authority.

CLI: `vectors`, `ranker`, `predict`, `contract`, `agent`, `token`, `causal`, `compile-interlink`.  
Transcend-check **2.0** falsifies v5 surfaces. Workflow bootstrap/activate/organism unchanged.

## 3.6.0 - Connect pass · metric graph · distill

- **Connect ⧉:** each activate/organism/breathe gathers multi-surface metrics into one pass vector.
- **Metric graph grows:** `settings.metric_graph:{repo}` expands path co-activations, immune codes, rolling averages every connect.
- **Distill into substrate:** high-signal lessons `remember` into episodic memory (same SQLite body).
- **Ledger:** `connect_pass` neural_ledger events; richer organism_pulse payload.
- **CLI/MCP:** `cortex metrics`, `cortex_metrics`.
- **ARIA expand:** wake cues for connect/metric/immune/organism; memory packets `connect` + `immune`; fluency cases.
- **CI:** `scripts/ci/smoke_connect_metrics.py`. Still recommend-only; still self-host only.

## 3.5.4 - Unmissable packet block

- **Profiles:** every agent/debug/minimal packet carries top-level `block` + `immune_action` + `read_first`.
- **Activate:** same top-level immune fields on the activation envelope.
- **Doctor --repo:** surfaces immune inspect when a repository is named.
- Still recommend-only; still self-host only.

## 3.5.3 - Immune gate surface

- **`cortex immune` / MCP `cortex_immune`:** read-first block + immune_action for one repo.
- **Transcend-check 1.1:** falsifies STOP / reverify / proceed immune codes.
- **CI (this repo only):** `scripts/ci/smoke_immune_gate.py`.
- Progress glyph `immune_gate` (⚠ label only). Still recommend-only; still no outside repos.

## 3.5.2 - Adherence + CI intelligence gates

- **Immune action:** `control_error.block` + `immune_action` (STOP codes agents cannot miss).
- **Organism/protocol:** carry immune_action into living state and agent_protocol.state.
- **CI (this repo only):** teach-seed smoke + retrieval path-recall gate.
- **OPERATOR.md:** single forward path for self-host use.
- Still no outside-repo scanning; still recommend-only.

## 3.5.1 - Teach the body (ARIA memory packets)

- **ARIA memory packets:** `examples/memory-packets/*.packet.json` + `.aria` teaching mass.
- **`cortex teach --seed`:** distills packet claims into durable Discovery Cards via ritual.
- **Interconnect doctrine:** `docs/intelligence/INTERCONNECT.md` indexed teaching mass.
- Retrieval boost for intelligence docs, memory packets, and discovery cards on teach/organism tasks.
- Still never executes ARIA; memory-only write to Cortex body.

## 3.5.0 - Living organism (forward only)

- **Mid-session life:** remember continues the organism pulse (diastole); consolidate seals.
- **Breathe ∽:** packet-fast rebind without full re-assimilate (`cortex breathe`, MCP `cortex_breathe`).
- **Phases:** systole → diastole → breathe → sealed; pulse chain persists across the session.
- Active session stores last organism pulse; ledger records every beat.
- Still not consciousness; still no mutation authority; still one substrate.

## 3.4.0 - Organism interlink (⊛)

- **Session co-process:** agent and Cortex share one living `organism` state per
  activation — identity, nervous, immune, metabolism, memory, intention,
  conscience, reflexes, pulse chain.
- **Not consciousness:** separable bond; host authority remains; no mutation grant.
- **CLI/MCP:** `cortex organism`, MCP `cortex_organism`.
- **Ledger:** organism pulses append to neural ledger; prior pulse chains.
- **Packet:** instructions step 0 is the organism bond; profiles carry organism.
- **Docs:** `docs/ORGANISM.md`. Glyph ⊛ is capability-free.

## 3.3.0 - Rapid progress (P0–P6)

- **P0 ⟡ transcend-check:** falsifies protocol, red modes, ritual, fluency, mirror glow.
- **P1 ▣ packet profiles:** `agent` | `debug` | `minimal` via `--profile`.
- **P2 ⚠ control_error:** single error vector agents read first; must_reverify coupling.
- **P3 ⌖ retrieval corpus:** path-recall eval (`cortex evaluate --mode retrieval`).
- **P4 ⟳ ritual idempotency:** remember de-dupe; consolidate statuses; block on control error.
- **P5 Δ surprise:** incremental reindex ratio on activate refresh.
- **P6 ☰ teach + doctor:** `cortex teach`; health exposes control_error + glyph map.
- ARIA progress glyphs (capability-free labels only).
- Self-host only unless operator names a path.

## 3.2.3 - Transcend (packet-first agent surfaces)

- **One language every door:** `agent_protocol` + `instructions` on activate,
  cortex-context/1.1, nexus packets, MCP activate/context/ritual.
- **Forced red modes:** `read_only` / `constrained` prefix hard STOP rules and
  machine-checkable `allowed_actions` / `hard_stops`.
- **MCP:** `cortex_activate`, `cortex_ritual`; refuse text on every tool.
- **Wrappers:** `ritual` in PowerShell/Bash integration templates.
- **Teaching:** `docs/TRANSCEND.md` — run from the packet alone.
- No new organs, no second DB, no auto-ARIA.

## 3.2.2 - Bright Point

- **Freeze:** `docs/BRIGHT_POINT.md` names the aligned release; self-host only contact.
- **Deepen packet:** `instructions` + machine-readable `agent_protocol` (steps, state, refuse).
- **Session ritual:** `cortex ritual` closes activate → remember → consolidate on one substrate.
- **Refuse:** no new regions, second DBs, auto-ARIA, glow-chasing, unsolicited host scans.
- Tag: `v3.2.2`.

## 3.2.1 - Contact Resonance

- **Tuning fork:** `cortex contact` runs mirror + fluency + foreign hosts and
  reports multi-string `resonance` intensity (economics, evidence, geometry,
  fluency, contact, timing) with brightness levels ember→steady→glow→bright.
- **Expanded contact matrix:** go + mixed polyglot hosts (5 foreign surfaces).
- **Mirror 1.1:** harmonic resonance field; points to contact for full bright.
- Packet geometry carries a `resonance_hint` (preservation/adjacency balance).

## 3.2.0 - Aligned Geometry

- **Covenant freeze:** `docs/COVENANT.md` locks five interlock axes (authority,
  evidence, activation, language, economics) as release constitution.
- **Steady-state discipline:** `docs/STEADY_STATE.md` + CONTRIBUTING vocabulary
  freeze; new organs only as forced tension reduction.
- **Geometry packet surface:** context packets expose `geometry` zero-point map.
- **ARIA evidence floor:** awake substrate contributes purpose-aligned evidence
  (≥2 paths) after materialization.
- **Probe quarantine test:** verify headings that mention ARIA cannot erase
  deferred bulk.
- **Fluency corpus ≥40** with zero false/missed wakes (adversarial dormant set).
- **Foreign host matrix:** python / node / docs synthetic hosts must pass organ
  gates (`benchmarks/foreign_host_matrix.py`, CI).
- **Deferred vs eager benchmark:** committed work-proxy comparison artifacts.
- **Dashboard 1.1:** covenant axes + deferred ARIA remaining counters.
- **CI:** fluency evaluation + foreign host matrix gates.
- Version alignment: package `3.2.0`.

## 3.1.0 - Constitutional Homeostasis

- Coherence mirror (`cortex mirror`): stress deferred economics, fluency gates,
  packet surfaces, and authority invariants; reports `glow` / `glow_intensity`.
- Fixed probe-side ARIA materialization: certificate retrieval no longer wakes
  and eagerly indexes the full language substrate when README headings mention
  ARIA. Materialization is intentional (activation / CLI query only).
- Context packets expose `aria_materialization` and efficiency substrate
  counters so agents can see wake economics.
- Bootstrap-tiered ARIA substrate indexing: inventory always, fully index
  anchors, defer bulk language files until ARIA-active materialization, with
  explicit work-proxy savings telemetry.
- Hardened ARIA wake classification against false friends (multi-token core
  cues; single-token learned cues rejected except `aria`) and expanded the
  fluency regression corpus.
- Added deliberate ARIA vendor bump scripts
  (`scripts/powershell/Bump-AriaSnapshot.ps1`,
  `scripts/bash/bump-aria-snapshot.sh`) so language snapshots are not mixed
  ad-hoc into Cortex core edits.
- Evolved the runtime to GCMT v1.5 with separate uncertainty/integrity failure
  geometry and a shadow-mode constitutional potential.
- Added a measurable harmonic balance between context preservation and adjacent
  conceptualization.
- Added authority-monotonic promotion with content-addressed external grant
  verification for scope growth.
- Added reversibility-weighted promotion requirements and staged recovery
  verification before rollback commits.
- Evolved continuation packets to `cortex-continuation/1.1` and added local
  authority rebinding for imported packets.
- Added the `cortex constitutional` and `cortex continuation-rebind` surfaces.
- Added five verified, capability-free ARIA function glyphs: `⋈`, `≋`, `⌁`,
  `↧`, and `↶`.
- Kept constitutional potential observational: hard constitutional violations
  remain non-compensable and host/human authority remains controlling.

## 3.0.0 - Governed Continuation Memory

- Integrated James Paul Jackson's Governed Continuation Memory Theory (GCMT v1.0)
  as an executable, non-biological software architecture.
- Added `cortex-continuation/1.0` packets with origin, operational state,
  evidence, canonical state, drift, wounds, authority, verification, receipts,
  expiry, and re-anchoring conditions.
- Added authorized Cortex canonical-memory promotion with evidence and
  verification locks, hash-chained receipts, and rollback.
- Added selective lifecycle decay of learned weight deviation toward structural
  priors without deleting source evidence or graph topology.
- Added repository-native base-versus-learned replay evaluation, boundary-
  preserving federation, SQLite vector buckets, a read-oriented MCP server, and
  a compact dashboard.
- Preserved the authority boundary: no learning, continuation, federation, or
  agent-access surface authorizes repository mutation.
- Internalized the complete Apache-2.0 ARIA snapshot as Cortex's
  manifest-verified native semantic language with no external repository
  dependency.
- Added the `internal_aria_substrate` neural region: always known,
  dormant-by-default for unrelated work, and deterministically activated by
  ARIA semantic, continuity, coordination, consent, capability, and governance
  signals.
- Hardened bootstrap retrieval probes against ambiguous duplicate symbol names
  and accepted exact heading evidence when a specialized document correctly
  outranks the README.
- Added typed native-ARIA runtime purposes, an inspectable bounded cue profile,
  human-reviewed cue admission through verified outcomes, confidence-only
  adaptation, and deterministic dormant fallback.
- Added a 20-case ARIA fluency corpus measuring false wakes, missed wakes, and
  typed-purpose assignment.

## 2.0.0 — Outcome-Grounded Repository Intelligence

- Made neural activation observational: association weights no longer change merely because paths co-activate.
- Added `cortex outcome` for explicit verified, helpful, irrelevant, failed, and unsafe outcome recording.
- Added bounded verification-weighted credit assignment, replay gates, immutable outcome ledger events, and before/after graph hashes.
- Added outcome and evidence-credit records to Cortex's single SQLite substrate.
- Added the agent-neutral `cortex-context/1.0` protocol via `cortex protocol`.
- Preserved the authority boundary: current source, tests, governance, and human authorization outrank learned associations.

## 1.3.1 — Trust-State Closure

- Activation, context, Governor, and health now consume the same current certificate.
- Current sessions are created after trust evaluation, preventing a new session from inflating continuity.
- Semantic scan configuration now controls retrieval candidate limits.
- Added an explicit Phoenix privacy-boundary policy; no Phoenix adapter is enabled.

## 1.3.0

- Added bounded self-host validation: Cortex can clone itself as an outer host, run a nested cloned engine, and verify the engine is excluded from host assimilation.
- Added full lifecycle before/after benchmark support for host-engine and nested-engine bootstrapping and activation.
- Added lane-relevance pruning with a bounded fallback, so uncertain routes cannot silently produce empty context packets.
- Added a polished README hero and verification, routing, local-first, and authority badges.

## 1.2.0

- Added the root-level deterministic Thalamus request-routing package, including intent classification, memory-lane budgeting, and auditable inhibitory evidence gating.
- Routed normal activation, public query, and neural-interlink CLI flows through Thalamus without changing Cortex's authority boundary.
- Blocked Git telemetry when the requested target is only nested within an ancestor worktree.
- Replaced the Windows-incompatible Bash-wrapper test with platform-specific wrapper execution and added Thalamus and telemetry-boundary coverage.

## 1.1.0 — 2026-07-11

- Integrated the standalone Neuron concepts directly into Cortex as `cortex.neuron`.
- Preserved Cortex as the sole repository-memory, episodic-memory, consolidation, and authority substrate.
- Added deterministic sparse spreading activation over existing repository relationships.
- Added bounded Hebbian association strengthening without autonomous topology rewriting.
- Added hash-chained neural event replay in the same SQLite database.
- Added environment learning for languages, manifests, ecosystems, frameworks, commands, entrypoints, CI, and runtime capabilities.
- Added neural support-path expansion to bounded context packets.
- Added environment and neural interlink sections to NexusGate packets.
- Added portable one-command PowerShell and Bash installation/bootstrap/verification/activation flows.
- Added automatic exclusion when the Cortex engine folder is dropped inside a host repository.
- Bound generated repository wrappers to the bootstrap-recorded Cortex home and Python engine so inherited environment variables cannot silently redirect repository memory or execution.
- Expanded the suite from 10 to 17 tests while retaining all original compatibility tests.

## 1.0.1 — 2026-07-11

- Excluded generated repository-local Cortex launcher scripts from assimilated memory to reduce retrieval noise.
- Revalidated CLI bootstrap, repository-local Bash activation, compile checks, and the 10-test integration suite.

## 1.0.0 — 2026-07-11

- Rebuilt Cortex around verified repository assimilation.
- Added repository-local agent integration and portable context packets.
- Added file inventory, unsupported-surface reporting, incremental indexing, and manifest hashes.
- Added semantic, structural, temporal, and episodic memory layers.
- Added Python and multi-language relationship extraction.
- Added Git commit, churn, and co-change telemetry.
- Added retrieval probes and bootstrap certificates.
- Added automatic activation refresh and Governor read-only fallback.
