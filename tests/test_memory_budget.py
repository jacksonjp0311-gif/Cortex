"""v8.9 trial-guided projection budget tests."""

from __future__ import annotations

import tempfile
import unittest
import hashlib
import json
from pathlib import Path

from cortex.admitted_memory import list_admitted_memories
from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.memory_budget import (
    K_MIN,
    apply_budget,
    budget_status,
    default_budget_policy,
    propose_budget,
    resolve_active_budget,
)
from cortex.memory_projection import project_memories
from cortex.memory_trials import run_cross_instantiation_trial
from cortex.store import Store
from cortex.will import issue_will, register_will_principal, set_default_will_policy


class MemoryBudgetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.home = ensure_home(self.base / "home")
        self.host = self.base / "host"
        self.host.mkdir()
        (self.host / "README.md").write_text("# budget host\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        self.repo = "BudgetHost"
        bootstrap_repository(self.home, self.store, self.host, self.repo)
        register_will_principal(
            self.store, self.repo, "op", "Op", secret="budget-secret-89"
        )
        set_default_will_policy(
            self.store,
            self.repo,
            principal_id="op",
            admit_types=[
                "successful_procedure",
                "persistent_constraint",
                "verified_fact",
            ],
            forbid_types=["unresolved_ambiguity"],
            max_retain=8,
            min_support="medium",
        )
        self.will = issue_will(
            self.store,
            self.repo,
            principal_id="op",
            secret="budget-secret-89",
            session_id="sess-budget",
            body_epoch_id="epoch-budget",
        )

    def tearDown(self) -> None:
        self.store.close()
        self.temporary.cleanup()

    def _admit(self, cid: str, ctype: str, summary: str) -> dict:
        # Legacy-shaped fixture: budget tests inspect policy behavior, while
        # v8.9.2 canonical admission tests cover the production write path.
        material = {
            "schema_version": "cortex-admitted-memory/legacy",
            "version": "8.7.0",
            "kind": "admitted_memory",
            "repo": self.repo,
            "repository_id": self.will.get("repository_id"),
            "session_id": "sess-budget",
            "turn_id": 1,
            "body_epoch_id": "epoch-budget",
            "candidate_id": cid,
            "candidate_type": ctype,
            "kind_alias": ctype,
            "summary": summary,
            "support_level": "medium",
            "evidence": {},
            "source": {"transition_hash": "t" * 64, "outcome_hash": "o" * 64,
                       "prior_frame_hash": "a" * 64, "next_frame_hash": "b" * 64},
            "will_id": self.will.get("will_id"),
            "will_receipt_hash": self.will.get("receipt_hash"),
            "membrane_receipt_hash": "m" * 64,
            "retain": True,
            "from_trajectory": True,
            "from_chat_text": False,
            "invented": False,
            "advisory_only": False,
            "policy_effect": False,
            "update_authorized": False,
            "memory_write_authorized": True,
            "durable_write_authorized": True,
            "host_mutate_authorized": False,
            "execution_authorized": False,
            "claim_boundary": "legacy fixture",
            "cortex_version": "8.7.0",
        }
        memory_id = "mem_" + cid
        event_id = "evt_" + cid
        receipt = {**material, "memory_id": memory_id, "event_id": event_id,
                   "receipt_hash": hashlib.sha256(json.dumps({**material, "memory_id": memory_id, "event_id": event_id}, sort_keys=True).encode()).hexdigest(),
                   "created_at": 1.0}
        self.store.append_admitted_memory(self.repo, receipt)
        from cortex.memory_state import ensure_active_state

        ensure_active_state(self.store, self.repo, receipt)
        for row in list_admitted_memories(self.store, self.repo):
            if row.get("candidate_id") == cid:
                return row
        self.fail(f"missing {cid}")
        return {}

    def test_empty_ledger_structure_only(self) -> None:
        status = budget_status(self.store, self.repo)
        self.assertEqual(status["admitted_count"], 0)
        self.assertEqual(status["proposal"]["mode"], "STRUCTURE_ONLY")
        active = resolve_active_budget(self.store, self.repo)
        self.assertEqual(active["mode"], "STRUCTURE_ONLY")
        self.assertTrue(active["policy"]["structure_only"])
        self.assertFalse(active["policy"]["include_use_feedback"])

    def test_apply_requires_authorization(self) -> None:
        result = apply_budget(self.store, self.repo, authorized=False)
        self.assertFalse(result.get("applied"))
        self.assertIn("missing_i_authorize_budget", result.get("errors") or [])

    def test_apply_unmeasured_blocked_with_memories(self) -> None:
        self._admit(
            "cand_proc_1",
            "successful_procedure",
            "run tests then commit procedure",
        )
        prop = propose_budget(self.store, self.repo)
        self.assertEqual(prop["mode"], "DEFAULT")
        self.assertTrue(prop.get("apply_blocked_if_unmeasured"))
        result = apply_budget(
            self.store, self.repo, authorized=True, force_unmeasured=False
        )
        self.assertFalse(result.get("applied"))
        self.assertTrue(
            any("unmeasured" in e for e in (result.get("errors") or []))
        )

    def test_force_unmeasured_apply_and_projection_stamp(self) -> None:
        self._admit(
            "cand_const_1",
            "persistent_constraint",
            "host mutation immutable and unwitnessed fluency blocked",
        )
        applied = apply_budget(
            self.store,
            self.repo,
            authorized=True,
            force_unmeasured=True,
        )
        self.assertTrue(applied.get("applied"))
        self.assertFalse(applied.get("truth_status_rewritten"))
        tip = resolve_active_budget(self.store, self.repo)
        self.assertFalse(tip.get("is_default", True))
        self.assertTrue(tip.get("operator_authorized"))
        proj = project_memories(
            self.store,
            self.repo,
            task="run tests then commit under host immutability",
            current_will=self.will,
            persist=False,
        )
        self.assertEqual(
            proj.get("budget_policy_hash"), tip.get("budget_policy_hash")
        )
        self.assertIsNotNone(proj.get("budget_mode"))
        self.assertFalse(proj.get("host_mutate_authorized"))

    def test_trial_refreshes_aggregate_and_expand(self) -> None:
        self._admit(
            "cand_proc_ok",
            "successful_procedure",
            "run tests then commit procedure under host immutability",
        )
        self._admit(
            "cand_const_host",
            "persistent_constraint",
            "host source mutation forbidden immutable unwitnessed fluency",
        )
        # Seed enough history tips for K_min with positive G
        history = []
        for i in range(K_MIN):
            history.append(
                {
                    "receipt_hash": f"{'a' * 60}{i:04d}",
                    "G_rehydration": 0.08,
                    "G_credit": 0.02,
                    "U": {"A": 0.3, "D": 0.38, "E": 0.40},
                    "created_at": float(i),
                }
            )
        self.store.set_setting(f"memory_trial_history:{self.repo}", history)
        prop = propose_budget(self.store, self.repo)
        self.assertIn(prop["mode"], {"EXPAND_CAUTIOUS", "FEEDBACK_ON"})
        self.assertTrue(prop["policy"]["calibrated"])
        self.assertGreaterEqual(prop["policy"]["max_memories"], 12)
        if prop["mode"] == "FEEDBACK_ON":
            self.assertTrue(prop["policy"]["include_use_feedback"])

        applied = apply_budget(self.store, self.repo, authorized=True)
        self.assertTrue(applied.get("applied"))
        self.assertGreaterEqual(
            applied["policy"]["max_memories"], default_budget_policy()["max_memories"]
        )

        # Live trial should refresh aggregate tip
        trial = run_cross_instantiation_trial(
            self.store,
            self.repo,
            task="run tests then commit procedure under host immutability",
            current_will=self.will,
            persist=True,
        )
        self.assertIn("G_rehydration", trial)
        agg = self.store.get_setting(f"trial_aggregate_latest:{self.repo}", None)
        self.assertIsNotNone(agg)
        self.assertGreaterEqual(int(agg.get("K") or 0), K_MIN)

    def test_contract_mode_on_negative_g(self) -> None:
        self._admit(
            "cand_x",
            "verified_fact",
            "verified fact for budget contract test",
        )
        history = [
            {
                "receipt_hash": f"{'b' * 60}{i:04d}",
                "G_rehydration": -0.05,
                "G_credit": -0.01,
                "U": {},
                "created_at": float(i),
            }
            for i in range(K_MIN)
        ]
        self.store.set_setting(f"memory_trial_history:{self.repo}", history)
        prop = propose_budget(self.store, self.repo)
        self.assertEqual(prop["mode"], "CONTRACT")
        self.assertLess(prop["policy"]["max_memories"], 12)

    def test_apply_never_rewrites_truth(self) -> None:
        self._admit(
            "cand_y",
            "successful_procedure",
            "run tests then commit",
        )
        applied = apply_budget(
            self.store, self.repo, authorized=True, force_unmeasured=True
        )
        self.assertTrue(applied.get("applied"))
        self.assertFalse(applied.get("truth_status_rewritten"))
        self.assertFalse(applied.get("host_mutate_authorized"))
        self.assertFalse(applied.get("execution_authorized"))


if __name__ == "__main__":
    unittest.main()
