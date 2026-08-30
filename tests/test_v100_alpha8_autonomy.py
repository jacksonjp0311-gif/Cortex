"""Adversarial closure for policy-bound Cortex autonomous improvement."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from cortex.autonomous_improvement import (
    AutonomyPolicyEnvelope,
    issue_autonomy_policy,
    promote_tournament_winner,
    record_improvement_episode,
    run_autonomous_improvement_campaign,
    run_improvement_tournament,
    synthesize_storm_claims,
    verify_autonomy_policy,
    verify_generation_transition,
)
from cortex.bootstrap import bootstrap_repository
from cortex.coding_workspace import (
    CONTRACT_SCHEMA,
    create_patch_proposal,
    verify_patch_in_isolated_worktree,
)
from cortex.chat_service import CortexChatService
from cortex.config import ensure_home
from cortex.epoch import ensure_current_epoch
from cortex.native_agent import CapabilityGrant, ScriptedAgentAdapter
from cortex.source_improvement import (
    create_source_improvement_contract,
    run_source_improvement_trial,
)
from cortex.store import Store
from cortex.symbiosis import open_symbiotic_session
from cortex.storm import (
    AgentManifest,
    DelegatedTask,
    StormAssignment,
    StormGrant,
    StormOrchestrator,
)
from cortex.will import register_will_principal


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


class V100Alpha8AutonomyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.host = self.base / "host"
        self.host.mkdir()
        (self.host / "app").mkdir()
        (self.host / "app" / "value.txt").write_text("bad\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=self.host, check=True)
        subprocess.run(["git", "config", "user.email", "storm@example.invalid"], cwd=self.host, check=True)
        subprocess.run(["git", "config", "user.name", "Storm Fixture"], cwd=self.host, check=True)
        subprocess.run(["git", "add", "."], cwd=self.host, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=self.host, check=True)
        self.home = ensure_home(self.base / "home")
        self.store = Store(self.home / "cortex.db")
        self.repo = "AutonomyHost"
        bootstrap_repository(self.home, self.store, self.host, self.repo)
        self.secret = "host-secret-alpha8"
        register_will_principal(
            self.store,
            self.repo,
            "operator",
            "Local Operator",
            secret=self.secret,
        )
        ensure_current_epoch(self.store, self.repo, reason="alpha9-policy-test")

    def tearDown(self) -> None:
        self.store.close()
        self.temporary.cleanup()

    def proposal_trial(self):
        patch = """diff --git a/app/value.txt b/app/value.txt
--- a/app/value.txt
+++ b/app/value.txt
@@ -1 +1 @@
-bad
+good
"""
        proposal = create_patch_proposal(self.host, patch, "repair fixture")
        step = {
            "id": "fixture_check",
            "argv": [
                "{python}",
                "-c",
                "from pathlib import Path; raise SystemExit(0 if Path('app/value.txt').read_text().strip() == 'good' else 1)",
            ],
            "timeout_seconds": 30,
        }
        contract = {
            "schema_version": CONTRACT_SCHEMA,
            "policy_id": "fixture-policy",
            "targets": ["app/value.txt"],
            "steps": [step],
            "model_selected": False,
            "caller_selected": False,
            "promotion_authorized": False,
        }
        contract["contract_hash"] = sha(contract)
        verification = verify_patch_in_isolated_worktree(self.host, proposal, contract)
        verification.update(
            {
                "kind": "coding_patch_verification",
                "receipt_hash": sha(verification),
            }
        )
        improvement_contract = create_source_improvement_contract(
            self.host, proposal, verification
        )
        trial = run_source_improvement_trial(
            self.host, proposal, verification, improvement_contract
        )
        self.assertEqual(trial["status"], "REPAIR_MEASURED")
        return proposal, trial

    def policy(
        self,
        *,
        canary_pass=True,
        auto=True,
        recursive=False,
        statuses=("REPAIR_MEASURED",),
    ):
        code = "raise SystemExit(0)" if canary_pass else "raise SystemExit(1)"
        envelope = AutonomyPolicyEnvelope(
            principal_id="operator",
            policy_id=f"policy-{canary_pass}-{auto}-{recursive}",
            allowed_path_prefixes=("app/",),
            allowed_trial_statuses=statuses,
            canary_steps=(
                {
                    "id": "canary",
                    "argv": [sys.executable, "-c", code],
                    "timeout_seconds": 30,
                },
            ),
            allow_auto_promotion=auto,
            allow_recursive_generation=recursive,
            issued_at=time.time() - 1,
            expires_at=time.time() + 120,
        )
        return issue_autonomy_policy(
            self.store, self.repo, envelope, secret=self.secret
        )

    def canonical_promotion_inputs(self, policy, proposal, trial):
        session = open_symbiotic_session(
            self.store,
            self.repo,
            task="canonical promotion fixture",
            provider="fixture",
            model_id="fixture",
            capability_profile={},
            tool_scopes=(),
            persist=True,
        )
        canonical_trial = self.store.append_symbiotic_receipt(
            self.repo,
            {
                **trial,
                "kind": "coding_improvement_trial",
                "session_id": session["session_id"],
                "turn_id": 1,
                "event_id": f"trial_{trial['result_hash'][:24]}",
                "body_epoch_id": session["body_epoch_id"],
            },
        )
        tournament = run_improvement_tournament(
            self.host, ({"proposal": proposal, "trial": canonical_trial},)
        )
        canonical_tournament = self.store.append_symbiotic_receipt(
            self.repo,
            {
                **tournament,
                "kind": "improvement_tournament",
                "session_id": session["session_id"],
                "turn_id": 2,
                "event_id": f"tournament_{tournament['tournament_hash'][:24]}",
                "body_epoch_id": session["body_epoch_id"],
                "policy_receipt_hash": policy["receipt_hash"],
            },
        )
        return canonical_tournament, canonical_trial

    def test_storm_synthesis_maps_independence_and_conflict_without_truth(self) -> None:
        observations = [
            {"receipt_hash": "a" * 64, "observation_hash": "1" * 64, "agent_id": "a"},
            {"receipt_hash": "b" * 64, "observation_hash": "2" * 64, "agent_id": "b"},
        ]
        result = synthesize_storm_claims(
            {
                "session_id": "storm",
                "summary_receipt_hash": "c" * 64,
                "verification": {"valid": True},
                "observations": observations,
            },
            (
                {"observation_receipt_hash": "a" * 64, "claim_key": "x", "stance": "affirm", "evidence_roots": ["root-1"]},
                {"observation_receipt_hash": "b" * 64, "claim_key": "x", "stance": "deny", "evidence_roots": ["root-1"]},
            ),
        )
        group = result["groups"][0]
        self.assertEqual(group["state"], "conflict")
        self.assertEqual(group["independent_evidence_root_count"], 1)
        self.assertEqual(group["truth_state"], "unknown")
        self.assertFalse(result["agreement_is_truth"])

    def test_unrelated_storm_observation_cannot_enter_synthesis(self) -> None:
        with self.assertRaisesRegex(ValueError, "unrelated"):
            synthesize_storm_claims(
                {"verification": {"valid": True}, "observations": []},
                ({"observation_receipt_hash": "x", "claim_key": "x", "stance": "affirm"},),
            )

    def test_autonomy_service_surface_exposes_only_authenticated_host_control(self) -> None:
        surface = CortexChatService(self.store, self.repo).autonomy()
        self.assertEqual(surface["state"], "POLICY_REQUIRED")
        self.assertEqual(surface["automatic_promotion"], "HOST_POLICY_REQUIRED")
        self.assertFalse(surface["model_may_self_authorize"])
        self.assertFalse(surface["policy_may_widen_itself"])
        self.assertFalse(surface["unbounded_autonomy"])
        self.assertTrue(surface["mutation_api_exposed"])
        self.assertEqual(
            surface["mutation_api_authority"],
            "authenticated_host_control_only",
        )
        self.assertFalse(surface["host_mutate_authorized"])
        self.assertFalse(surface["execution_authorized"])

    def test_policy_requires_registered_principal_secret(self) -> None:
        policy = self.policy()
        self.assertTrue(
            verify_autonomy_policy(
                self.store, self.repo, policy["receipt_hash"], secret=self.secret
            )["valid"]
        )
        forged = verify_autonomy_policy(
            self.store, self.repo, policy["receipt_hash"], secret="attacker"
        )
        self.assertFalse(forged["valid"])
        self.assertIn("principal_secret_mismatch", forged["errors"])

    def test_policy_cannot_remove_permanent_protected_surfaces(self) -> None:
        envelope = AutonomyPolicyEnvelope(
            principal_id="operator",
            policy_id="cannot-widen",
            allowed_path_prefixes=("cortex/", "tests/"),
            forbidden_path_prefixes=(),
        )
        material = envelope.material()
        self.assertIn("cortex/autonomous_improvement.py", material["forbidden_path_prefixes"])
        self.assertIn("cortex/tool_fabric.py", material["forbidden_path_prefixes"])
        self.assertIn("tests/", material["forbidden_path_prefixes"])

    def test_tournament_selects_measured_repair_but_grants_no_authority(self) -> None:
        proposal, trial = self.proposal_trial()
        tournament = run_improvement_tournament(
            self.host, ({"proposal": proposal, "trial": trial},)
        )
        self.assertEqual(tournament["selected_proposal_hash"], proposal["proposal_hash"])
        self.assertFalse(tournament["promotion_authorized"])
        self.assertFalse(tournament["model_host_mutate_authorized"])

    def test_policy_bound_winner_promotes_and_canary_passes(self) -> None:
        proposal, trial = self.proposal_trial()
        policy = self.policy(canary_pass=True)
        tournament, trial = self.canonical_promotion_inputs(policy, proposal, trial)
        receipt = promote_tournament_winner(
            self.store,
            self.repo,
            self.host,
            policy_receipt_hash=policy["receipt_hash"],
            secret=self.secret,
            tournament=tournament,
            proposal=proposal,
            trial=trial,
        )
        self.assertEqual(receipt["status"], "promoted_canary_pass")
        self.assertFalse(receipt["rolled_back"])
        self.assertEqual((self.host / "app" / "value.txt").read_text().strip(), "good")
        self.assertFalse(receipt["model_host_mutate_authorized"])

    def test_canary_failure_rolls_back_exact_patch(self) -> None:
        proposal, trial = self.proposal_trial()
        policy = self.policy(canary_pass=False)
        tournament, trial = self.canonical_promotion_inputs(policy, proposal, trial)
        receipt = promote_tournament_winner(
            self.store,
            self.repo,
            self.host,
            policy_receipt_hash=policy["receipt_hash"],
            secret=self.secret,
            tournament=tournament,
            proposal=proposal,
            trial=trial,
        )
        self.assertEqual(receipt["status"], "rolled_back_canary_failed")
        self.assertTrue(receipt["rolled_back"])
        self.assertEqual((self.host / "app" / "value.txt").read_text().strip(), "bad")

    def test_policy_without_auto_promotion_holds_winner(self) -> None:
        proposal, trial = self.proposal_trial()
        policy = self.policy(auto=False)
        tournament, trial = self.canonical_promotion_inputs(policy, proposal, trial)
        with self.assertRaisesRegex(PermissionError, "auto_promotion_not_delegated"):
            promote_tournament_winner(
                self.store,
                self.repo,
                self.host,
                policy_receipt_hash=policy["receipt_hash"],
                secret=self.secret,
                tournament=tournament,
                proposal=proposal,
                trial=trial,
            )
        self.assertEqual((self.host / "app" / "value.txt").read_text().strip(), "bad")

    def test_improvement_episode_is_history_not_admitted_memory(self) -> None:
        proposal, trial = self.proposal_trial()
        policy = self.policy()
        tournament, trial = self.canonical_promotion_inputs(policy, proposal, trial)
        promotion = promote_tournament_winner(
            self.store,
            self.repo,
            self.host,
            policy_receipt_hash=policy["receipt_hash"],
            secret=self.secret,
            tournament=tournament,
            proposal=proposal,
            trial=trial,
        )
        episode = record_improvement_episode(
            self.store,
            self.repo,
            promotion,
            lessons=("bounded repair observed",),
            counterevidence=("single fixture only",),
        )
        self.assertTrue(episode["historical_evidence_only"])
        self.assertFalse(episode["active_guidance"])
        self.assertFalse(episode["memory_admission_authorized"])

    def test_candidate_generation_cannot_verify_itself(self) -> None:
        proposal, trial = self.proposal_trial()
        tournament = run_improvement_tournament(
            self.host, ({"proposal": proposal, "trial": trial},)
        )
        policy = self.policy(recursive=True)
        transition = verify_generation_transition(
            parent_generation="g1",
            candidate_generation="g2",
            verifier_generation="g2",
            policy=policy,
            tournament=tournament,
            proposal=proposal,
        )
        self.assertFalse(transition["eligible"])
        self.assertIn("candidate_generation_cannot_self_verify", transition["errors"])
        self.assertFalse(transition["candidate_self_authorized"])

    def test_storm_patch_flows_through_campaign_without_auto_promotion(self) -> None:
        patch = """diff --git a/app/value.txt b/app/value.txt
--- a/app/value.txt
+++ b/app/value.txt
@@ -1 +1 @@
-bad
+good
"""
        agent = AgentManifest(
            agent_id="agent.coder",
            role="coder",
            purpose="propose one bounded patch",
            allowed_tool_ids=("workspace.propose_patch",),
        )
        child_grant = CapabilityGrant(
            workspace_root=str(self.host),
            principal_id=agent.agent_id,
            purpose="Storm campaign candidate",
            allowed_tools=("workspace.propose_patch",),
            max_tool_calls=1,
            max_total_tool_seconds=30,
            issued_at=time.time() - 1,
            expires_at=time.time() + 60,
        )
        storm_grant = StormGrant(
            principal_id="operator",
            purpose="Storm candidate generation",
            allowed_agent_ids=(agent.agent_id,),
            allowed_roles=(agent.role,),
            allowed_tool_ids=("workspace.propose_patch",),
            max_tool_calls_per_agent=1,
            max_total_tool_seconds_per_agent=30,
            issued_at=time.time() - 1,
            expires_at=time.time() + 60,
        )
        adapter = ScriptedAgentAdapter(
            [
                {
                    "tool_calls": [
                        {
                            "id": "proposal-1",
                            "name": "workspace.propose_patch",
                            "arguments": {"patch": patch, "summary": "repair fixture"},
                        }
                    ],
                    "finish_reason": "tool_calls",
                },
                {"public_output": "candidate proposed", "finish_reason": "stop"},
            ]
        )
        storm = StormOrchestrator(self.store, self.repo).run(
            "generate bounded candidates",
            (
                StormAssignment(
                    DelegatedTask("candidate", "repair the fixture", agent),
                    adapter,
                    child_grant,
                ),
            ),
            grant=storm_grant,
        )
        policy = self.policy(
            statuses=("REPAIR_MEASURED", "VERIFIED_MAINTENANCE")
        )
        campaign = run_autonomous_improvement_campaign(
            self.store,
            self.repo,
            self.host,
            storm_result=storm,
            policy_receipt_hash=policy["receipt_hash"],
            secret=self.secret,
            auto_promote=False,
        )
        self.assertEqual(campaign["candidate_count"], 1)
        self.assertEqual(campaign["tournament"]["selection_state"], "selected")
        self.assertIsNone(campaign["promotion"])
        self.assertEqual((self.host / "app" / "value.txt").read_text().strip(), "bad")
        self.assertFalse(campaign["authority"]["model_host_mutate_authorized"])


if __name__ == "__main__":
    unittest.main()
