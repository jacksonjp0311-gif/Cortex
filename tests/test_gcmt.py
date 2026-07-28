from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from cortex import __version__
from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.context import build_context
from cortex.continuation import (
    build_continuation_packet,
    promote,
    rollback,
    verify_continuation_packet,
)
from cortex.evaluation import evaluate_corpus
from cortex.federation import federated_query
from cortex.governor import Governor
from cortex.lifecycle import apply_lifecycle, lifecycle_plan
from cortex.mcp import CortexMCP
from cortex.retrieval import query
from cortex.store import Store


class GovernedContinuationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.home = ensure_home(self.base / "home")
        self.repo = self.base / "alpha"
        self.repo.mkdir()
        (self.repo / "README.md").write_text(
            "# Alpha\n\nThe alpha service uses a verified greeting route.\n",
            encoding="utf-8",
        )
        (self.repo / "app.py").write_text(
            "from helper import greeting\n\n"
            "def run():\n"
            "    return greeting('alpha')\n",
            encoding="utf-8",
        )
        (self.repo / "helper.py").write_text(
            "def greeting(name):\n"
            "    return f'hello {name}'\n",
            encoding="utf-8",
        )
        self.store = Store(self.home / "cortex.db")
        bootstrap_repository(self.home, self.store, self.repo, "Alpha")
        self.governor = Governor(self.home, self.store)

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def context(self) -> dict:
        return build_context(
            self.home,
            self.store,
            self.governor,
            "Alpha",
            "Trace the verified greeting route",
        )

    def test_vector_buckets_are_backfilled_and_used_without_losing_recall(self) -> None:
        self.store.db.execute("DELETE FROM memory_vector_buckets WHERE repo='Alpha'")
        self.store.db.commit()
        hits = query(self.store, "Alpha", "verified greeting route", limit=5)
        count = self.store.db.execute(
            "SELECT COUNT(*) FROM memory_vector_buckets WHERE repo='Alpha'"
        ).fetchone()[0]
        self.assertGreater(count, 0)
        self.assertIn("README.md", {hit.path for hit in hits})

    def test_verified_continuation_packet_preserves_three_state_planes(self) -> None:
        packet = build_continuation_packet(
            self.store,
            self.context(),
            origin_version=__version__,
            ttl_seconds=60,
        )
        self.assertEqual(packet["protocol"], "cortex-continuation/1.0")
        self.assertIn("operational_state", packet)
        self.assertIn("evidence_state", packet)
        self.assertIn("canonical_state", packet)
        self.assertTrue(verify_continuation_packet(packet)["valid"])
        self.assertFalse(
            verify_continuation_packet(
                packet, now=packet["conditions"]["expires_at"] + 1
            )["valid"]
        )

    def test_promotion_requires_evidence_verification_authority_and_rolls_back(self) -> None:
        evidence_row = self.store.lexical("Alpha", "verified", 1)[0]
        evidence = [
            {
                "memory_id": evidence_row["id"],
                "path": evidence_row["path"],
                "content_hash": evidence_row["content_hash"],
            }
        ]
        rejected = promote(
            self.store,
            "Alpha",
            state_key="architecture.greeting",
            candidate={"owner": "app.py"},
            evidence=evidence,
            verification={"tests": True, "repeatable": True},
            authority={"promotion_authorized": False},
        )
        self.assertFalse(rejected["promoted"])
        accepted = promote(
            self.store,
            "Alpha",
            state_key="architecture.greeting",
            candidate={"owner": "app.py"},
            evidence=evidence,
            verification={"tests": True, "repeatable": True},
            authority={"promotion_authorized": True},
        )
        self.assertTrue(accepted["promoted"])
        self.assertTrue(self.store.verify_continuation_receipts("Alpha"))
        duplicate = promote(
            self.store,
            "Alpha",
            state_key="architecture.greeting",
            candidate={"owner": "app.py"},
            evidence=evidence,
            verification={"tests": True, "repeatable": True},
            authority={"promotion_authorized": True},
        )
        self.assertFalse(duplicate["promoted"])
        self.assertEqual(duplicate["canonical_receipt_id"], accepted["receipt_id"])
        result = rollback(
            self.store, "Alpha", accepted["receipt_id"], authorized=True
        )
        self.assertTrue(result["rolled_back"])
        self.assertIsNone(self.store.canonical_state("Alpha", "architecture.greeting"))
        self.assertTrue(self.store.verify_continuation_receipts("Alpha"))

    def test_lifecycle_decay_retires_only_learned_deviation(self) -> None:
        row = self.store.neural_synapses("Alpha")[0]
        learned = min(float(row["maximum_weight"]), float(row["base_weight"]) + 0.1)
        self.store.db.execute(
            """UPDATE neural_synapses SET weight=?, updated_at=?
               WHERE repo='Alpha' AND synapse_id=?""",
            (learned, time.time() - 10 * 86_400, row["synapse_id"]),
        )
        self.store.db.commit()
        plan = lifecycle_plan(
            self.store, "Alpha", grace_hours=0, decay_per_day=0.2
        )
        proposal = next(
            item for item in plan["proposals"] if item["synapse_id"] == row["synapse_id"]
        )
        self.assertGreaterEqual(proposal["proposed_weight"], float(row["base_weight"]))
        applied = apply_lifecycle(
            self.store,
            "Alpha",
            governance_mode="constrained",
            authorized=True,
            grace_hours=0,
            decay_per_day=0.2,
        )
        self.assertTrue(applied["applied"])
        self.assertTrue(self.store.verify_neural_ledger("Alpha"))

    def test_federation_preserves_repository_boundaries(self) -> None:
        second = self.base / "beta"
        second.mkdir()
        (second / "README.md").write_text(
            "# Beta\n\nThe beta service owns a different greeting route.\n",
            encoding="utf-8",
        )
        bootstrap_repository(self.home, self.store, second, "Beta")
        result = federated_query(
            self.store,
            "greeting route",
            repositories=["Alpha", "Beta"],
            limit=8,
        )
        self.assertTrue(result["boundary_preserved"])
        self.assertTrue(
            all(hit["boundary"]["repository"] in {"Alpha", "Beta"} for hit in result["hits"])
        )

    def test_replay_evaluation_compares_base_and_learned_routes(self) -> None:
        corpus = {
            "name": "alpha-smoke",
            "cases": [
                {
                    "id": "source-recall",
                    "repo": "Alpha",
                    "task": "Trace the greeting implementation",
                    "expected_paths": ["app.py", "helper.py"],
                },
                {
                    "id": "abstain",
                    "repo": "Alpha",
                    "task": "Where is the quantum payment deployment?",
                    "should_abstain": True,
                    "abstain_below": 0.99,
                },
            ],
        }
        result = evaluate_corpus(self.store, corpus)
        self.assertEqual(result["corpus"]["cases"], 2)
        self.assertTrue(result["gate"]["no_retrieval_regression"])
        self.assertEqual(result["claim_class"], "benchmark_evidence")

    def test_mcp_exposes_read_only_agent_surfaces(self) -> None:
        self.store.close()
        server = CortexMCP(self.home)
        try:
            initialized = server.dispatch(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {"protocolVersion": "2025-11-25"},
                }
            )
            self.assertEqual(initialized["result"]["serverInfo"]["name"], "cortex")
            discovered = server.dispatch(
                {"jsonrpc": "2.0", "id": "discover", "method": "server/discover", "params": {}}
            )
            self.assertIn("2026-07-28", discovered["result"]["supportedVersions"])
            listed = server.dispatch(
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
            )
            names = {tool["name"] for tool in listed["result"]["tools"]}
            self.assertIn("cortex_continuation", names)
            self.assertIn("cortex_federated_query", names)
        finally:
            server.close()
            self.store = Store(self.home / "cortex.db")


if __name__ == "__main__":
    unittest.main()
