"""Adversarial tests for authenticated alpha.10 campaign control."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.campaign_control import (
    authorize_control_action,
    campaign_action_request,
    campaign_state,
    issue_control_session,
    prepare_campaign,
    revoke_control_session,
    transition_campaign_control,
)
from cortex.config import ensure_home
from cortex.epoch import ensure_current_epoch
from cortex.store import Store
from cortex.symbiosis import open_symbiotic_session
from cortex.will import register_will_principal


class V100Alpha10CampaignControlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.host = self.base / "host"
        self.host.mkdir()
        (self.host / "app.txt").write_text("alpha10\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=self.host, check=True)
        subprocess.run(
            ["git", "config", "user.email", "control@example.invalid"],
            cwd=self.host,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Control Fixture"],
            cwd=self.host,
            check=True,
        )
        subprocess.run(["git", "add", "."], cwd=self.host, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=self.host, check=True)
        self.home = ensure_home(self.base / "home")
        self.store = Store(self.home / "cortex.db")
        self.repo = "ControlHost"
        self.secret = "alpha10-operator-secret"
        bootstrap_repository(self.home, self.store, self.host, self.repo)
        register_will_principal(
            self.store,
            self.repo,
            "operator",
            "Local Operator",
            secret=self.secret,
        )
        ensure_current_epoch(self.store, self.repo, reason="alpha10-control-test")

    def tearDown(self) -> None:
        self.store.close()
        self.temporary.cleanup()

    def session(self, **overrides):
        values = {
            "principal_id": "operator",
            "principal_secret": self.secret,
            "allowed_actions": ("campaign.prepare", "campaign.cancel", "control.revoke"),
            "origin": "http://127.0.0.1:8791",
            "ttl_seconds": 300,
        }
        values.update(overrides)
        return issue_control_session(self.store, self.repo, **values)

    def authorize(self, session, action="campaign.prepare", nonce="nonce-1", **overrides):
        values = {
            "control_session_receipt_hash": session["receipt_hash"],
            "control_token": session["control_token"],
            "csrf_token": session["csrf_token"],
            "origin": "http://127.0.0.1:8791",
            "action": action,
            "action_nonce": nonce,
            "request": {"campaign_id": "campaign-1"},
        }
        values.update(overrides)
        return authorize_control_action(self.store, self.repo, **values)

    def canonical_root(self, kind: str):
        session = open_symbiotic_session(
            self.store,
            self.repo,
            task=f"alpha10 {kind}",
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
                "event_id": f"alpha10_{kind}",
                "body_epoch_id": session["body_epoch_id"],
            },
        )

    def authorize_request(self, session, action, nonce, request):
        return self.authorize(
            session,
            action=action,
            nonce=nonce,
            request=request,
        )

    def test_secrets_are_returned_once_but_never_persisted(self) -> None:
        session = self.session()
        canonical = self.store.symbiotic_receipt(session["receipt_hash"], repo=self.repo)
        self.assertIsNotNone(canonical)
        self.assertNotIn("control_token", canonical)
        self.assertNotIn("csrf_token", canonical)
        persisted = json.dumps(canonical, sort_keys=True)
        self.assertNotIn(session["control_token"], persisted)
        self.assertNotIn(session["csrf_token"], persisted)
        self.assertFalse(canonical["model_may_use_control_session"])
        self.assertFalse(canonical["model_host_mutate_authorized"])
        self.assertFalse(canonical["model_execution_authorized"])

    def test_wrong_principal_secret_and_nonloopback_origin_fail(self) -> None:
        with self.assertRaisesRegex(PermissionError, "principal secret mismatch"):
            self.session(principal_secret="attacker-secret")
        with self.assertRaisesRegex(PermissionError, "loopback"):
            self.session(origin="https://attacker.example")

    def test_caller_cannot_open_action_with_wrong_control_proof(self) -> None:
        session = self.session()
        for override, expected in (
            ({"control_token": "wrong"}, "control_token_mismatch"),
            ({"csrf_token": "wrong"}, "csrf_token_mismatch"),
            ({"origin": "http://localhost:8791"}, "control_origin_mismatch"),
            ({"action": "campaign.promote"}, "control_action_not_allowed"),
        ):
            with self.subTest(override=override):
                with self.assertRaisesRegex(PermissionError, expected):
                    self.authorize(session, nonce=f"nonce-{expected}", **override)

    def test_action_nonce_is_exactly_once(self) -> None:
        session = self.session()
        first = self.authorize(session)
        self.assertTrue(first["host_control_authorized"])
        self.assertTrue(first["exactly_once"])
        self.assertFalse(first["model_host_mutate_authorized"])
        self.assertFalse(first["model_execution_authorized"])
        with self.assertRaisesRegex(PermissionError, "action_nonce_replayed"):
            self.authorize(session)
        matches = [
            row
            for row in self.store.symbiotic_receipts_by_kind(
                self.repo, "campaign_control_action"
            )
            if row.get("action_nonce") == "nonce-1"
        ]
        self.assertEqual(len(matches), 1)

    def test_expiry_and_epoch_drift_fail_closed(self) -> None:
        session = self.session(ttl_seconds=30)
        with self.assertRaisesRegex(PermissionError, "control_session_expired"):
            self.authorize(
                session,
                nonce="expired",
                now=float(session["expires_at"]) + 1,
            )
        (self.host / "epoch-drift.txt").write_text("drift\n", encoding="utf-8")
        bootstrap_repository(self.home, self.store, self.host, self.repo)
        ensure_current_epoch(self.store, self.repo, reason="alpha10-epoch-drift")
        with self.assertRaisesRegex(PermissionError, "control_session_epoch_stale"):
            self.authorize(session, nonce="stale")

    def test_authenticated_revocation_closes_future_actions(self) -> None:
        session = self.session()
        revoke_action = self.authorize(
            session, action="control.revoke", nonce="revoke-nonce"
        )
        revocation = revoke_control_session(
            self.store,
            self.repo,
            action_authorization=revoke_action,
            reason="operator stop",
        )
        self.assertEqual(revocation["status"], "revoked")
        duplicate = revoke_control_session(
            self.store,
            self.repo,
            action_authorization=revoke_action,
            reason="replayed stop",
        )
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(duplicate["receipt_hash"], revocation["receipt_hash"])
        with self.assertRaisesRegex(PermissionError, "control_session_revoked"):
            self.authorize(session, nonce="after-revoke")

    def test_tampered_control_session_fails_canonical_verification(self) -> None:
        session = self.session()
        self.store.db.execute("DROP TRIGGER symbiotic_circulation_receipts_no_update")
        row = self.store.db.execute(
            "SELECT receipt_json FROM symbiotic_circulation_receipts WHERE receipt_hash=?",
            (session["receipt_hash"],),
        ).fetchone()
        body = json.loads(row["receipt_json"])
        body["allowed_actions"] = ["campaign.promote"]
        self.store.db.execute(
            "UPDATE symbiotic_circulation_receipts SET receipt_json=? WHERE receipt_hash=?",
            (json.dumps(body, sort_keys=True), session["receipt_hash"]),
        )
        self.store.db.commit()
        with self.assertRaisesRegex(PermissionError, "control_session_invalid"):
            self.authorize(session, nonce="tampered")

    def test_campaign_lifecycle_is_durable_bound_and_cancellable(self) -> None:
        session = self.session(allowed_actions=(
            "campaign.prepare",
            "campaign.start",
            "campaign.cancel",
        ))
        policy = self.canonical_root("autonomy_policy")
        storm = self.canonical_root("storm_summary")
        prepare_request = campaign_action_request(
            "campaign-1",
            "campaign.prepare",
            policy_receipt_hash=policy["receipt_hash"],
            storm_summary_receipt_hash=storm["receipt_hash"],
        )
        prepare_action = self.authorize_request(
            session, "campaign.prepare", "prepare", prepare_request
        )
        prepared = prepare_campaign(
            self.store,
            self.repo,
            campaign_id="campaign-1",
            policy_receipt_hash=policy["receipt_hash"],
            storm_summary_receipt_hash=storm["receipt_hash"],
            action_authorization=prepare_action,
        )
        self.assertEqual(prepared["status"], "prepared_request")
        self.assertFalse(prepared["campaign_execution_observed"])
        start_request = campaign_action_request(
            "campaign-1",
            "campaign.start",
            prior_state_receipt_hash=prepared["receipt_hash"],
            policy_receipt_hash=policy["receipt_hash"],
            storm_summary_receipt_hash=storm["receipt_hash"],
        )
        start_action = self.authorize_request(
            session, "campaign.start", "start", start_request
        )
        started = transition_campaign_control(
            self.store,
            self.repo,
            campaign_id="campaign-1",
            action="campaign.start",
            action_authorization=start_action,
        )
        self.assertEqual(started["status"], "start_requested")
        self.assertFalse(started["campaign_execution_observed"])
        cancel_request = campaign_action_request(
            "campaign-1",
            "campaign.cancel",
            prior_state_receipt_hash=started["receipt_hash"],
            policy_receipt_hash=policy["receipt_hash"],
            storm_summary_receipt_hash=storm["receipt_hash"],
        )
        cancel_action = self.authorize_request(
            session, "campaign.cancel", "cancel", cancel_request
        )
        cancelled = transition_campaign_control(
            self.store,
            self.repo,
            campaign_id="campaign-1",
            action="campaign.cancel",
            action_authorization=cancel_action,
        )
        self.assertEqual(cancelled["status"], "cancel_requested")
        self.assertTrue(cancelled["cooperative_stop_required"])
        self.assertEqual(cancelled["state_sequence"], 2)
        self.assertEqual(
            campaign_state(self.store, self.repo, "campaign-1")["receipt_hash"],
            cancelled["receipt_hash"],
        )
        self.assertFalse(cancelled["model_execution_authorized"])

    def test_lifecycle_action_cannot_be_rebound_or_reused(self) -> None:
        session = self.session()
        policy = self.canonical_root("autonomy_policy")
        storm = self.canonical_root("storm_summary")
        request = campaign_action_request(
            "campaign-1",
            "campaign.prepare",
            policy_receipt_hash=policy["receipt_hash"],
            storm_summary_receipt_hash=storm["receipt_hash"],
        )
        action = self.authorize_request(
            session, "campaign.prepare", "prepare-bound", request
        )
        with self.assertRaisesRegex(PermissionError, "request_mismatch"):
            prepare_campaign(
                self.store,
                self.repo,
                campaign_id="campaign-2",
                policy_receipt_hash=policy["receipt_hash"],
                storm_summary_receipt_hash=storm["receipt_hash"],
                action_authorization=action,
            )
        prepare_campaign(
            self.store,
            self.repo,
            campaign_id="campaign-1",
            policy_receipt_hash=policy["receipt_hash"],
            storm_summary_receipt_hash=storm["receipt_hash"],
            action_authorization=action,
        )
        with self.assertRaisesRegex(ValueError, "already exists"):
            prepare_campaign(
                self.store,
                self.repo,
                campaign_id="campaign-1",
                policy_receipt_hash=policy["receipt_hash"],
                storm_summary_receipt_hash=storm["receipt_hash"],
                action_authorization=action,
            )


if __name__ == "__main__":
    unittest.main()
