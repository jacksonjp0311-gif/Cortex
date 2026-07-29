"""v5.0 governed local cognition substrate gates."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.activation import activate_repository
from cortex.agents.tokens import (
    ALLOWED_SCOPES,
    FORBIDDEN_SCOPES,
    mint_token,
    register_agent,
    validate_token,
)
from cortex.bootstrap import bootstrap_repository
from cortex.causal import causal_report, evaluate_causal_episode, open_episode
from cortex.config import ensure_home
from cortex.contract.check import DEFAULT_CONTRACT, STRICT_CONTRACT, check_contract
from cortex.governor import Governor
from cortex.ranker.model import ensure_ranker, ranker_status, train_from_outcome
from cortex.store import Store
from cortex.vectors.hnsw import HNSWIndex
from cortex.vectors.index import build_hnsw_index, hnsw_status, query_hnsw


class V5SubstrateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.home = ensure_home(self.base / "home")
        self.repo = self.base / "v5host"
        self.repo.mkdir()
        (self.repo / "README.md").write_text(
            "# V5 Host\n\n## Architecture\n\nCore loop and memory.\n",
            encoding="utf-8",
        )
        (self.repo / "app.py").write_text(
            "def run() -> str:\n    return 'ok'\n\ndef helper(x: int) -> int:\n    return x + 1\n",
            encoding="utf-8",
        )
        (self.repo / "test_app.py").write_text(
            "from app import run\n\ndef test_run() -> None:\n    assert run() == 'ok'\n",
            encoding="utf-8",
        )
        self.store = Store(self.home / "cortex.db")
        self.boot = bootstrap_repository(self.home, self.store, self.repo, "V5Host")
        self.gov = Governor(self.home, self.store)

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_no_host_mutate_scope(self) -> None:
        self.assertNotIn("host.mutate", ALLOWED_SCOPES)
        self.assertIn("host.mutate", FORBIDDEN_SCOPES)

    def test_multi_res_compile(self) -> None:
        from cortex.neuron import compile_interlink

        state = compile_interlink(
            self.store, "V5Host", resolutions=("file", "symbol", "basic_block")
        )
        self.assertIn("resolutions", state)
        self.assertGreaterEqual(state["resolutions"].get("file", 0), 1)
        # symbols extracted from app.py functions
        self.assertGreaterEqual(state["resolutions"].get("symbol", 0), 1)
        nodes = self.store.neural_nodes("V5Host")
        resolutions = {
            (row["resolution"] if "resolution" in row.keys() else "file")
            for row in nodes
        }
        self.assertIn("file", resolutions)

    def test_hnsw_build_and_query(self) -> None:
        built = build_hnsw_index(self.store, "V5Host")
        self.assertTrue(built.get("built") or built.get("reason") == "no_vectors")
        if built.get("built"):
            st = hnsw_status(self.store, "V5Host")
            self.assertTrue(st.get("available"))
            hits = query_hnsw(self.store, "V5Host", "architecture memory", k=4)
            self.assertIsInstance(hits, list)

    def test_hnsw_deterministic_unit(self) -> None:
        a = HNSWIndex(dim=3, M=4, seed=42)
        b = HNSWIndex(dim=3, M=4, seed=42)
        items = [("z", [0.0, 1.0, 0.0]), ("a", [1.0, 0.0, 0.0]), ("m", [0.7, 0.7, 0.0])]
        a.build(items)
        b.build(items)
        self.assertEqual(a.search([1.0, 0.0, 0.0], k=2)[0][0], "a")
        self.assertEqual(
            [k for k, _ in a.search([1.0, 0.0, 0.0], k=3)],
            [k for k, _ in b.search([1.0, 0.0, 0.0], k=3)],
        )

    def test_ranker_verified_only(self) -> None:
        ensure_ranker(self.store, "V5Host")
        blocked = train_from_outcome(
            self.store,
            "V5Host",
            outcome_id="out_x",
            activation_id="act_x",
            status="verified",
            reward=1.0,
            verification_type="test",
            governance_mode="read_only",
        )
        self.assertFalse(blocked.get("trained"))
        ok = train_from_outcome(
            self.store,
            "V5Host",
            outcome_id="out_y",
            activation_id="act_y",
            status="verified",
            reward=1.0,
            verification_type="test",
            governance_mode="normal",
        )
        self.assertTrue(ok.get("trained"))
        st = ranker_status(self.store, "V5Host")
        self.assertGreaterEqual(st.get("train_count", 0), 1)

    def test_predict_and_activate_prefetch(self) -> None:
        from cortex.predict import predict_context

        pred = predict_context(
            self.store, "V5Host", "Map the architecture", budget=160, governor_mode="normal"
        )
        self.assertIn("predicted_paths", pred)
        act = activate_repository(
            self.home,
            self.store,
            self.gov,
            "V5Host",
            "Map the architecture",
            budget=500,
            prefetch="auto",
        )
        self.assertIn("connect_pass", act)
        self.assertIn("block", act)

    def test_contracts(self) -> None:
        fail = check_contract(
            {
                "governor": {"mode": "read_only"},
                "authority": {"cortex_may_mutate": False},
                "claim_boundary": "x",
                "operational_state": {"evidence_ids": [1]},
            },
            contract=STRICT_CONTRACT,
        )
        self.assertFalse(fail.get("passed"))
        ok = check_contract(
            {
                "governor": {"mode": "normal"},
                "control_error": {"block": False},
                "authority": {
                    "cortex_may_mutate": False,
                    "packet_is_not_authorization": True,
                },
                "claim_boundary": "x",
                "operational_state": {"evidence_ids": [1]},
            },
            contract=DEFAULT_CONTRACT,
        )
        self.assertTrue(ok.get("passed"))

    def test_agents_and_tokens(self) -> None:
        reg = register_agent(self.store, "V5Host", "agent-a", "Test Agent")
        self.assertTrue(reg.get("registered"))
        bad = mint_token(
            self.store, "V5Host", "agent-a", ["host.mutate"], ttl_seconds=600
        )
        self.assertFalse(bad.get("minted"))
        tok = mint_token(
            self.store,
            "V5Host",
            "agent-a",
            ["memory.read", "memory.remember"],
            ttl_seconds=600,
        )
        self.assertTrue(tok.get("minted"))
        val = validate_token(
            self.store, "V5Host", tok["token_id"], required_scope="memory.read"
        )
        self.assertTrue(val.get("valid"))

    def test_causal_ledger(self) -> None:
        open_episode(self.store, "V5Host", "retrieval")
        ep = evaluate_causal_episode(
            self.store, "V5Host", recall_before=0.4, recall_after=0.5
        )
        self.assertEqual(ep.get("verdict"), "improved")
        report = causal_report(self.store, "V5Host")
        self.assertGreaterEqual(report["counts"]["total"], 1)


if __name__ == "__main__":
    unittest.main()
