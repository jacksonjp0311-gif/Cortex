"""Adversarial closure tests for alpha.11 control capabilities and lifecycle."""

from __future__ import annotations

import concurrent.futures
import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.campaign_control import (
    authorize_control_action,
    campaign_action_request,
    issue_control_session,
    prepare_campaign,
    revoke_control_session,
    transition_campaign_control,
    verify_campaign_lifecycle,
    verify_control_action,
)
from cortex.config import ensure_home
from cortex.epoch import ensure_current_epoch
from cortex.store import Store
from cortex.symbiosis import open_symbiotic_session
from cortex.will import register_will_principal


class V100Alpha11IntegrityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.host = self.base / "host"
        self.host.mkdir()
        (self.host / "app.txt").write_text("alpha11\n", encoding="utf-8")
        import subprocess

        subprocess.run(["git", "init", "-q"], cwd=self.host, check=True)
        subprocess.run(
            ["git", "config", "user.email", "alpha11@example.invalid"],
            cwd=self.host,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Alpha 11 Fixture"],
            cwd=self.host,
            check=True,
        )
        subprocess.run(["git", "add", "."], cwd=self.host, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=self.host, check=True)
        self.home = ensure_home(self.base / "home")
        self.store = Store(self.home / "cortex.db")
        self.repo = "Alpha11Host"
        self.secret = "alpha11-operator-secret"
        bootstrap_repository(self.home, self.store, self.host, self.repo)
        register_will_principal(
            self.store,
            self.repo,
            "operator",
            "Local Operator",
            secret=self.secret,
        )
        ensure_current_epoch(self.store, self.repo, reason="alpha11-integrity-test")

    def tearDown(self) -> None:
        self.store.close()
        self.temporary.cleanup()

    def _session(self, *, ttl_seconds: float = 300.0):
        return issue_control_session(
            self.store,
            self.repo,
            principal_id="operator",
            principal_secret=self.secret,
            allowed_actions=(
                "campaign.prepare",
                "campaign.start",
                "campaign.cancel",
                "control.revoke",
            ),
            origin="http://127.0.0.1:8791",
            ttl_seconds=ttl_seconds,
        )

    def _authorize(self, session, action, nonce, request):
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

    def _root(self, kind: str):
        session = open_symbiotic_session(
            self.store,
            self.repo,
            task=f"alpha11 {kind}",
            provider="fixture",
            model_id="none",
            capability_profile={},
            tool_scopes=(),
            persist=True,
        )
        return self.store.append_symbiotic_receipt(
            self.repo,
            {
                "kind": kind,
                "status": "verified",
                "session_id": session["session_id"],
                "turn_id": 0,
                "event_id": f"alpha11_{kind}",
                "body_epoch_id": session["body_epoch_id"],
            },
        )

    def _authorized_prepare(self, session, campaign_id="campaign-11"):
        policy = self._root("autonomy_policy")
        storm = self._root("storm_summary")
        request = campaign_action_request(
            campaign_id,
            "campaign.prepare",
            policy_receipt_hash=policy["receipt_hash"],
            storm_summary_receipt_hash=storm["receipt_hash"],
        )
        action = self._authorize(session, "campaign.prepare", "prepare-11", request)
        return policy, storm, request, action

    def test_unspent_action_expires_with_parent_session(self) -> None:
        session = self._session(ttl_seconds=30)
        _, _, request, action = self._authorized_prepare(session)
        with self.assertRaisesRegex(PermissionError, "canonical_action_expired"):
            verify_control_action(
                self.store,
                self.repo,
                action,
                expected_action="campaign.prepare",
                expected_request=request,
                now=float(session["expires_at"]) + 1,
            )

    def test_unspent_action_is_closed_by_parent_revocation(self) -> None:
        session = self._session()
        _, _, request, action = self._authorized_prepare(session)
        revoke_request = {"campaign_id": "campaign-11"}
        revoke_action = self._authorize(
            session, "control.revoke", "revoke-11", revoke_request
        )
        revoke_control_session(
            self.store,
            self.repo,
            action_authorization=revoke_action,
            reason="close outstanding capabilities",
        )
        with self.assertRaisesRegex(PermissionError, "parent_control_session_revoked"):
            verify_control_action(
                self.store,
                self.repo,
                action,
                expected_action="campaign.prepare",
                expected_request=request,
            )

    def test_unspent_action_is_closed_by_epoch_drift(self) -> None:
        session = self._session()
        _, _, request, action = self._authorized_prepare(session)
        (self.host / "epoch-drift.txt").write_text("drift\n", encoding="utf-8")
        bootstrap_repository(self.home, self.store, self.host, self.repo)
        ensure_current_epoch(self.store, self.repo, reason="alpha11-epoch-drift")
        with self.assertRaisesRegex(PermissionError, "parent_control_session_epoch_stale"):
            verify_control_action(
                self.store,
                self.repo,
                action,
                expected_action="campaign.prepare",
                expected_request=request,
            )

    def test_parallel_nonce_is_database_exactly_once(self) -> None:
        session = self._session()
        request = {"campaign_id": "parallel-11"}

        def attempt(_index: int):
            store = Store(self.home / "cortex.db")
            try:
                return authorize_control_action(
                    store,
                    self.repo,
                    control_session_receipt_hash=session["receipt_hash"],
                    control_token=session["control_token"],
                    csrf_token=session["csrf_token"],
                    origin="http://127.0.0.1:8791",
                    action="campaign.prepare",
                    action_nonce="parallel-nonce",
                    request=request,
                )
            finally:
                store.close()

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = []
            for future in [pool.submit(attempt, index) for index in range(2)]:
                try:
                    outcomes.append(("ok", future.result()))
                except PermissionError as exc:
                    outcomes.append(("held", str(exc)))
        self.assertEqual([kind for kind, _ in outcomes].count("ok"), 1)
        self.assertEqual([kind for kind, _ in outcomes].count("held"), 1)
        self.assertIn("action_nonce_replayed", str(outcomes))
        rows = [
            item
            for item in self.store.symbiotic_receipts_by_kind(
                self.repo, "campaign_control_action"
            )
            if item.get("action_nonce") == "parallel-nonce"
        ]
        self.assertEqual(len(rows), 1)

    def test_lifecycle_reconstruction_rejects_semantically_illegal_row(self) -> None:
        session = self._session()
        policy, storm, _, prepare_action = self._authorized_prepare(session)
        prepared = prepare_campaign(
            self.store,
            self.repo,
            campaign_id="campaign-11",
            policy_receipt_hash=policy["receipt_hash"],
            storm_summary_receipt_hash=storm["receipt_hash"],
            action_authorization=prepare_action,
        )
        start_request = campaign_action_request(
            "campaign-11",
            "campaign.start",
            prior_state_receipt_hash=prepared["receipt_hash"],
            policy_receipt_hash=policy["receipt_hash"],
            storm_summary_receipt_hash=storm["receipt_hash"],
        )
        start_action = self._authorize(session, "campaign.start", "start-11", start_request)
        started = transition_campaign_control(
            self.store,
            self.repo,
            campaign_id="campaign-11",
            action="campaign.start",
            action_authorization=start_action,
        )
        forged_request = campaign_action_request(
            "campaign-11",
            "campaign.start",
            prior_state_receipt_hash=started["receipt_hash"],
            policy_receipt_hash=policy["receipt_hash"],
            storm_summary_receipt_hash=storm["receipt_hash"],
        )
        forged_action = self._authorize(
            session, "campaign.start", "start-again-11", forged_request
        )
        forged_session = open_symbiotic_session(
            self.store,
            self.repo,
            task="forge individually valid lifecycle row",
            provider="fixture",
            model_id="none",
            capability_profile={},
            tool_scopes=(),
            persist=True,
        )
        self.store.append_symbiotic_receipt(
            self.repo,
            {
                "schema_version": "cortex-campaign-lifecycle/1.0",
                "kind": "campaign_lifecycle",
                "status": "start_requested",
                "session_id": forged_session["session_id"],
                "turn_id": 0,
                "event_id": "alpha11_illegal_start",
                "body_epoch_id": forged_session["body_epoch_id"],
                "campaign_id": "campaign-11",
                "state_sequence": 2,
                "previous_state_receipt_hash": started["receipt_hash"],
                "action_authorization_receipt_hash": forged_action["receipt_hash"],
                "principal_id": "operator",
                "policy_receipt_hash": policy["receipt_hash"],
                "storm_summary_receipt_hash": storm["receipt_hash"],
                "cooperative_stop_required": False,
                "campaign_execution_observed": False,
                "evidence_semantics_verified": False,
                "host_control_authorized": True,
                "model_host_mutate_authorized": False,
                "model_execution_authorized": False,
                "memory_admission_authorized": False,
                "competence_promotion_authorized": False,
                "policy_effect": False,
            },
        )
        verification = verify_campaign_lifecycle(
            self.store, self.repo, "campaign-11"
        )
        self.assertFalse(verification["valid"])
        self.assertIn(
            "illegal_transition:start_requested->start_requested",
            verification["errors"],
        )
        self.assertFalse(verification["model_host_mutate_authorized"])
        self.assertFalse(verification["model_execution_authorized"])


if __name__ == "__main__":
    unittest.main()
