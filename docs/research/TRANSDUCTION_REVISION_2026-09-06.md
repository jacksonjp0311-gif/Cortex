# Transduction revision and canonical navigation

Reviewed baseline: `ad29b81a2b961294368fa795998fefd1134a4b5b`.
Product remains `10.0.0a39`. No model calls; no shadow organization activation.

Committed runtime revision: `6f134f15a88123b690094daa642f2aee5a5a5c8f`.
[Committed-source control check](../../benchmarks/results/gso_transduction_revision_committed_2026-09-06.json)
reproduced **16/16**. This is the same finite panel, not independent replication.

## Technical delta

The [original audit](GOVERNED_SELF_ORGANIZATION.md) is unchanged. New compilations
use `cortex-edit-intent-compilation/2.0`: fields must be strings, JSON must be an
object, and missing terminal newlines are represented by Git's explicit marker.
The version-1 reconstruction path preserves historical compiler identities; it
does not silently reinterpret them using the new algorithm.

Isolated verification now emits `cortex-coding-patch-verification/1.1`. It hashes
the applied **target files** before verification and compares them after each
step, stopping on mutation. Evaluator mutation returns HELD with typed attribution
`EVALUATOR_MUTATED_CANDIDATE`. Strict whitespace checking and exact byte transport
remain enabled. This is target nonmutation checking, not whole-OS attestation or
protection against a malicious evaluator that mutates and restores bytes mid-step.

[New finite control audit](../../benchmarks/results/gso_transduction_revision_2026-09-06.json)
is separate from the prior 13/16 artifact and from the historical live 5/8 cohort.
The same controls are regression checks, not independent samples. No fresh live
accuracy, semantic gain or cumulative organization follows.

Executed focused verification: **73 tests passed in 61.74s**, covering navigation,
strict compiler/legacy reconstruction, transduction, patch transport, isolated
workspace/source improvement, instrument and cohort gates. The new local panel
met **16/16 expectations**. No full repository suite or new live model trial ran.
Ruff, targeted compileall and diff checks passed. Navigation rendering assumptions
are checked structurally (GitHub-safe table/links/images), not by a live GitHub
pixel-render test.

## Remaining gate

Complete transduction assurance remains HELD. Structured-screen reconstruction
does not yet fully bind reconstructed compiler output to applied-before-evaluator
artifacts. Raw observation text is bounded/lossy; execution-environment trust and
evaluator scope remain declared assumptions. Existing read-only historical path
views therefore remain conservative. No new model experiment is commissioned.

Next: versioned compiler-to-observation binding and frozen complete-path controls.
Only after that comes a shadow organization kernel, then contradiction/homeostasis,
then a matched retention experiment. Do not skip to an effect study.

## Repository information architecture

[Human hub](../README.md), [system map](../SYSTEM_MAP.md), [status](../STATUS.md),
[agent start](../AGENT_START.md) and [knowledge map](../CORTEX_KNOWLEDGE_MAP.json)
are synchronized views, not additional runtime memory. The knowledge map links
12 concepts and classifies existing documents; missing empirical links remain
explicit. Scope inferred from a path is labeled as such, not claimed content review.

The entire former README is preserved, with its original Git blob checked by the
docs checker. [Migration inventory](../DOCUMENTATION_MIGRATION.md) records unique
sections and routing decisions. Images and historical phase/evidence files stay
in place. The managed AGENTS.md block remains untouched.

## Epistemic topology

Hypothesis: preserving evidence without preserving canonical relationships can
still produce wrong context. The repository map reduces ambiguity about which
source owns current status versus historical interpretation. This is navigational
structure, not measured improvement in model cognition.

Future navigation fidelity: `N_f = correct canonical retrievals / tested tasks`.
This pass performs scripted entry/edge checks and a three-reader walkthrough;
it does not estimate population navigation accuracy or organizational heredity.
