"""v8.3.3 independent activation-conformance unit and failure tests."""

from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
import tempfile
import unittest
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.cognitive.measured import (
    COORDINATE_SCHEMA,
    COORDINATE_SCHEMA_METADATA,
    capture_measured_state,
    coordinate_schema_payload,
    measured_delta,
)
from cortex.config import ensure_home
from cortex.epoch import ensure_current_epoch
from cortex.ostt.conformance import (
    activation_cohort_report,
    build_activation_conformance_receipt,
    finalize_activation_observation,
    verify_activation_receipt,
)
from cortex.ostt.contracts import CORE_CONTRACTS
from cortex.ostt.independent_verifier import (
    CONFORMANCE_TOLERANCE,
    independently_recompute_transition,
    residual_panel,
)
from cortex.ostt.residuals import (
    REQUIRED_COMPARISON_MODES,
    REQUIRED_CONFORMANCE_INVARIANTS,
    ResidualReceipt,
    residual_evidence_report,
)
from cortex.store import Store
from cortex.witness import ensure_witness_tables


def _snapshot_hash(snapshot: dict) -> str:
    """Recreate the public state-hash material after a failure injection."""
    material = {
        "repo": snapshot.get("repo"),
        "repository_id": snapshot.get("repository_id"),
        "coordinate_schema_digest": snapshot.get("coordinate_schema_digest"),
        "values": dict(snapshot.get("values") or {}),
        "validity_mask": dict(snapshot.get("validity_mask") or {}),
        "failure_reasons": dict(snapshot.get("failure_reasons") or {}),
    }
    encoded = json.dumps(
        material,
        sort_keys=True,
        default=str,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _claim_flags(report: dict) -> tuple[bool, bool, bool]:
    return (
        bool(report.get("policy_effect")),
        bool(report.get("update_authorized")),
        bool(report.get("advisory_only")),
    )


class ActivationConformanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.home = ensure_home(self.base / "home")
        self.host = self.base / "host"
        self.host.mkdir()
        (self.host / "README.md").write_text("# v8.3.3 host\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        self.repo = "ConformanceHost"
        bootstrap_repository(self.home, self.store, self.host, self.repo)
        # This is a measured home-scoped coordinate. A count of zero is valid;
        # absence of its declared SQL table is not.
        ensure_witness_tables(self.store)
        self.epoch = ensure_current_epoch(
            self.store, self.repo, reason="activation_conformance_test"
        )
        self.before = capture_measured_state(self.store, self.repo)
        self.after = capture_measured_state(self.store, self.repo)

    def tearDown(self) -> None:
        self.store.close()
        self.temporary.cleanup()

    def _transition(
        self,
        event_id: str = "event-1",
        *,
        before: dict | None = None,
        after: dict | None = None,
    ) -> dict:
        return measured_delta(
            before or self.before,
            after or self.after,
            event_id=event_id,
            event_kind="activation_transaction",
        )

    def _build(
        self,
        event_id: str = "event-1",
        *,
        task: str | None = None,
        controller: str = "advanced",
        body_epoch: dict | None = None,
        transition: dict | None = None,
        measurement_cohort_id: str | None = None,
        host_manifest_before: str = "host-manifest",
        host_manifest_after: str = "host-manifest",
    ) -> dict:
        return build_activation_conformance_receipt(
            self.store,
            self.repo,
            task=task or f"task-{event_id}",
            controller=controller,
            realized_action=(
                "evidence_only"
                if controller == "evidence_baseline"
                else "bounded_adapt"
            ),
            capability_id="capability-test",
            pre_epoch_id=self.epoch.epoch_id,
            body_epoch=body_epoch or self.epoch.to_dict(),
            measured_transition=transition or self._transition(event_id),
            host_manifest_before=host_manifest_before,
            host_manifest_after=host_manifest_after,
            measurement_cohort_id=measurement_cohort_id,
        )

    def _verified_residual_receipt(
        self,
        *,
        arm: str,
        comparison_mode: str,
        case_task: str = "paired-production-case",
    ) -> ResidualReceipt:
        event_id = f"verified-{arm}-{comparison_mode}"
        candidate = self._build(
            event_id,
            task=case_task,
            controller=arm,
        )
        candidate["comparison_mode"] = comparison_mode
        canonical = self.store.append_activation_conformance_receipt(
            self.repo, candidate
        )
        verification = verify_activation_receipt(
            self.store, self.repo, canonical["receipt_hash"]
        )
        return ResidualReceipt.from_dict(
            {**canonical, "canonical_verification": verification}
        )

    def test_finalizer_uses_bound_opening_not_stale_cognitive_transition(self) -> None:
        stale_transition = self._transition("stale-cognitive-event")
        stale_before_hash = stale_transition["before_state"]["state_hash"]
        self.store.add_event(
            None,
            self.repo,
            "activation_opening_boundary",
            "advance measured state before the bound opening",
        )
        self.epoch = ensure_current_epoch(
            self.store, self.repo, reason="bound_activation_opening_test"
        )
        bound_before = capture_measured_state(self.store, self.repo)
        self.assertNotEqual(bound_before["state_hash"], stale_before_hash)
        activation = {
            "body_epoch": self.epoch.to_dict(),
            "measured_event_field": stale_transition,
        }

        receipt = finalize_activation_observation(
            self.store,
            self.repo,
            activation,
            task="bound activation opening",
            controller="advanced",
            realized_action="bounded_adapt",
            capability_id="capability-bound-opening",
            pre_epoch_id=self.epoch.epoch_id,
            before_state=bound_before,
            host_manifest_before="host-manifest",
            host_manifest_after="host-manifest",
        )

        observed_before = receipt["measured_transition"]["before_state"]
        self.assertEqual(observed_before["state_hash"], bound_before["state_hash"])
        self.assertNotEqual(observed_before["state_hash"], stale_before_hash)
        self.assertEqual(
            activation["measured_event_field"]["before_state"]["state_hash"],
            bound_before["state_hash"],
        )

    @staticmethod
    def _invariants(failed: str | None = None) -> tuple[dict, ...]:
        return tuple(
            {
                "invariant_id": invariant_id,
                "passed": invariant_id != failed,
                "evidence_ids": [f"evidence-{invariant_id}"],
                "expected": True,
                "observed": invariant_id != failed,
                "reason": "deterministic test projection",
            }
            for invariant_id in sorted(REQUIRED_CONFORMANCE_INVARIANTS)
        )

    @staticmethod
    def _witness() -> dict:
        return {
            "witness_id": "measurement-witness",
            "witness_kind": "MEASUREMENT",
            "verifier": "cortex.ostt.independent_verifier",
            "subject_receipt_hash": "subject-hash",
            "evidence_hashes": ["before", "after", "schema", "verifier"],
            "passed": True,
            "issued_at": 1.0,
        }

    def _residual_receipt(
        self,
        *,
        arm: str = "advanced",
        case_id: str = "paired-case",
        schema_digest: str = "schema-a",
        comparison_mode: str = "ostt",
        failed_invariant: str | None = None,
    ) -> ResidualReceipt:
        output = {"events": 0.0, "sessions": 0.0}
        return ResidualReceipt(
            operator_id="activation_observation",
            input_type="ActivationObservationInput",
            output_type="MeasuredActivationTransition",
            status="conformance_measured",
            observed_output=output,
            reference_output=dict(output),
            invariant_results=self._invariants(failed_invariant),
            epoch_id="epoch-1",
            cohort_id="cohort-1",
            coordinate_schema_digest=schema_digest,
            repository_id="repo-id-conformance",
            repo=self.repo,
            case_id=case_id,
            comparison_arm=arm,
            measurement_witness=self._witness(),
            approximation_mode="exact",
            comparison_mode=comparison_mode,
            valid_fraction=1.0,
            b_rms=0.0,
            b_max=0.0,
            b_invalid=0.0,
            channel_burdens={"O_OPERATIONS": 0.0, "T_TASK": 0.0},
            epsilon=1e-12,
        )

    def test_coordinate_schema_is_ordered_frozen_and_digest_bound(self) -> None:
        required_fields = {
            "coordinate_id",
            "scalar_type",
            "measurement_source",
            "operational_unit",
            "channel_family",
            "normalization_scale",
            "null_allowed",
            "required_for_conformance",
            "criticality_weight",
            "schema_version",
        }
        payload = coordinate_schema_payload()
        names = [coordinate.coordinate_id for coordinate in COORDINATE_SCHEMA]
        self.assertEqual(payload, COORDINATE_SCHEMA_METADATA)
        self.assertEqual(payload["ordered_coordinate_names"], names)
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(len(payload["coordinate_schema_digest"]), 64)
        self.assertEqual(len(payload["shape_signature_digest"]), 64)
        self.assertEqual(len(payload["scale_digest"]), 64)
        self.assertTrue(
            all(required_fields == set(coordinate.to_dict()) for coordinate in COORDINATE_SCHEMA)
        )
        with self.assertRaises(FrozenInstanceError):
            COORDINATE_SCHEMA[0].coordinate_id = "mutated"  # type: ignore[misc]

    def test_raw_snapshots_independently_reproduce_persisted_delta(self) -> None:
        transition = self._transition()
        recomputed = independently_recompute_transition(
            transition["before_state"], transition["after_state"]
        )
        panel = residual_panel(
            transition["normalized_delta"],
            recomputed["normalized_delta"],
            recomputed["coordinate_validity"],
        )
        self.assertEqual(recomputed["raw_delta"], transition["raw_delta"])
        self.assertEqual(
            recomputed["normalized_delta"], transition["normalized_delta"]
        )
        self.assertTrue(recomputed["before_hash_valid"])
        self.assertTrue(recomputed["after_hash_valid"])
        self.assertTrue(panel["conforms"])
        self.assertLessEqual(panel["B_rms"], CONFORMANCE_TOLERANCE)
        self.assertLessEqual(panel["B_max"], CONFORMANCE_TOLERANCE)
        self.assertEqual(panel["B_invalid"], 0.0)
        self.assertTrue(
            all(value == 0.0 for value in panel["channel_burdens"].values())
        )

    def test_missing_sql_table_is_null_and_invalid_never_zero(self) -> None:
        self.store.db.execute("DROP TABLE prediction_traces")
        self.store.db.commit()
        snapshot = capture_measured_state(self.store, self.repo)
        self.assertIsNone(snapshot["values"]["prediction_traces"])
        self.assertIsNot(snapshot["values"]["prediction_traces"], 0.0)
        self.assertFalse(snapshot["validity_mask"]["prediction_traces"])
        self.assertIn(
            "OperationalError", snapshot["failure_reasons"]["prediction_traces"]
        )
        self.assertEqual(snapshot["valid_count"], snapshot["required_count"] - 1)
        self.assertLess(snapshot["valid_fraction"], 1.0)

    def test_invalid_required_coordinate_blocks_conformance(self) -> None:
        after = copy.deepcopy(self.after)
        after["values"]["prediction_traces"] = None
        after["validity_mask"]["prediction_traces"] = False
        after["failure_reasons"]["prediction_traces"] = "InjectedCoordinateFailure"
        after["valid_count"] -= 1
        after["valid_fraction"] = after["valid_count"] / after["required_count"]
        after["state_hash"] = _snapshot_hash(after)
        transition = self._transition(after=after)
        receipt = self._build(transition=transition)
        invariants = {
            item["invariant_id"]: item for item in receipt["invariant_results"]
        }
        self.assertEqual(transition["status"], "observed_incomplete")
        self.assertIsNone(transition["normalized_delta"]["prediction_traces"])
        self.assertFalse(transition["baseline_eligible"])
        self.assertFalse(transition["policy_eligible"])
        self.assertFalse(invariants["measurement_complete"]["passed"])
        self.assertEqual(receipt["status"], "observed_incomplete")
        self.assertFalse(receipt["evidence_ready"])
        self.assertFalse(receipt["measurement_witness"]["passed"])
        self.assertFalse(receipt["policy_effect"])
        self.assertFalse(receipt["update_authorized"])

    def test_equal_flat_length_list_and_mapping_are_not_same_shape(self) -> None:
        with self.assertRaisesRegex(ValueError, "different structural shapes"):
            ResidualReceipt.measure(
                operator_id="activation_observation",
                input_type="ActivationObservationInput",
                output_type="MeasuredActivationTransition",
                known_output=[1.0, 2.0],
                observed_output={"a": 1.0, "b": 2.0},
                uncertainty=0.0,
                uncertainty_calibrated=True,
                invariant_projection={"ok": True},
            )

    def test_coordinate_schema_drift_is_an_incompatible_partition(self) -> None:
        report = residual_evidence_report(
            CORE_CONTRACTS,
            [
                self._residual_receipt(
                    arm="evidence_baseline", schema_digest="schema-a"
                ),
                self._residual_receipt(arm="advanced", schema_digest="schema-b"),
            ],
        )
        self.assertEqual(report["paired_case_count"], 0)
        self.assertEqual(report["incompatible_receipt_count"], 2)
        self.assertTrue(report["cross_partition_cases"])
        self.assertFalse(report["gates"]["comparison_matrix"])

    def test_stale_epoch_identifier_fails_named_invariant(self) -> None:
        stale = self.epoch.to_dict()
        stale["epoch_id"] = "stale-epoch"
        receipt = self._build(body_epoch=stale)
        invariants = {
            item["invariant_id"]: item for item in receipt["invariant_results"]
        }
        self.assertFalse(invariants["epoch_current"]["passed"])
        self.assertEqual(receipt["status"], "observed_incomplete")
        self.assertFalse(receipt["evidence_ready"])

    def test_stale_cohort_identifier_fails_named_invariant(self) -> None:
        receipt = self._build(measurement_cohort_id="stale-cohort")
        invariants = {
            item["invariant_id"]: item for item in receipt["invariant_results"]
        }
        self.assertFalse(invariants["cohort_current"]["passed"])
        self.assertEqual(receipt["status"], "observed_incomplete")

    def test_host_manifest_change_fails_host_immutability(self) -> None:
        receipt = self._build(
            host_manifest_before="host-before", host_manifest_after="host-after"
        )
        invariants = {
            item["invariant_id"]: item for item in receipt["invariant_results"]
        }
        self.assertFalse(invariants["host_immutable"]["passed"])
        self.assertEqual(invariants["host_immutable"]["expected"], "host-before")
        self.assertEqual(invariants["host_immutable"]["observed"], "host-after")
        self.assertEqual(receipt["status"], "observed_incomplete")

    def test_duplicate_operator_event_append_is_exactly_once(self) -> None:
        receipt = self._build("duplicate-event")
        first = self.store.append_activation_conformance_receipt(self.repo, receipt)
        duplicate = self.store.append_activation_conformance_receipt(self.repo, receipt)
        count = self.store.db.execute(
            """
            SELECT COUNT(*) AS n FROM activation_conformance_receipts
            WHERE repo=? AND operator_id=? AND event_id=?
            """,
            (self.repo, receipt["operator_id"], receipt["event_id"]),
        ).fetchone()["n"]
        self.assertTrue(first["inserted"])
        self.assertFalse(first["duplicate"])
        self.assertFalse(duplicate["inserted"])
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(first["receipt_hash"], duplicate["receipt_hash"])
        self.assertEqual(count, 1)

    def test_canonical_receipt_rows_reject_every_update_and_delete(self) -> None:
        appended = self.store.append_activation_conformance_receipt(
            self.repo, self._build("immutable-event")
        )
        triggers = {
            row["name"]
            for row in self.store.db.execute(
                "SELECT name FROM sqlite_master WHERE type='trigger'"
            ).fetchall()
        }
        self.assertIn("activation_conformance_receipts_no_update", triggers)
        self.assertIn("activation_conformance_receipts_no_delete", triggers)
        self.assertNotIn(
            "activation_conformance_receipt_identity_immutable", triggers
        )
        with self.assertRaisesRegex(
            sqlite3.IntegrityError,
            "canonical activation conformance receipts cannot be updated",
        ):
            self.store.db.execute(
                "UPDATE activation_conformance_receipts SET status=? WHERE receipt_hash=?",
                ("observed_incomplete", appended["receipt_hash"]),
            )
        self.store.db.rollback()
        with self.assertRaisesRegex(
            sqlite3.IntegrityError,
            "canonical activation conformance receipts cannot be deleted",
        ):
            self.store.db.execute(
                "DELETE FROM activation_conformance_receipts WHERE receipt_hash=?",
                (appended["receipt_hash"],),
            )
        self.store.db.rollback()

    def test_chain_tip_partition_identity_is_immutable(self) -> None:
        appended = self.store.append_activation_conformance_receipt(
            self.repo, self._build("immutable-tip-event")
        )
        with self.assertRaisesRegex(
            sqlite3.IntegrityError,
            "activation conformance chain-tip identity cannot be updated",
        ):
            self.store.db.execute(
                """
                UPDATE activation_conformance_chain_tips
                SET repo=? WHERE tip_receipt_hash=?
                """,
                ("wrong-repo", appended["receipt_hash"]),
            )
        self.store.db.rollback()

    def test_unbound_conformance_claim_is_rejected_before_append(self) -> None:
        arbitrary_claim = {
            "operator_id": "activation_observation",
            "event_id": "unbound-event",
            "case_id": "unbound-case",
            "comparison_arm": "advanced",
            "body_epoch_id": self.epoch.epoch_id,
            "measurement_cohort_id": "unbound-cohort",
            "coordinate_schema_digest": COORDINATE_SCHEMA_METADATA[
                "coordinate_schema_digest"
            ],
            "status": "conformance_measured",
        }
        with self.assertRaisesRegex(ValueError, "not independently valid"):
            self.store.append_activation_conformance_receipt(
                self.repo, arbitrary_claim
            )
        count = self.store.db.execute(
            "SELECT COUNT(*) AS n FROM activation_conformance_receipts"
        ).fetchone()["n"]
        self.assertEqual(count, 0)

    def test_candidate_is_promoted_only_at_transactional_append(self) -> None:
        candidate = self._build("candidate-event")
        self.assertEqual(candidate["status"], "conformance_candidate")
        self.assertFalse(candidate["evidence_ready"])
        self.assertFalse(candidate["conformance_ready"])
        pending = {
            result["invariant_id"]: result
            for result in candidate["invariant_results"]
        }
        self.assertFalse(pending["exactly_once_event"]["passed"])
        self.assertFalse(pending["receipt_hash_valid"]["passed"])

        canonical = self.store.append_activation_conformance_receipt(
            self.repo, candidate
        )
        invariants = {
            result["invariant_id"]: result
            for result in canonical["invariant_results"]
        }
        self.assertEqual(canonical["status"], "conformance_measured")
        self.assertEqual(canonical["gate_state"], "CONFORMANCE_MEASURED")
        self.assertTrue(canonical["evidence_ready"])
        self.assertTrue(canonical["conformance_ready"])
        self.assertTrue(canonical["inserted"])
        self.assertTrue(invariants["exactly_once_event"]["passed"])
        self.assertEqual(
            invariants["exactly_once_event"]["observed"],
            "enforced_by_transactional_ledger",
        )
        self.assertTrue(invariants["receipt_hash_valid"]["passed"])
        self.assertEqual(
            invariants["receipt_hash_valid"]["observed"],
            "verified_on_ledger_append_and_read",
        )
        self.assertEqual(
            canonical["ledger_admission"]["admission_status"], "verifier_bound"
        )
        self.assertEqual(
            canonical["ledger_admission"]["submitted_status"],
            "conformance_candidate",
        )

    def test_tampered_receipt_content_fails_hash_verification(self) -> None:
        appended = self.store.append_activation_conformance_receipt(
            self.repo, self._build("tampered-event")
        )
        receipt_hash = appended["receipt_hash"]
        row = self.store.db.execute(
            "SELECT receipt_json FROM activation_conformance_receipts WHERE receipt_hash=?",
            (receipt_hash,),
        ).fetchone()
        payload = json.loads(row["receipt_json"])
        payload["realized_action"] = "tampered"
        # Simulate offline corruption after bypassing the runtime append-only
        # trigger. Normal Store users cannot update a canonical row.
        self.store.db.execute(
            "DROP TRIGGER activation_conformance_receipts_no_update"
        )
        self.store.db.execute(
            "UPDATE activation_conformance_receipts SET receipt_json=? WHERE receipt_hash=?",
            (json.dumps(payload, sort_keys=True), receipt_hash),
        )
        self.store.db.commit()
        verification = verify_activation_receipt(
            self.store, self.repo, receipt_hash
        )
        self.assertEqual(verification["verification_status"], "failed")
        self.assertFalse(verification["receipt_hash_valid"])
        self.assertFalse(verification["chain_valid"])

    def test_broken_previous_hash_linkage_fails_chain_verification(self) -> None:
        first = self.store.append_activation_conformance_receipt(
            self.repo, self._build("chain-event-1")
        )
        second = self.store.append_activation_conformance_receipt(
            self.repo, self._build("chain-event-2")
        )
        self.assertEqual(second["previous_receipt_hash"], first["receipt_hash"])
        # Simulate offline corruption; the normal update surface is blocked.
        self.store.db.execute(
            "DROP TRIGGER activation_conformance_receipts_no_update"
        )
        self.store.db.execute(
            """
            UPDATE activation_conformance_receipts
            SET previous_receipt_hash=? WHERE receipt_hash=?
            """,
            ("f" * 64, second["receipt_hash"]),
        )
        self.store.db.commit()
        receipt = second
        chain = self.store.verify_activation_conformance_chain(
            self.repo,
            receipt["operator_id"],
            receipt["body_epoch_id"],
            receipt["measurement_cohort_id"],
            receipt["coordinate_schema_digest"],
        )
        self.assertFalse(chain["valid"])
        self.assertIn(second["receipt_hash"], chain["invalid_receipt_hashes"])

    def test_chain_verification_returns_invalid_for_malformed_sqlite_values(self) -> None:
        appended = self.store.append_activation_conformance_receipt(
            self.repo, self._build("malformed-row-event")
        )
        self.store.db.execute(
            "DROP TRIGGER activation_conformance_receipts_no_update"
        )
        # Explicit test-only bypass: production code cannot rewrite partition
        # identity, but verification must still fail closed on offline damage.
        self.store.db.execute(
            "DROP TRIGGER activation_conformance_chain_tip_identity_immutable"
        )
        self.store.db.execute(
            """
            UPDATE activation_conformance_receipts
            SET receipt_json=?, chain_sequence=?, created_at=?
            WHERE receipt_hash=?
            """,
            (
                sqlite3.Binary(b"\x80"),
                "not-an-integer",
                "not-a-number",
                appended["receipt_hash"],
            ),
        )
        self.store.db.execute(
            """
            UPDATE activation_conformance_chain_tips
            SET receipt_count=?, repo=?
            WHERE tip_receipt_hash=?
            """,
            ("not-an-integer", "wrong-repo", appended["receipt_hash"]),
        )
        self.store.db.commit()
        chain = self.store.verify_activation_conformance_chain(
            self.repo,
            appended["operator_id"],
            appended["body_epoch_id"],
            appended["measurement_cohort_id"],
            appended["coordinate_schema_digest"],
        )
        self.assertFalse(chain["valid"])
        self.assertTrue(
            any("receipt_json_invalid" in error for error in chain["errors"])
        )
        self.assertIn("chain_tip_count_invalid", chain["errors"])
        self.assertIn("chain_tip_partition_mismatch:repo", chain["errors"])

    def test_chain_verification_rejects_coercible_scalars_and_surrogate_json(self) -> None:
        appended = self.store.append_activation_conformance_receipt(
            self.repo, self._build("malformed-scalar-event")
        )
        self.store.db.execute(
            "DROP TRIGGER activation_conformance_receipts_no_update"
        )
        # SQLite's numeric converters accept these BLOBs. Verification must
        # require actual ledger scalar types and must not throw on a JSON lone
        # surrogate that cannot be encoded as canonical UTF-8.
        self.store.db.execute(
            """
            UPDATE activation_conformance_receipts
            SET receipt_json=?, chain_sequence=?, created_at=?
            WHERE receipt_hash=?
            """,
            (
                '{"bad":"\\ud800"}',
                sqlite3.Binary(b"1"),
                sqlite3.Binary(b"1.0"),
                appended["receipt_hash"],
            ),
        )
        self.store.db.execute(
            """
            UPDATE activation_conformance_chain_tips
            SET receipt_count=?, updated_at=?
            WHERE tip_receipt_hash=?
            """,
            (
                sqlite3.Binary(b"1"),
                sqlite3.Binary(b"1.0"),
                appended["receipt_hash"],
            ),
        )
        self.store.db.commit()

        chain = self.store.verify_activation_conformance_chain(
            self.repo,
            appended["operator_id"],
            appended["body_epoch_id"],
            appended["measurement_cohort_id"],
            appended["coordinate_schema_digest"],
        )
        self.assertFalse(chain["valid"])
        errors = chain["errors"]
        self.assertTrue(any("receipt_json_invalid" in error for error in errors))
        self.assertTrue(any("chain_sequence_invalid" in error for error in errors))
        self.assertTrue(any("created_at_invalid" in error for error in errors))
        self.assertIn("chain_tip_count_invalid", errors)
        self.assertIn("chain_tip_updated_at_invalid", errors)

    def test_chain_verification_binds_exact_repository_name_and_identity(self) -> None:
        appended = self.store.append_activation_conformance_receipt(
            self.repo, self._build("repo-binding-event")
        )
        repository = self.store.repo(self.repo)
        alias = "ConformanceAlias"
        self.store.db.execute(
            """
            INSERT INTO repositories(name, repository_id, path, attached_at)
            VALUES(?, ?, ?, ?)
            """,
            (
                alias,
                repository["repository_id"],
                repository["path"],
                1.0,
            ),
        )
        self.store.db.commit()
        chain = self.store.verify_activation_conformance_chain(
            alias,
            appended["operator_id"],
            appended["body_epoch_id"],
            appended["measurement_cohort_id"],
            appended["coordinate_schema_digest"],
        )
        self.assertFalse(chain["valid"])
        self.assertTrue(
            any(
                "partition_field_mismatch:repo" in error
                for error in chain["errors"]
            )
        )
        self.assertIn("chain_tip_partition_mismatch:repo", chain["errors"])
        self.assertIsNone(
            self.store.activation_conformance_receipt(
                appended["receipt_hash"], repo=alias
            )
        )

    def test_missing_structured_measurement_witness_blocks_conformance(self) -> None:
        receipt = replace(self._residual_receipt(), measurement_witness={})
        self.assertIn("measurement_witness_missing", receipt.validation_errors())
        self.assertFalse(receipt.evidence_ready)

    def test_per_invariant_failure_names_only_the_failed_projection(self) -> None:
        receipt = self._residual_receipt(failed_invariant="host_immutable")
        failures = [
            error
            for error in receipt.validation_errors()
            if error.startswith("invariant_failed:")
        ]
        self.assertEqual(failures, ["invariant_failed:host_immutable"])
        self.assertFalse(receipt.evidence_ready)

    def test_unpaired_comparison_arms_fail_matrix(self) -> None:
        receipts = [
            self._residual_receipt(arm="advanced", comparison_mode=mode)
            for mode in sorted(REQUIRED_COMPARISON_MODES)
        ]
        report = residual_evidence_report(CORE_CONTRACTS, receipts)
        self.assertEqual(report["paired_case_count"], 0)
        self.assertEqual(report["unpaired_case_count"], 1)
        self.assertFalse(report["gates"]["comparison_matrix"])
        self.assertEqual(report["cohort_statuses"][0]["status"], "unpaired")

    def test_gate_c_is_cold_below_sixteen_compatible_receipts(self) -> None:
        self.store.append_activation_conformance_receipt(
            self.repo, self._build("cold-cohort-event")
        )
        report = activation_cohort_report(self.store, self.repo)
        self.assertEqual(report["status"], "cold")
        self.assertEqual(report["receipt_count"], 1)
        self.assertEqual(report["required_count"], 16)
        self.assertEqual(report["remaining"], 15)
        self.assertEqual(_claim_flags(report), (False, False, True))

    def test_one_ready_operator_does_not_claim_global_readiness(self) -> None:
        receipts = [
            self._verified_residual_receipt(
                arm=arm,
                comparison_mode=mode,
            )
            for arm in ("evidence_baseline", "advanced")
            for mode in sorted(REQUIRED_COMPARISON_MODES)
        ]
        report = residual_evidence_report(CORE_CONTRACTS, receipts)
        activation = report["operator_statuses"]["activation_observation"]
        self.assertEqual(activation["status"], "conformance_ready")
        self.assertEqual(report["ready_count"], 1)
        self.assertEqual(report["measured_count"], 1)
        self.assertEqual(report["status"], "conformance_measured_shadow")
        self.assertFalse(report["gates"]["global_operator_evidence"])
        self.assertFalse(report["update_authorized"])
        self.assertEqual(_claim_flags(report), (False, False, True))

    def test_asserted_unbound_conformance_never_becomes_ready(self) -> None:
        forged = self._residual_receipt()
        self.assertFalse(forged.evidence_ready)
        self.assertIn("conformance_payload_missing", forged.validation_errors())
        self.assertIn("canonical_verification_missing", forged.validation_errors())
        report = residual_evidence_report(CORE_CONTRACTS, [forged])
        self.assertEqual(
            report["operator_statuses"]["activation_observation"]["status"],
            "measured_incomplete",
        )
        self.assertEqual(report["ready_count"], 0)


if __name__ == "__main__":
    unittest.main()
