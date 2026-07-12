from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home, load_repo_config
from cortex.context import build_context, nexus_packet
from cortex.governor import Governor
from cortex.models import Hit
from cortex.neuron import activate_interlink
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

    def test_plasticity_is_bounded_and_ledgered(self) -> None:
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
        after_rows = self.store.neural_synapses("AgentRepo")
        self.assertTrue(self.store.verify_neural_ledger("AgentRepo"))
        self.assertTrue(packet.plasticity_updates)
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

    def test_neural_synaptic_decay(self) -> None:
        """Verify that synapses decay toward minimum_weight over time
        when not co-activated, and that recent updates are exempt during grace period."""
        from cortex.neuron.plasticity import bounded_decay, decay_stats

        # Old synapse (40 days stale) should decay significantly
        now = 1_000_000.0
        old_proposal = bounded_decay(
            synapse_id="syn_old",
            weight=0.8,
            minimum_weight=0.05,
            maximum_weight=1.0,
            last_updated=now - (40 * 86400),  # 40 days ago
            now=now,
            decay_rate=0.005,
            grace_hours=24.0,
        )
        self.assertLess(old_proposal.proposed_weight, 0.8)
        self.assertGreater(old_proposal.proposed_weight, 0.05)
        self.assertIn("bounded_decay", old_proposal.reason)

        # Fresh synapse (within grace period) should NOT decay
        fresh_proposal = bounded_decay(
            synapse_id="syn_fresh",
            weight=0.7,
            minimum_weight=0.05,
            maximum_weight=1.0,
            last_updated=now - 3600,  # 1 hour ago
            now=now,
        )
        self.assertEqual(fresh_proposal.proposed_weight, 0.7)
        self.assertEqual(fresh_proposal.delta, 0.0)
        self.assertEqual(fresh_proposal.reason, "decay_grace_period")

        # Stale synapse with no last_updated should still decay (treats as very old)
        unknown_proposal = bounded_decay(
            synapse_id="syn_unknown",
            weight=0.5,
            minimum_weight=0.1,
            maximum_weight=1.0,
            last_updated=None,
            now=now,
        )
        self.assertLess(unknown_proposal.proposed_weight, 0.5)
        self.assertGreater(unknown_proposal.proposed_weight, 0.1)

    def test_decay_proposals_batch(self) -> None:
        """Verify batch decay_proposals returns correct counts and ratios."""
        from cortex.neuron.plasticity import decay_proposals, decay_stats

        now = 1_000_000.0
        synapses = [
            {"synapse_id": "fresh_1", "weight": 0.7, "minimum_weight": 0.05, "maximum_weight": 1.0, "last_updated": now - 3600},
            {"synapse_id": "fresh_2", "weight": 0.6, "minimum_weight": 0.05, "maximum_weight": 1.0, "last_updated": now - 7200},
            {"synapse_id": "stale_1", "weight": 0.9, "minimum_weight": 0.05, "maximum_weight": 1.0, "last_updated": now - (10 * 86400)},
            {"synapse_id": "stale_2", "weight": 0.4, "minimum_weight": 0.1, "maximum_weight": 1.0, "last_updated": now - (50 * 86400)},
        ]

        proposals = decay_proposals(synapses, now=now)
        self.assertEqual(len(proposals), 4)

        stats = decay_stats(synapses, now=now)
        self.assertEqual(stats["total"], 4)
        self.assertEqual(stats["in_grace_period"], 2)
        self.assertEqual(stats["decayed"], 2)
        self.assertLess(stats["weight_preservation_ratio"], 1.0)

    def test_decay_neural_synapses_store(self) -> None:
        """Verify decay_neural_synapses() updates the database correctly."""
        import time as _time
        from cortex.config import save_repo_config
        from cortex.indexer import index_repository

        config = load_repo_config(self.repo)
        save_repo_config(self.repo, config)
        index_repository(self.store, "AgentRepo", config, force=True)

        # Manually create some synapses with backdated updated_at
        for i, days_old in enumerate([0, 5, 30]):
            self.store.db.execute(
                """
                INSERT INTO neural_synapses(
                  repo, synapse_id, source_id, target_id, relation,
                  base_weight, weight, minimum_weight, maximum_weight,
                  plasticity_rule, update_count, evidence, metadata, updated_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "AgentRepo", f"test_syn_{i}", f"src_{i}", f"tgt_{i}", "related",
                    0.5, 0.7, 0.05, 1.0, "hebbian", 0, "", "{}", _time.time() - (days_old * 86400),
                ),
            )
        self.store.commit()

        # Run decay with 1-day grace period
        result = self.store.decay_neural_synapses("AgentRepo", grace_hours=24.0)
        self.assertIn("applied", result)
        self.assertIn("decayed", result)
        # Stale synapses should have decayed, fresh one shouldn't
        self.assertGreaterEqual(result["applied"], 1)

        # Verify ledger entry was created for decayed synapses
        events = self.store.neural_events("AgentRepo", limit=5)
        decay_events = [e for e in events if e["event_type"] == "plasticity_decay"]
        self.assertGreater(len(decay_events), 0)


if __name__ == "__main__":
    unittest.main()
