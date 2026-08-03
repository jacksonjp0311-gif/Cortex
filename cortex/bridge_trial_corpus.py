"""Sealed 64-case corpus for v8.2.2 bridge trials.

This corpus is evaluation-only.  It must not feed ranker training, concept-route
construction, or threshold selection.  Bump the freeze id for any edit.
"""

from __future__ import annotations


BRIDGE_TRIAL_FREEZE_ID = "bridge64-v1-2026-08-02"

_SPECS = [
    ("activation", "cortex/activation.py", "assemble a bounded task packet after routing and repository verification", "finalize an activation transaction with evidence and session state"),
    ("bridge_trial", "cortex/bridge_trials.py", "paired fixed size reserve experiment using relevance geometry and novelty", "counterfactual connector candidate compared with a deterministic random arm"),
    ("measured_event", "cortex/cognitive/measured.py", "persist a signed before and after operational delta receipt", "which component records normalized changes from one cognitive cycle"),
    ("counterfactual", "cortex/cognitive/counterfactual.py", "simulate abstain evidence only and bounded adaptation without executing them", "comparison-only internal projection of alternative controller actions"),
    ("workspace", "cortex/cognitive/workspace.py", "bounded competition that broadcasts a few reliable signals across modules", "select globally available operational signals by urgency reliability and novelty"),
    ("autobiography", "cortex/cognitive/autobiography.py", "hash chained operational episodes with previous receipt lineage", "append repository events into a continuity chain without claiming personal identity"),
    ("lesion", "cortex/cognitive/lesion.py", "remove one internal subsystem and measure functional dependence", "paired ablation of prediction workspace and continuity mechanisms"),
    ("coherence", "cortex/coherence.py", "measure coupled seams across geometry ranker spectral and fusion state", "calculate the bounded system coupling score and active indicators"),
    ("constitutional_geometry", "cortex/constitutional_geometry.py", "enumerate authority evidence activation language and economics axes", "zero point coordinate rules for constitutional participation"),
    ("continuity", "cortex/continuity.py", "verify the sealed body epoch matches the living repository", "detect version schema and root hash mismatch in continuity state"),
    ("epoch", "cortex/epoch.py", "seal repository evidence adaptive and constitutional roots into an epoch", "observe whether the current source tree agrees with its body identity"),
    ("evidence_kernel", "cortex/evidence_kernel.py", "retain source grounded evidence under bounded retrieval rules", "trusted evidence substrate that outranks learned association"),
    ("fuse_proxy", "cortex/fuse_proxy.py", "stream an OpenAI compatible response while ticking geometry on deltas", "local HTTP chat completions front for the fusion co-process"),
    ("governor", "cortex/governor.py", "choose normal constrained or read only operation from memory stability", "controller that limits blast radius from confidence freshness and focus"),
    ("host_mesh", "cortex/host_mesh.py", "observe several attached repositories without merging their identities", "report per-host role coherence ranker and graph state"),
    ("info_interlock", "cortex/math_net/info_interlock.py", "measure evidence learned route and independently witnessed outcome synergy", "cohort scoped mutual information interlock with lesion telemetry"),
    ("calibration", "cortex/math_net/calibration.py", "fit shadow confidence weights from verified outcomes", "map predicted retrieval confidence to observed correctness without promotion"),
    ("info_account", "cortex/math_net/info_account.py", "account for uncertainty change per logarithmic token budget", "information expenditure and promotion score measurement"),
    ("operator", "cortex/math_net/operator.py", "assemble weighted adjacency and reverse edge operators", "matrix representation of neural synapse mass for spectral routines"),
    ("plasticity_rct", "cortex/math_net/plasticity_rct.py", "randomized controlled comparison of optional synapse updates", "opt in treatment and control arms for neural plasticity"),
    ("ratio_lattice", "cortex/math_net/ratio_lattice.py", "complete graph triangle closure and local neighborhood geometry", "calculate triadic metrics without top degree projection bias"),
    ("spectral_memory", "cortex/math_net/spectral_memory.py", "classify reset integrate and retain memory regimes from spectral state", "retention kernel pulse using graph diffusion telemetry"),
    ("uncertainty", "cortex/math_net/uncertainty.py", "single bounded uncertainty scalar consumed by control gates", "combine retrieval certificate drift and sparse evidence confidence"),
    ("memory_simplex", "cortex/memory_simplex.py", "switch between advanced retrieval and trusted evidence baseline", "fallback controller that disables adaptive ranking lanes"),
    ("ranker", "cortex/ranker/model.py", "local learned reranker with promotion rollback and frozen snapshots", "score retrieval features while preserving constitutional boundaries"),
    ("retrieval", "cortex/retrieval.py", "hybrid lexical semantic graph retrieval with evidence floors", "deduplicate paths and apply post ranking metadata to query hits"),
    ("self_sensing", "cortex/self_sensing.py", "compare current operational vector with a learned baseline residual", "classify local regime stress from measured engineering telemetry"),
    ("structure_invent", "cortex/structure_invent.py", "propose weak edges when paths cofire under explicit gates", "bounded topology invention from coactivation without authority"),
    ("interconnect", "cortex/interconnect.py", "assemble one compact mesh report across operational subsystems", "read continuity graph ranker field and bridge panels together"),
    ("emergence_log", "cortex/emergence_log.py", "append only progress history that agents inspect before work", "store threshold crossings utility measurements and directives"),
    ("pack_memory", "cortex/packs/memory.py", "route binary intelligence packs by task domain", "boost selected memory pack evidence without granting authority"),
    ("witness", "cortex/witness.py", "sealed evaluation outside the adaptive geometry", "independent receipt backed validation for promotion claims"),
]

BRIDGE_TRIAL_CORPUS = [
    {
        "id": f"bridge64_{name}_{variant}",
        "query": query,
        "expected_substrings": [path],
        "suite": "bridge64",
        "split": "sealed_bridge_holdout",
    }
    for name, path, first, second in _SPECS
    for variant, query in (("a", first), ("b", second))
]

assert len(BRIDGE_TRIAL_CORPUS) == 64


__all__ = ["BRIDGE_TRIAL_CORPUS", "BRIDGE_TRIAL_FREEZE_ID"]
