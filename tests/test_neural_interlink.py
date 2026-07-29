from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.aria_meta import (
    bundle_identity,
    bundle_root,
    classify_aria_task,
    load_aria_cue_profile,
    verify_bundle,
)
from cortex.aria_meta.evaluation import evaluate_aria_corpus, load_aria_corpus
from cortex.config import ensure_home, load_repo_config
from cortex.context import build_context, nexus_packet
from cortex.governor import Governor
from cortex.models import Hit
from cortex.neuron import activate_interlink
from cortex.learning import record_outcome
from cortex.retrieval import query
from cortex.store import Store


class CortexNeuralInterlinkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.home = ensure_home(self.base / "home")
        self.repo = self.base / "agent-repo"
        self.repo.mkdir()
        (self.repo / "README.md").write_text(
            "# Agent Repository\n\n## Architecture\n\nThe planner calls the memory bridge.\n",
            encoding="utf-8",
        )
        (self.repo / "planner.py").write_text(
            "from memory_bridge import retrieve\n\n"
            "def plan(task: str) -> str:\n"
            "    return retrieve(task)\n",
            encoding="utf-8",
        )
        (self.repo / "memory_bridge.py").write_text(
            "def retrieve(task: str) -> str:\n"
            "    return f'memory:{task}'\n",
            encoding="utf-8",
        )
        tests = self.repo / "tests"
        tests.mkdir()
        (tests / "test_planner.py").write_text(
            "from planner import plan\n\n"
            "def test_plan():\n"
            "    assert plan('x') == 'memory:x'\n",
            encoding="utf-8",
        )
        (self.repo / "pyproject.toml").write_text(
            "[project]\nname='agent-repo'\nversion='0.1.0'\n"
            "dependencies=['pytest>=8']\n\n"
            "[project.scripts]\nagent-run='planner:plan'\n",
            encoding="utf-8",
        )
        self.store = Store(self.home / "cortex.db")
        self.bootstrap = bootstrap_repository(
            self.home, self.store, self.repo, "AgentRepo"
        )

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_bootstrap_learns_environment_and_compiles_single_substrate(self) -> None:
        environment = self.bootstrap["environment"]
        neural = self.bootstrap["neural_interlink"]
        self.assertIn("python", environment["ecosystems"])
        self.assertTrue(any(item["name"] == "python" for item in environment["inventory"]["languages"]))
        self.assertGreaterEqual(neural["nodes"], 5)
        self.assertGreaterEqual(neural["synapses"], 2)
        self.assertEqual(neural["node_coverage"], 1.0)
        self.assertTrue(neural["ledger_valid"])
        self.assertTrue((self.repo / ".cortex" / "runtime" / "environment_latest.json").exists())
        self.assertFalse((self.home / "neuron.db").exists())
        self.assertTrue(environment["meta_language"]["available"])
        self.assertEqual(
            environment["meta_language"]["cortex_implementation_language"], "python"
        )
        self.assertEqual(
            environment["meta_language"]["source_kind"], "bundled_internal"
        )
        self.assertEqual(
            environment["meta_language"]["role"], "native_semantic_language"
        )
        self.assertEqual(
            environment["meta_language"]["knowledge_relationship"],
            "native_internal_language",
        )
        self.assertTrue(environment["meta_language"]["bundle"]["valid"])

    def test_internal_aria_bundle_is_self_contained_and_manifest_valid(self) -> None:
        identity = bundle_identity()
        verification = verify_bundle()
        self.assertEqual(identity["label"], "INTERNAL ARIA META-LANGUAGE")
        self.assertEqual(identity["role"], "native_semantic_language")
        self.assertEqual(identity["neural_region"], "internal_aria_substrate")
        self.assertFalse(identity["external_runtime_dependency"])
        self.assertTrue((bundle_root() / "ARIA-RUNTIME.json").is_file())
        self.assertTrue((bundle_root() / "ARIA-CONNECT.json").is_file())
        self.assertTrue(verification["valid"], verification)
        self.assertGreaterEqual(verification["checked_files"], 297)

    def test_native_aria_region_is_known_but_task_gated(self) -> None:
        dormant = classify_aria_task("Fix the Python retrieval implementation")
        false_friend = classify_aria_task("Rename a Python variable")
        glyph_false_friend = classify_aria_task("Replace the toolbar glyph icon asset")
        active = classify_aria_task(
            "Use ARIA semantic replay for a governed session handoff"
        )
        self.assertTrue(dormant["known"])
        self.assertEqual(dormant["mode"], "dormant")
        self.assertEqual(false_friend["mode"], "dormant")
        self.assertEqual(glyph_false_friend["mode"], "dormant")
        self.assertEqual(active["mode"], "active")
        self.assertIn("aria", active["matched_signals"])
        self.assertEqual(
            active["purposes"], ["language", "continuity"]
        )
        self.assertEqual(active["decision_rule"], "immutable_core_match")
        self.assertFalse(active["automatic_execution"])

    def test_aria_fluency_corpus_has_no_false_or_missed_wakes(self) -> None:
        corpus = (
            Path(__file__).resolve().parents[1]
            / "benchmarks"
            / "corpora"
            / "aria_fluency.json"
        )
        result = evaluate_aria_corpus(load_aria_corpus(corpus))
        self.assertGreaterEqual(result["cases"], 30)
        self.assertEqual(result["false_wakes"], 0, result)
        self.assertEqual(result["missed_wakes"], 0, result)
        self.assertEqual(result["purpose_misses"], 0, result)

    def test_bootstrap_defers_non_anchor_aria_substrate(self) -> None:
        native = self.repo / "cortex" / "aria_meta" / "vendor"
        (native / "docs").mkdir(parents=True)
        (native / "grammar").mkdir(parents=True, exist_ok=True)
        (native / "ARIA-RUNTIME.json").write_text(
            json.dumps({"schema": "aria-runtime", "version": "test"}),
            encoding="utf-8",
        )
        (native / "ARIA-CONNECT.json").write_text(
            json.dumps({"schema": "aria-connect", "version": "test"}),
            encoding="utf-8",
        )
        (native / "README.md").write_text("# ARIA\n", encoding="utf-8")
        (native / "grammar" / "semantic-cues.json").write_text(
            json.dumps({"format": "test", "cues": []}),
            encoding="utf-8",
        )
        deep = native / "docs" / "semantic-replay-handoff.md"
        deep.write_text(
            "# ARIA\n\nSemantic replay and cooperative mesh session handoff.\n",
            encoding="utf-8",
        )
        result = bootstrap_repository(
            self.home, self.store, self.repo, "AgentRepo", force=True
        )
        aria = result["index"]["aria_substrate"]
        self.assertEqual(aria["indexing_mode"], "deferred")
        self.assertGreaterEqual(aria["deferred_files"], 1)
        self.assertGreaterEqual(aria["anchors_indexed"], 1)
        self.assertGreater(aria["work_proxy"]["estimated_bootstrap_savings_ratio"], 0.0)
        deep_rel = "cortex/aria_meta/vendor/docs/semantic-replay-handoff.md"
        row = self.store.file("AgentRepo", deep_rel)
        self.assertEqual(row["status"], "substrate_deferred")
        # Certificate still verifies with deferred bulk.
        self.assertEqual(result["certificate"]["status"], "verified")
        self.assertEqual(
            result["certificate"]["coverage"]["deferred_substrate_count"],
            aria["deferred_files"],
        )
        # Wake materializes deferred evidence into searchable memory.
        hits = query(
            self.store,
            "AgentRepo",
            "Use ARIA semantic replay for cooperative mesh session handoff",
            limit=24,
        )
        self.assertIn(deep_rel, {hit.path for hit in hits})
        materialized = self.store.file("AgentRepo", deep_rel)
        self.assertEqual(materialized["status"], "indexed")

    def test_verified_outcome_admits_and_tunes_bounded_aria_cue(self) -> None:
        task = "Use ARIA to define a mother tongue continuity boundary"
        packet = activate_interlink(
            self.store,
            "AgentRepo",
            task,
            query(self.store, "AgentRepo", task, limit=12),
            plasticity_enabled=False,
            governance_mode="normal",
        )
        admitted = record_outcome(
            self.store,
            "AgentRepo",
            packet.activation_id,
            status="verified",
            verification_type="human-review",
            verification_payload={
                "aria_cue_reviewed": True,
                "aria_cue_proposals": [
                    {"phrase": "mother tongue", "purpose": "language"}
                ],
            },
            governance_mode="normal",
        )
        cue_learning = admitted["aria_cue_learning"]
        self.assertFalse(cue_learning["authority_changed"])
        self.assertEqual(cue_learning["updates"][0]["action"], "cue_admitted")
        profile = load_aria_cue_profile(self.store, "AgentRepo")
        learned = classify_aria_task(
            "Use the mother tongue boundary", profile["cues"]
        )
        self.assertEqual(learned["mode"], "active")
        self.assertEqual(learned["purposes"], ["language"])
        self.assertEqual(
            learned["decision_rule"],
            "verified_learned_cue_at_or_above_threshold",
        )

        second_task = "Use the mother tongue boundary"
        second = activate_interlink(
            self.store,
            "AgentRepo",
            second_task,
            query(self.store, "AgentRepo", second_task, limit=12),
            plasticity_enabled=False,
            governance_mode="normal",
        )
        tuned = record_outcome(
            self.store,
            "AgentRepo",
            second.activation_id,
            status="irrelevant",
            verification_type="human-review",
            governance_mode="normal",
        )
        self.assertEqual(
            tuned["aria_cue_learning"]["updates"][0]["action"],
            "confidence_adjusted",
        )
        profile = load_aria_cue_profile(self.store, "AgentRepo")
        self.assertLess(
            profile["cues"][0]["confidence"], profile["threshold"]
        )
        self.assertEqual(
            classify_aria_task(
                "Use the mother tongue boundary", profile["cues"]
            )["mode"],
            "dormant",
        )

    def test_internal_aria_evidence_is_dormant_until_semantically_requested(self) -> None:
        native = self.repo / "cortex" / "aria_meta" / "vendor" / "docs"
        native.mkdir(parents=True)
        native_path = native / "semantic-replay-handoff.md"
        native_path.write_text(
            "# ARIA\n\nSemantic replay and cooperative mesh govern session handoff.\n",
            encoding="utf-8",
        )
        (native / "glyph-memory.md").write_text(
            "# Glyph memory\n\nSymbolic rendering semantics.\n",
            encoding="utf-8",
        )
        bootstrap_repository(
            self.home, self.store, self.repo, "AgentRepo", force=True
        )
        relative = "cortex/aria_meta/vendor/docs/semantic-replay-handoff.md"
        node = next(
            row
            for row in self.store.neural_nodes("AgentRepo")
            if row["path"] == relative
        )
        metadata = json.loads(node["metadata"])
        self.assertEqual(metadata["neural_region"], "internal_aria_substrate")
        self.assertTrue(metadata["dormant_by_default"])

        generic_hits = query(
            self.store, "AgentRepo", "Fix the Python planner bridge", limit=24
        )
        self.assertNotIn(relative, {hit.path for hit in generic_hits})
        generic = activate_interlink(
            self.store,
            "AgentRepo",
            "Fix the Python planner bridge",
            generic_hits,
            plasticity_enabled=False,
        )
        generic_aria = generic.metrics["aria_substrate"]
        self.assertEqual(generic_aria["mode"], "dormant")
        self.assertGreaterEqual(generic_aria["total_nodes"], 1)
        self.assertEqual(generic_aria["eligible_nodes"], 0)
        self.assertEqual(generic_aria["considered_nodes"], 0)

        aria_hits = query(
            self.store,
            "AgentRepo",
            "Use ARIA semantic replay for cooperative mesh session handoff",
            limit=24,
        )
        self.assertIn(relative, {hit.path for hit in aria_hits})
        awakened = activate_interlink(
            self.store,
            "AgentRepo",
            "Use ARIA semantic replay for cooperative mesh session handoff",
            aria_hits,
            plasticity_enabled=False,
        )
        awakened_aria = awakened.metrics["aria_substrate"]
        self.assertEqual(awakened_aria["mode"], "active")
        self.assertGreaterEqual(awakened_aria["eligible_nodes"], 1)
        self.assertLess(
            awakened_aria["eligible_nodes"], awakened_aria["total_nodes"]
        )
        self.assertGreaterEqual(awakened_aria["considered_nodes"], 1)

    def test_aria_is_detected_as_meta_language_without_replacing_python(self) -> None:
        (self.repo / "ARIA-RUNTIME.json").write_text(
            json.dumps(
                {
                    "schema": "aria.runtime/1",
                    "release": "0.1.0-alpha.14",
                    "languageEvolution": "cooperative-agent-mesh-alpha.17",
                    "status": "experimental",
                    "repository": {"canonicalCli": "aria.cmd"},
                }
            ),
            encoding="utf-8",
        )
        (self.repo / "ARIA-CONNECT.json").write_text(
            json.dumps(
                {
                    "schema": "aria.agent-connection/1",
                    "protocol": "semantic-sync/1",
                    "commands": {
                        "handshake": "./aria.cmd handshake --json",
                        "health": "./aria.cmd doctor -Strict",
                    },
                    "continuity": [
                        {
                            "artifact": "aria.cooperative-mesh/1",
                            "boundary": "Evidence may compose; authority may not.",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        plans = self.repo / "plans"
        plans.mkdir()
        (plans / "coordination.aria").write_text(
            'aria 0.4.0\nemit "Evidence may compose; authority may not."\n',
            encoding="utf-8",
        )
        refreshed = bootstrap_repository(
            self.home, self.store, self.repo, "AgentRepo", force=True
        )
        meta = refreshed["environment"]["meta_language"]
        self.assertTrue(meta["available"])
        self.assertEqual(meta["name"], "ARIA")
        self.assertEqual(meta["role"], "host_meta_language")
        self.assertEqual(meta["source_kind"], "host_repository")
        self.assertIsNone(meta["bundle"])
        self.assertEqual(meta["cortex_implementation_language"], "python")
        self.assertEqual(meta["cortex_execution_language"], "python")
        self.assertFalse(meta["execution_policy"]["automatic_execution"])
        self.assertFalse(meta["authority"]["grants_mutation_authority"])
        self.assertIn("plans/coordination.aria", meta["artifact_paths"])
        context = build_context(
            self.home,
            self.store,
            Governor(self.home, self.store),
            "AgentRepo",
            "Coordinate a verified plan",
        )
        self.assertEqual(context["environment"]["meta_language"]["name"], "ARIA")

    def test_sparse_activation_is_deterministic_without_plasticity(self) -> None:
        hits = query(self.store, "AgentRepo", "planner memory bridge", limit=12)
        first = activate_interlink(
            self.store,
            "AgentRepo",
            "planner memory bridge",
            hits,
            plasticity_enabled=False,
            governance_mode="read_only",
        )
        second = activate_interlink(
            self.store,
            "AgentRepo",
            "planner memory bridge",
            hits,
            plasticity_enabled=False,
            governance_mode="read_only",
        )
        self.assertEqual(first.state_hash, second.state_hash)
        self.assertEqual(first.fired_paths, second.fired_paths)
        self.assertLessEqual(first.metrics["nodes_considered"], first.metrics["total_nodes"])
        self.assertIn("planner.py", first.fired_paths)

    def test_structural_interconnection_activates_nonretrieved_support(self) -> None:
        row = self.store.memories_for_path("AgentRepo", "planner.py")[0]
        seed = Hit(
            memory_id=int(row["id"]),
            repo=row["repo"],
            path=row["path"],
            start_line=int(row["start_line"]),
            end_line=int(row["end_line"]),
            text=row["text"],
            kind=row["kind"],
            score=1.0,
            content_hash=row["content_hash"],
            metadata={"semantic_similarity": 1.0},
        )
        packet = activate_interlink(
            self.store,
            "AgentRepo",
            "planner retrieve",
            [seed],
            plasticity_enabled=False,
            governance_mode="read_only",
        )
        self.assertIn("memory_bridge.py", packet.support_paths)
        self.assertIn("memory_bridge.py", packet.fired_paths)

    def test_verified_outcome_is_bounded_replay_gated_and_ledgered(self) -> None:
        hits = query(self.store, "AgentRepo", "planner retrieve memory", limit=12)
        before = {
            row["synapse_id"]: float(row["weight"])
            for row in self.store.neural_synapses("AgentRepo")
        }
        packet = activate_interlink(
            self.store,
            "AgentRepo",
            "planner retrieve memory",
            hits,
            plasticity_enabled=True,
            governance_mode="normal",
            learning_rate=0.25,
        )
        # Activation itself is observational in v2: learning requires verified outcome.
        self.assertEqual(before, {row["synapse_id"]: float(row["weight"]) for row in self.store.neural_synapses("AgentRepo")})
        result = record_outcome(
            self.store, "AgentRepo", packet.activation_id, status="verified",
            verification_type="pytest", governance_mode="normal",
        )
        after_rows = self.store.neural_synapses("AgentRepo")
        self.assertTrue(self.store.verify_neural_ledger("AgentRepo"))
        self.assertGreater(result["credited_synapses"], 0)
        self.assertTrue(result["replay"]["accepted"])
        self.assertGreater(result["accepted_updates"], 0)
        for row in after_rows:
            self.assertGreaterEqual(float(row["weight"]), float(row["minimum_weight"]))
            self.assertLessEqual(float(row["weight"]), float(row["maximum_weight"]))
            self.assertGreaterEqual(float(row["weight"]), before[row["synapse_id"]])

    def test_context_and_nexus_packet_include_environment_and_interlink(self) -> None:
        governor = Governor(self.home, self.store)
        context = build_context(
            self.home,
            self.store,
            governor,
            "AgentRepo",
            "Trace the planner through the memory bridge",
            1200,
            manifest_current=True,
        )
        self.assertTrue(context["environment"]["available"])
        self.assertIn("activation_id", context["neural_interlink"])
        self.assertLessEqual(context["efficiency"]["node_scan_fraction"], 1.0)
        self.assertLessEqual(context["efficiency"]["context_budget_fraction"], 1.0)
        self.assertTrue(context["evidence"])
        packet = nexus_packet(context)
        self.assertIn("neural_interlink", packet["context"])
        self.assertFalse(packet["authority"]["cortex_may_mutate"])
        self.assertTrue(packet["authority"]["human_authorized_only"])
        from cortex.context import cortex_context_protocol
        protocol = cortex_context_protocol(context)
        self.assertEqual("cortex-context/1.0", protocol["protocol"])
        self.assertTrue(protocol["prohibited_actions"])

    def test_neural_ledger_detects_tampering(self) -> None:
        row = self.store.db.execute(
            "SELECT id FROM neural_ledger WHERE repo=? ORDER BY sequence LIMIT 1",
            ("AgentRepo",),
        ).fetchone()
        self.assertIsNotNone(row)
        self.store.db.execute(
            "UPDATE neural_ledger SET payload=? WHERE id=?",
            (json.dumps({"tampered": True}), row["id"]),
        )
        self.store.db.commit()
        self.assertFalse(self.store.verify_neural_ledger("AgentRepo"))

    def test_embedded_engine_directory_is_excluded_from_host_assimilation(self) -> None:
        nested = self.repo / "CortexEngine"
        (nested / "cortex").mkdir(parents=True)
        (nested / "cortex" / "fake.py").write_text("SECRET_ENGINE_SENTINEL = True\n", encoding="utf-8")

        # Simulate a portable engine path nested in a host by temporarily rebinding the recorded module root.
        config = load_repo_config(self.repo)
        config.engine_module_root = str(nested)
        if "CortexEngine" not in config.exclude:
            config.exclude.append("CortexEngine")
        from cortex.config import save_repo_config
        from cortex.indexer import index_repository

        save_repo_config(self.repo, config)
        index_repository(self.store, "AgentRepo", config, force=True)
        paths = {row["path"] for row in self.store.files("AgentRepo")}
        self.assertNotIn("CortexEngine/cortex/fake.py", paths)


if __name__ == "__main__":
    unittest.main()
