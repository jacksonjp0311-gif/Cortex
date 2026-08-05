"""v8.3.3 production-path activation-conformance integration tests."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cortex.activation import activate_repository
from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.cli import main as cli_main
from cortex.governor import Governor
from cortex.ostt.conformance import (
    activation_cohort_report,
    activation_receipt_report,
    verify_activation_receipt,
)
from cortex.ostt.independent_verifier import independently_recompute_transition
from cortex.store import Store
from cortex.witness import ensure_witness_tables


def _host_source_manifest(root: Path) -> str:
    """Hash temporary host source while excluding Cortex-local integration state."""
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in {".cortex", ".git"} for part in relative.parts):
            continue
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _claim_flags(report: dict) -> tuple[bool, bool, bool]:
    return (
        bool(report.get("policy_effect")),
        bool(report.get("update_authorized")),
        bool(report.get("advisory_only")),
    )


class ActivationConformanceIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.home = ensure_home(self.base / "home")
        self.host = self.base / "production-host"
        self.host.mkdir()
        (self.host / "README.md").write_text(
            "# Production activation fixture\n", encoding="utf-8"
        )
        (self.host / "service.py").write_text(
            "def status():\n    return 'ready'\n", encoding="utf-8"
        )
        self.store = Store(self.home / "cortex.db")
        self.repo = "ActivationProductionHost"
        bootstrap_repository(self.home, self.store, self.host, self.repo)
        # A zero-row witness table is a valid measured coordinate. Its absence
        # is tested separately as an unavailable measurement.
        ensure_witness_tables(self.store)
        self.governor = Governor(self.home, self.store)

    def tearDown(self) -> None:
        self.store.close()
        self.temporary.cleanup()

    def _baseline(self, task: str = "paired activation case") -> dict:
        return activate_repository(
            self.home,
            self.store,
            self.governor,
            self.repo,
            task,
            budget=400,
            refresh="never",
            force_evidence_baseline=True,
        )

    def _advanced(self, task: str = "paired activation case") -> dict:
        return activate_repository(
            self.home,
            self.store,
            self.governor,
            self.repo,
            task,
            budget=400,
            refresh="never",
            memory_controller="advanced",
        )

    def _ledger_count(self) -> int:
        row = self.store.db.execute(
            "SELECT COUNT(*) AS n FROM activation_conformance_receipts WHERE repo=?",
            (self.repo,),
        ).fetchone()
        return int(row["n"])

    def _adaptive_counts(self) -> dict[str, float]:
        queries = {
            "neural_nodes": "SELECT COUNT(*) AS n FROM neural_nodes WHERE repo=?",
            "neural_synapses": "SELECT COUNT(*) AS n FROM neural_synapses WHERE repo=?",
            "prediction_traces": "SELECT COUNT(*) AS n FROM prediction_traces WHERE repo=?",
            "sessions": "SELECT COUNT(*) AS n FROM sessions WHERE repo=?",
            "ranker_training": (
                "SELECT COALESCE(SUM(train_count),0) AS n "
                "FROM ranker_models WHERE repo=?"
            ),
        }
        return {
            name: float(
                self.store.db.execute(sql, (self.repo,)).fetchone()["n"] or 0.0
            )
            for name, sql in queries.items()
        }

    def test_normal_evidence_baseline_activation_emits_one_receipt(self) -> None:
        count_before = self._ledger_count()
        result = self._baseline("baseline production receipt")
        receipt = result["ostt_residual_receipt"]
        self.assertNotIn("error", receipt, result)
        self.assertEqual(result["controller_execution"]["resolved"], "evidence_baseline")
        self.assertEqual(receipt["controller"], "evidence_baseline")
        self.assertEqual(receipt["comparison_arm"], "evidence_baseline")
        self.assertEqual(receipt["realized_action"], "evidence_only")
        self.assertEqual(receipt["input_type"], "ActivationObservationInput")
        self.assertEqual(receipt["output_type"], "MeasuredActivationTransition")
        self.assertEqual(receipt["status"], "conformance_measured")
        self.assertEqual(receipt["gate_state"], "CONFORMANCE_MEASURED")
        self.assertTrue(receipt["measurement_witness"]["passed"])
        self.assertTrue(receipt["inserted"])
        self.assertFalse(receipt["duplicate"])
        self.assertEqual(receipt["event_id"], result["measured_event_field"]["event_id"])
        self.assertEqual(self._ledger_count(), count_before + 1)
        rows = self.store.activation_conformance_receipts(
            self.repo, operator_id="activation_observation", limit=10
        )
        self.assertEqual(
            len([row for row in rows if row["event_id"] == receipt["event_id"]]),
            1,
        )
        self.assertEqual(_claim_flags(receipt), (False, False, True))

    def test_normal_advanced_activation_emits_same_schema_and_recomputes(self) -> None:
        baseline_result = self._baseline("same-schema paired case")
        baseline = baseline_result["ostt_residual_receipt"]
        host_before = _host_source_manifest(self.host)
        advanced_result = self._advanced("same-schema paired case")
        host_after = _host_source_manifest(self.host)
        advanced = advanced_result["ostt_residual_receipt"]
        self.assertNotIn("error", advanced, advanced_result)
        self.assertEqual(advanced_result["controller_execution"]["resolved"], "advanced")
        self.assertEqual(advanced["controller"], "advanced")
        self.assertEqual(advanced["comparison_arm"], "advanced")
        self.assertEqual(advanced["realized_action"], "bounded_adapt")
        self.assertEqual(advanced["status"], "conformance_measured")
        self.assertEqual(set(advanced), set(baseline))
        self.assertEqual(
            set(advanced["observed_output"]), set(baseline["observed_output"])
        )
        self.assertEqual(
            set(advanced["reference_output"]), set(baseline["reference_output"])
        )
        self.assertEqual(
            {item["invariant_id"] for item in advanced["invariant_results"]},
            {item["invariant_id"] for item in baseline["invariant_results"]},
        )
        recomputed = independently_recompute_transition(
            advanced["measured_transition"]["before_state"],
            advanced["measured_transition"]["after_state"],
        )
        self.assertEqual(
            recomputed["raw_delta"], advanced["measured_transition"]["raw_delta"]
        )
        self.assertEqual(
            recomputed["normalized_delta"],
            advanced["observed_output"],
        )
        self.assertEqual(
            recomputed["normalized_delta"],
            advanced["reference_output"],
        )
        self.assertTrue(advanced["residual_panel"]["conforms"])
        self.assertEqual(advanced["residual_panel"]["B_invalid"], 0.0)
        self.assertEqual(host_before, host_after)
        self.assertEqual(_claim_flags(advanced), (False, False, True))

    def test_baseline_activation_remains_sterile_while_observed(self) -> None:
        adaptive_before = self._adaptive_counts()
        host_before = _host_source_manifest(self.host)
        with mock.patch(
            "cortex.activation.index_repository",
            side_effect=AssertionError("baseline must not index"),
        ) as index_call, mock.patch(
            "cortex.connect_pass.record_connect_pass",
            side_effect=AssertionError("baseline must not run connect pass"),
        ) as connect_call, mock.patch(
            "cortex.cognitive.model.score_and_update",
            side_effect=AssertionError("baseline must not learn"),
        ) as learn_call:
            result = self._baseline("sterile baseline observation")
        receipt = result["ostt_residual_receipt"]
        adaptive_after = self._adaptive_counts()
        host_after = _host_source_manifest(self.host)
        index_call.assert_not_called()
        connect_call.assert_not_called()
        learn_call.assert_not_called()
        self.assertTrue(result["sterile_baseline"])
        self.assertEqual(adaptive_before, adaptive_after)
        self.assertEqual(host_before, host_after)
        self.assertEqual(receipt["status"], "conformance_measured")
        self.assertTrue(receipt["chain_valid"])
        self.assertEqual(_claim_flags(receipt), (False, False, True))

    def test_all_read_only_reports_preserve_claim_boundary_and_gate_c_cold(self) -> None:
        result = self._baseline("report boundary activation")
        receipt = result["ostt_residual_receipt"]
        receipt_hash = receipt["receipt_hash"]
        latest = activation_receipt_report(self.store, self.repo)
        cohort = activation_cohort_report(self.store, self.repo)
        verification = verify_activation_receipt(
            self.store, self.repo, receipt_hash
        )
        for report in (receipt, latest, cohort, verification):
            self.assertEqual(_claim_flags(report), (False, False, True), report)
        self.assertEqual(receipt["outcome_receipt"]["status"], "pending")
        self.assertFalse(receipt["outcome_receipt"]["required_for_conformance"])
        self.assertEqual(cohort["status"], "cold")
        self.assertEqual(cohort["receipt_count"], 1)
        self.assertEqual(cohort["remaining"], 15)
        self.assertEqual(verification["verification_status"], "verified")
        self.assertTrue(verification["receipt_hash_valid"])
        self.assertTrue(verification["chain_valid"])

    def test_ostt_inspection_cli_is_read_only(self) -> None:
        activation = self._baseline("read-only CLI case")
        receipt_hash = str(
            (activation.get("ostt_residual_receipt") or {}).get("receipt_hash") or ""
        )
        count_before = self._ledger_count()
        commands = (
            ["ostt", "activation-receipt", "--repo", self.repo, "--json"],
            ["ostt", "activation-cohort", "--repo", self.repo, "--json"],
            [
                "ostt",
                "verify-receipt",
                "--repo",
                self.repo,
                "--receipt",
                receipt_hash,
                "--json",
            ],
        )
        with mock.patch(
            "cortex.cli.activate_repository",
            side_effect=AssertionError("inspection must not execute activation"),
        ):
            for command in commands:
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    cli_main(["--home", str(self.home), *command])
                report = json.loads(output.getvalue())
                self.assertEqual(_claim_flags(report), (False, False, True))
        self.assertEqual(self._ledger_count(), count_before)


if __name__ == "__main__":
    unittest.main()
