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

    def test_mesh_and_prune_and_ritual_gates(self) -> None:
        from cortex.interconnect import mesh_status
        from cortex.prune import prune_graph
        from cortex.session_ritual import run_session_ritual

        mesh = mesh_status(
            self.store, "V5Host", governor=self.gov, home=self.home
        )
        self.assertEqual(mesh.get("glyph"), "⧉")
        self.assertIn("gates", mesh)
        self.assertTrue(mesh["gates"]["relevance_never_mutation"])
        dry = prune_graph(self.store, "V5Host", dry_run=True)
        self.assertIn("candidates", dry)
        ritual = run_session_ritual(
            self.home,
            self.store,
            self.gov,
            "V5Host",
            "seal under default contract",
            memories=[{"kind": "discovery", "text": "mesh-gate-fact"}],
            contract="default",
        )
        self.assertIn("gates_sealed", ritual)
        self.assertIn(ritual.get("contract"), {"default", "strict", "off"})

    def test_spectral_kernels_and_dashboard(self) -> None:
        from cortex.interconnect import mesh_dashboard
        from cortex.kernels import annotate_synapses, kernels_status, rho_from_delta
        from cortex.ranker.model import FEATURE_NAMES, promote_ranker_snapshot

        self.assertAlmostEqual(rho_from_delta(2.3), 0.10, delta=0.02)
        ann = annotate_synapses(self.store, "V5Host")
        self.assertIn("counts", ann)
        ks = kernels_status(self.store, "V5Host")
        self.assertIn("retention", ks)
        self.assertIn("reset", ks["retention"] or {})
        dash = mesh_dashboard(
            self.store, "V5Host", governor=self.gov, home=self.home
        )
        self.assertIn("xi_spectrum", dash)
        self.assertTrue(dash.get("law", "").startswith("common_pulse"))
        denied = promote_ranker_snapshot(self.store, "V5Host", promotion_authorized=False)
        self.assertFalse(denied.get("promoted"))
        self.assertGreaterEqual(len(FEATURE_NAMES), 20)

    def test_lean_agent_profile_and_multi_agent_gate(self) -> None:
        from cortex.agents.tokens import (
            mint_token,
            register_agent,
            set_multi_agent_mode,
        )
        from cortex.hippocampus import remember
        from cortex.profiles import project_packet

        full = {
            "schema_version": "1.4",
            "task": "lean",
            "repository": {"name": "V5Host", "manifest_current": True, "bootstrap_status": "verified"},
            "governor": {"mode": "normal", "stability": 1.0, "extra": "drop"},
            "control_error": {
                "block": False,
                "severity": "none",
                "must_reverify": False,
                "immune_action": {"code": "PROCEED_UNDER_HOST_AUTHORITY", "block": False},
                "summary": "ok",
            },
            "instructions": ["1"],
            "agent_protocol": {
                "hard_stops": [],
                "state": {"allowed_actions": ["read"]},
                "entrypoints": [],
            },
            "thalamus": {"intent": "code_change", "confidence": 0.5, "lane_weights": {"a": 1}},
            "aria_materialization": {"mode": "dormant", "materialized": False},
            "geometry": {"zero_point": True, "axes": {"x": {}}},
            "evidence": [
                {
                    "path": "a.py",
                    "line_range": [1, 2],
                    "kind": "source",
                    "score": 1.0,
                    "text": "x" * 2000,
                    "content_hash": "h",
                }
            ],
            "neural_interlink": {
                "activation_id": "a",
                "state_hash": "s",
                "metrics": {"nodes_fired": 1},
                "fired_paths": ["a"] * 20,
                "support_paths": ["b"] * 20,
            },
            "efficiency": {"context_budget_fraction": 0.2},
            "progress_glyphs": {
                "glyphs": {"connect_pass": {"symbol": "⧉"}},
                "automatic_execution": False,
            },
            "organism": {
                "glyph": "⊛",
                "phase": "systole",
                "pulse": "p",
                "living": True,
                "body": {
                    "immune": {"block": False},
                    "nervous": {"aria_mode": "dormant", "nodes_fired": 1, "mesh": {}},
                    "metabolism": {},
                },
            },
            "connect_pass": {"pass_count": 1, "metric_graph": {"averages": {}}, "spectral": {}},
            "packet_hash": "x",
            "context_budget": 800,
            "estimated_tokens": 100,
        }
        agent = project_packet(full, "agent")
        self.assertEqual(agent["profile"], "agent")
        self.assertIn("constitutional_supervision", agent)
        self.assertLessEqual(len(agent["evidence"][0]["text"]), 800)
        self.assertLessEqual(len(agent["neural_interlink"]["fired_paths"]), 8)
        self.assertNotIn("environment", agent)
        # multi-agent gate
        set_multi_agent_mode(self.store, "V5Host", True)
        blocked = remember(
            self.home, self.store, "V5Host", "discovery", "no-token-should-block"
        )
        self.assertTrue(blocked.get("blocked"))
        register_agent(self.store, "V5Host", "a1", "Agent One")
        tok = mint_token(
            self.store, "V5Host", "a1", ["memory.remember", "memory.read"]
        )
        ok = remember(
            self.home,
            self.store,
            "V5Host",
            "discovery",
            "with-token-ok",
            token_id=tok["token_id"],
        )
        self.assertTrue(ok.get("recorded") or ok.get("duplicate"))
        set_multi_agent_mode(self.store, "V5Host", False)


if __name__ == "__main__":
    unittest.main()
