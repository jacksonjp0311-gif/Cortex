"""Canonical and transactional closure for Cortex alpha.9."""

from __future__ import annotations

import sys
import time

from cortex.bootstrap import bootstrap_repository
from cortex.autonomous_improvement import (
    AutonomyPolicyEnvelope,
    issue_autonomy_policy,
    promote_tournament_winner,
    resolve_canonical_storm_result,
    revoke_autonomy_policy,
    verify_autonomy_policy,
)
from test_v100_alpha8_autonomy import V100Alpha8AutonomyTests


class V100Alpha9CanonicalCampaignTests(V100Alpha8AutonomyTests):
    def test_caller_valid_boolean_cannot_forge_storm(self) -> None:
        with self.assertRaisesRegex(ValueError, "canonical Storm"):
            resolve_canonical_storm_result(self.store, self.repo, "f" * 64)

    def test_raw_tournament_and_trial_cannot_promote(self) -> None:
        proposal, trial = self.proposal_trial()
        policy = self.policy()
        from cortex.autonomous_improvement import run_improvement_tournament

        tournament = run_improvement_tournament(
            self.host, ({"proposal": proposal, "trial": trial},)
        )
        with self.assertRaisesRegex(PermissionError, "canonical_tournament_missing"):
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

    def test_auto_policy_requires_nonempty_canary(self) -> None:
        envelope = AutonomyPolicyEnvelope(
            principal_id="operator",
            policy_id="missing-canary",
            allowed_path_prefixes=("app/",),
            canary_steps=(),
            allow_auto_promotion=True,
            issued_at=time.time() - 1,
            expires_at=time.time() + 60,
        )
        with self.assertRaisesRegex(ValueError, "requires at least one"):
            issue_autonomy_policy(
                self.store, self.repo, envelope, secret=self.secret
            )

    def test_authenticated_revocation_closes_policy(self) -> None:
        policy = self.policy()
        revocation = revoke_autonomy_policy(
            self.store,
            self.repo,
            policy["receipt_hash"],
            secret=self.secret,
            reason="operator stop",
        )
        self.assertEqual(revocation["status"], "revoked")
        check = verify_autonomy_policy(
            self.store, self.repo, policy["receipt_hash"], secret=self.secret
        )
        self.assertFalse(check["valid"])
        self.assertIn("policy_revoked", check["errors"])

    def test_epoch_drift_closes_policy_without_transition(self) -> None:
        policy = self.policy()
        (self.host / "epoch-drift.txt").write_text("drift\n", encoding="utf-8")
        bootstrap_repository(self.home, self.store, self.host, self.repo)
        from cortex.epoch import ensure_current_epoch

        ensure_current_epoch(self.store, self.repo, reason="alpha9-epoch-drift")
        check = verify_autonomy_policy(
            self.store, self.repo, policy["receipt_hash"], secret=self.secret
        )
        self.assertFalse(check["valid"])
        self.assertIn("policy_epoch_stale", check["errors"])

    def test_failed_canary_never_touches_active_tree(self) -> None:
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
        self.assertTrue(receipt["canary_isolated_before_active_apply"])
        self.assertIsNone(receipt["application"])
        self.assertEqual((self.host / "app" / "value.txt").read_text(), "bad\n")

    def test_policy_canary_command_is_host_vector_not_shell(self) -> None:
        envelope = AutonomyPolicyEnvelope(
            principal_id="operator",
            policy_id="argv-canary",
            allowed_path_prefixes=("app/",),
            canary_steps=(
                {
                    "id": "argv",
                    "argv": [sys.executable, "-c", "raise SystemExit(0)"],
                    "timeout_seconds": 30,
                },
            ),
            allow_auto_promotion=True,
            issued_at=time.time() - 1,
            expires_at=time.time() + 60,
        )
        policy = issue_autonomy_policy(
            self.store, self.repo, envelope, secret=self.secret
        )
        self.assertEqual(policy["canary_steps"][0]["argv"][0], sys.executable)
        self.assertFalse(policy["model_execution_authorized"])
