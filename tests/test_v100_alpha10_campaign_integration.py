"""Recoverable candidate-commit integration tests for Cortex alpha.10."""

from __future__ import annotations

import time
import subprocess

from cortex.campaign_control import campaign_action_request, transition_campaign_control
from cortex.campaign_integration import (
    apply_campaign_integration,
    integration_request,
    prepare_campaign_integration,
)
from cortex.chat_service import CortexChatService
from cortex.campaign_runtime import claim_campaign_worker, run_claimed_improvement_campaign
from cortex.bootstrap import bootstrap_repository
from cortex.epoch import ensure_current_epoch
from cortex.native_agent import CapabilityGrant, ScriptedAgentAdapter
from cortex.storm import AgentManifest, DelegatedTask, StormAssignment, StormGrant, StormOrchestrator
from test_v100_alpha10_campaign_runtime import V100Alpha10CampaignRuntimeTests


class V100Alpha10CampaignIntegrationTests(V100Alpha10CampaignRuntimeTests):
    def storm_with_patch(self):
        patch = """diff --git a/app/value.txt b/app/value.txt
--- a/app/value.txt
+++ b/app/value.txt
@@ -1 +1 @@
-bad
+good
"""
        agent = AgentManifest(
            agent_id="agent.coder", role="coder", purpose="bounded candidate",
            allowed_tool_ids=("workspace.propose_patch",),
        )
        now = time.time()
        child = CapabilityGrant(
            workspace_root=str(self.host), principal_id=agent.agent_id,
            purpose="candidate", allowed_tools=("workspace.propose_patch",),
            max_tool_calls=1, issued_at=now - 1, expires_at=now + 60,
        )
        ceiling = StormGrant(
            principal_id="operator", purpose="candidate", allowed_agent_ids=(agent.agent_id,),
            allowed_roles=(agent.role,), allowed_tool_ids=("workspace.propose_patch",),
            max_agents=1, max_concurrency=1, max_tool_calls_per_agent=1,
            issued_at=now - 1, expires_at=now + 60,
        )
        adapter = ScriptedAgentAdapter([
            {"tool_calls": [{"id": "p", "name": "workspace.propose_patch", "arguments": {"patch": patch, "summary": "repair"}}], "finish_reason": "tool_calls"},
            {"public_output": "candidate", "finish_reason": "stop"},
        ])
        return StormOrchestrator(self.store, self.repo).run(
            "generate candidate",
            (StormAssignment(DelegatedTask("candidate", "repair", agent), adapter, child),),
            grant=ceiling,
        )

    def prepared_run(self):
        subprocess.run(["git", "add", "-A"], cwd=self.host, check=True)
        if subprocess.run(
            ["git", "diff", "--cached", "--quiet"], cwd=self.host, check=False
        ).returncode:
            subprocess.run(
                ["git", "commit", "-qm", "tracked Cortex fixture"],
                cwd=self.host,
                check=True,
            )
            bootstrap_repository(self.home, self.store, self.host, self.repo)
            subprocess.run(["git", "add", "-A"], cwd=self.host, check=True)
            if subprocess.run(
                ["git", "diff", "--cached", "--quiet"],
                cwd=self.host,
                check=False,
            ).returncode:
                subprocess.run(
                    ["git", "commit", "-qm", "Cortex fixture integration"],
                    cwd=self.host,
                    check=True,
                )
            ensure_current_epoch(self.store, self.repo, reason="alpha10-integration-fixture")
        policy = self.policy(statuses=("REPAIR_MEASURED", "VERIFIED_MAINTENANCE"))
        storm = self.storm_with_patch()
        control = self.control_session()
        prepare_request = campaign_action_request(
            "campaign-runtime", "campaign.prepare",
            policy_receipt_hash=policy["receipt_hash"],
            storm_summary_receipt_hash=storm["summary_receipt_hash"],
        )
        from cortex.campaign_control import prepare_campaign
        prepared = prepare_campaign(
            self.store, self.repo, campaign_id="campaign-runtime",
            policy_receipt_hash=policy["receipt_hash"],
            storm_summary_receipt_hash=storm["summary_receipt_hash"],
            action_authorization=self.authorize(control, "campaign.prepare", "p", prepare_request),
        )
        start_request = campaign_action_request(
            "campaign-runtime", "campaign.start", prior_state_receipt_hash=prepared["receipt_hash"],
            policy_receipt_hash=policy["receipt_hash"], storm_summary_receipt_hash=storm["summary_receipt_hash"],
        )
        transition_campaign_control(
            self.store, self.repo, campaign_id="campaign-runtime", action="campaign.start",
            action_authorization=self.authorize(control, "campaign.start", "s", start_request),
        )
        claim = claim_campaign_worker(
            self.store, self.repo, self.host, campaign_id="campaign-runtime",
            worker_id="worker-integration", policy_secret=self.secret,
        )
        run = run_claimed_improvement_campaign(
            self.store, self.repo, self.host, claim_receipt_hash=claim["receipt_hash"],
            storm_result=storm, policy_receipt_hash=policy["receipt_hash"], policy_secret=self.secret,
        )
        return policy, control, run

    def test_candidate_commit_is_off_tree_then_fast_forward_integrated(self) -> None:
        policy, control, run = self.prepared_run()
        campaign = run["campaign_result"]
        winner = next(item for item in campaign["evaluated"] if item.get("eligible"))
        terminal = run["terminal"]
        promote_request = integration_request(
            "campaign-runtime", "campaign.promote", terminal_hash=terminal["receipt_hash"]
        )
        prepared = prepare_campaign_integration(
            self.store, self.repo, self.host, campaign_id="campaign-runtime",
            terminal_receipt_hash=terminal["receipt_hash"], policy_receipt_hash=policy["receipt_hash"],
            policy_secret=self.secret, tournament_receipt_hash=campaign["tournament"]["receipt_hash"],
            trial_receipt_hash=winner["trial"]["receipt_hash"], proposal=winner["proposal"],
            action_authorization=self.authorize(control, "campaign.promote", "promote", promote_request),
        )
        self.assertEqual((self.host / "app" / "value.txt").read_text().strip(), "bad")
        self.assertFalse(prepared["active_worktree_mutated"])
        integrate_request = integration_request(
            "campaign-runtime", "campaign.integrate",
            preparation_hash=prepared["receipt_hash"], candidate_commit=prepared["candidate_commit"],
        )
        integrated = apply_campaign_integration(
            self.store, self.repo, self.host, preparation_receipt_hash=prepared["receipt_hash"],
            action_authorization=self.authorize(control, "campaign.integrate", "integrate", integrate_request),
        )
        self.assertEqual(integrated["status"], "verified_complete")
        self.assertEqual((self.host / "app" / "value.txt").read_text().strip(), "good")
        self.assertFalse(integrated["campaign_success"])
        self.assertFalse(integrated["model_host_mutate_authorized"])
        rollback_request = integration_request(
            "campaign-runtime",
            "campaign.rollback",
            preparation_hash=prepared["receipt_hash"],
            candidate_commit=prepared["candidate_commit"],
            integration_result_hash=integrated["receipt_hash"],
        )
        rolled_back = CortexChatService(self.store, self.repo).campaign_command(
            "campaign-runtime",
            "rollback",
            {"integration_result_hash": integrated["receipt_hash"]},
            self.authorize(
                control, "campaign.rollback", "rollback", rollback_request
            ),
        )
        self.assertEqual(rolled_back["status"], "rollback_verified")
        self.assertTrue(rolled_back["history_preserving_revert"])
        self.assertEqual(rolled_back["anchor_tree"], rolled_back["restored_tree"])
        self.assertEqual((self.host / "app" / "value.txt").read_text().strip(), "bad")


if __name__ == "__main__":
    import unittest
    unittest.main()
