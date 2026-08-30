"""Worker-observation and cancellation tests for Cortex alpha.10."""

from __future__ import annotations

import time

from cortex.campaign_control import (
    authorize_control_action,
    campaign_action_request,
    issue_control_session,
    prepare_campaign,
    transition_campaign_control,
)
from cortex.campaign_runtime import (
    acknowledge_campaign_cancellation,
    claim_campaign_worker,
    observe_campaign_runtime,
    record_worker_heartbeat,
)
from cortex.native_agent import CapabilityGrant, ScriptedAgentAdapter
from cortex.storm import (
    AgentManifest,
    DelegatedTask,
    StormAssignment,
    StormGrant,
    StormOrchestrator,
)
from test_v100_alpha8_autonomy import V100Alpha8AutonomyTests


class V100Alpha10CampaignRuntimeTests(V100Alpha8AutonomyTests):
    def storm(self):
        agent = AgentManifest(
            agent_id="agent.observer",
            role="observer",
            purpose="produce one bounded observation",
        )
        now = time.time()
        child = CapabilityGrant(
            workspace_root=str(self.host),
            principal_id=agent.agent_id,
            purpose="alpha10 worker fixture",
            allowed_tools=(),
            max_tool_calls=0,
            max_total_tool_seconds=0,
            issued_at=now - 1,
            expires_at=now + 60,
        )
        ceiling = StormGrant(
            principal_id="operator",
            purpose="alpha10 canonical worker fixture",
            allowed_agent_ids=(agent.agent_id,),
            allowed_roles=(agent.role,),
            allowed_tool_ids=(),
            max_agents=1,
            max_concurrency=1,
            max_iterations_per_agent=1,
            max_tool_calls_per_agent=0,
            max_total_tool_seconds_per_agent=0,
            issued_at=now - 1,
            expires_at=now + 60,
        )
        return StormOrchestrator(self.store, self.repo).run(
            "observe the fixture",
            (
                StormAssignment(
                    DelegatedTask("observe", "report fixture state", agent),
                    ScriptedAgentAdapter(
                        [{"public_output": "fixture observed", "finish_reason": "stop"}]
                    ),
                    child,
                ),
            ),
            grant=ceiling,
        )

    def control_session(self):
        return issue_control_session(
            self.store,
            self.repo,
            principal_id="operator",
            principal_secret=self.secret,
            allowed_actions=(
                "campaign.prepare",
                "campaign.start",
                "campaign.cancel",
            ),
            origin="http://127.0.0.1:8791",
        )

    def authorize(self, session, action, nonce, request):
        return authorize_control_action(
            self.store,
            self.repo,
            control_session_receipt_hash=session["receipt_hash"],
            control_token=session["control_token"],
            csrf_token=session["csrf_token"],
            origin="http://127.0.0.1:8791",
            action=action,
            action_nonce=nonce,
            request=request,
        )

    def start_request(self):
        policy = self.policy()
        storm = self.storm()
        control = self.control_session()
        prepare_request = campaign_action_request(
            "campaign-runtime",
            "campaign.prepare",
            policy_receipt_hash=policy["receipt_hash"],
            storm_summary_receipt_hash=storm["summary_receipt_hash"],
        )
        prepared = prepare_campaign(
            self.store,
            self.repo,
            campaign_id="campaign-runtime",
            policy_receipt_hash=policy["receipt_hash"],
            storm_summary_receipt_hash=storm["summary_receipt_hash"],
            action_authorization=self.authorize(
                control, "campaign.prepare", "prepare", prepare_request
            ),
        )
        start_request = campaign_action_request(
            "campaign-runtime",
            "campaign.start",
            prior_state_receipt_hash=prepared["receipt_hash"],
            policy_receipt_hash=policy["receipt_hash"],
            storm_summary_receipt_hash=storm["summary_receipt_hash"],
        )
        started = transition_campaign_control(
            self.store,
            self.repo,
            campaign_id="campaign-runtime",
            action="campaign.start",
            action_authorization=self.authorize(
                control, "campaign.start", "start", start_request
            ),
        )
        return policy, storm, control, started

    def cancel_request(self, policy, storm, control, prior):
        request = campaign_action_request(
            "campaign-runtime",
            "campaign.cancel",
            prior_state_receipt_hash=prior["receipt_hash"],
            policy_receipt_hash=policy["receipt_hash"],
            storm_summary_receipt_hash=storm["summary_receipt_hash"],
        )
        return transition_campaign_control(
            self.store,
            self.repo,
            campaign_id="campaign-runtime",
            action="campaign.cancel",
            action_authorization=self.authorize(
                control, "campaign.cancel", "cancel", request
            ),
        )

    def claim(self, **overrides):
        values = {
            "campaign_id": "campaign-runtime",
            "worker_id": "worker-1",
            "policy_secret": self.secret,
            "lease_seconds": 10,
            "now": 100.0,
        }
        values.update(overrides)
        return claim_campaign_worker(
            self.store, self.repo, self.host, **values
        )

    def test_worker_claim_reverifies_policy_and_storm(self) -> None:
        self.start_request()
        with self.assertRaisesRegex(PermissionError, "principal_secret_mismatch"):
            self.claim(policy_secret="attacker")
        claim = self.claim()
        self.assertTrue(claim["policy_verified"])
        self.assertTrue(claim["storm_verified"])
        self.assertFalse(claim["execution_success"])
        self.assertFalse(claim["integration_authorized"])
        self.assertFalse(claim["model_execution_authorized"])

    def test_claim_is_exactly_once_and_not_transferable(self) -> None:
        self.start_request()
        first = self.claim()
        duplicate = self.claim()
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(duplicate["receipt_hash"], first["receipt_hash"])
        with self.assertRaisesRegex(PermissionError, "another worker"):
            self.claim(worker_id="worker-2")

    def test_heartbeat_chain_and_stale_detection_are_read_only(self) -> None:
        self.start_request()
        claim = self.claim()
        heartbeat = record_worker_heartbeat(
            self.store,
            self.repo,
            claim_receipt_hash=claim["receipt_hash"],
            sequence=1,
            stage="verification",
            now=101.0,
            lease_seconds=10,
        )
        self.assertEqual(heartbeat["previous_heartbeat_receipt_hash"], "")
        self.assertEqual(
            observe_campaign_runtime(
                self.store, self.repo, "campaign-runtime", now=105.0
            )["state"],
            "running",
        )
        before = len(
            self.store.symbiotic_receipts_by_kind(
                self.repo, "campaign_worker_heartbeat"
            )
        )
        stale = observe_campaign_runtime(
            self.store, self.repo, "campaign-runtime", now=112.0
        )
        after = len(
            self.store.symbiotic_receipts_by_kind(
                self.repo, "campaign_worker_heartbeat"
            )
        )
        self.assertEqual(stale["state"], "stale")
        self.assertTrue(stale["read_only"])
        self.assertEqual(before, after)

    def test_heartbeat_sequence_and_early_cancellation_fail(self) -> None:
        self.start_request()
        claim = self.claim()
        with self.assertRaisesRegex(ValueError, "sequence must be 1"):
            record_worker_heartbeat(
                self.store,
                self.repo,
                claim_receipt_hash=claim["receipt_hash"],
                sequence=2,
                stage="claimed",
            )
        with self.assertRaisesRegex(PermissionError, "before it is requested"):
            record_worker_heartbeat(
                self.store,
                self.repo,
                claim_receipt_hash=claim["receipt_hash"],
                sequence=1,
                stage="cancelling",
                cancellation_observed=True,
            )

    def test_cancel_request_requires_worker_observation_before_ack(self) -> None:
        policy, storm, control, started = self.start_request()
        claim = self.claim()
        live = record_worker_heartbeat(
            self.store,
            self.repo,
            claim_receipt_hash=claim["receipt_hash"],
            sequence=1,
            stage="candidate",
        )
        self.cancel_request(policy, storm, control, started)
        with self.assertRaisesRegex(PermissionError, "has not observed"):
            acknowledge_campaign_cancellation(
                self.store,
                self.repo,
                claim_receipt_hash=claim["receipt_hash"],
                heartbeat_receipt_hash=live["receipt_hash"],
                exit_state="cooperative_stop",
            )
        cancelling = record_worker_heartbeat(
            self.store,
            self.repo,
            claim_receipt_hash=claim["receipt_hash"],
            sequence=2,
            stage="cancelling",
            cancellation_observed=True,
        )
        ack = acknowledge_campaign_cancellation(
            self.store,
            self.repo,
            claim_receipt_hash=claim["receipt_hash"],
            heartbeat_receipt_hash=cancelling["receipt_hash"],
            exit_state="cooperative_stop",
        )
        self.assertEqual(ack["status"], "cancellation_acknowledged")
        self.assertFalse(ack["independent_process_exit_verified"])
        observed = observe_campaign_runtime(
            self.store, self.repo, "campaign-runtime"
        )
        self.assertEqual(observed["state"], "cancellation_acknowledged")
        self.assertFalse(observed["campaign_execution_success"])


if __name__ == "__main__":
    import unittest

    unittest.main()
