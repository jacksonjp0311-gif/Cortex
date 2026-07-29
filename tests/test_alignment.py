"""Aligned geometry gates: covenant interlocks under stress."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cortex.activation import activate_repository
from cortex.aria_meta.evaluation import evaluate_aria_corpus, load_aria_corpus
from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home, load_repo_config
from cortex.governor import Governor
from cortex.retrieval import query
from cortex.store import Store
from cortex.verify import verify_repository


class AlignmentGeometryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.home = ensure_home(self.base / "home")
        self.repo = self.base / "aligned-host"
        self.repo.mkdir()
        (self.repo / "README.md").write_text(
            "# Aligned Host\n\n## Architecture\n\nCore loop.\n\n"
            "## Native ARIA semantic language\n\nProbe bait heading.\n",
            encoding="utf-8",
        )
        (self.repo / "service.py").write_text(
            "def run() -> str:\n    return 'ready'\n",
            encoding="utf-8",
        )
        vendor = self.repo / "cortex" / "aria_meta" / "vendor"
        (vendor / "docs").mkdir(parents=True)
        (vendor / "grammar").mkdir(parents=True)
        for name, body in {
            "ARIA-RUNTIME.json": "{}",
            "ARIA-CONNECT.json": "{}",
            "README.md": "# ARIA\n",
            "AGENTS.md": "# a\n",
            "VERSION": "0\n",
            "MANIFEST.sha256": "",
            "aria.policy.json": "{}",
            "aria.lock.json": "{}",
        }.items():
            (vendor / name).write_text(body, encoding="utf-8")
        (vendor / "grammar" / "semantic-cues.json").write_text(
            json.dumps({"format": "t", "cues": []}), encoding="utf-8"
        )
        (vendor / "grammar" / "glyphs.json").write_text("{}", encoding="utf-8")
        (vendor / "grammar" / "glyph-cards.json").write_text("{}", encoding="utf-8")
        (vendor / "grammar" / "opcodes.json").write_text("{}", encoding="utf-8")
        for index in range(8):
            (vendor / "docs" / f"continuity-{index}.md").write_text(
                "# Continuity\n\nSemantic replay and session handoff details.\n",
                encoding="utf-8",
            )
        self.store = Store(self.home / "cortex.db")
        self.boot = bootstrap_repository(
            self.home, self.store, self.repo, "AlignedHost"
        )

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_verify_probes_do_not_materialize_aria_bulk(self) -> None:
        deferred_before = sum(
            1
            for row in self.store.files("AlignedHost")
            if row["status"] == "substrate_deferred"
        )
        self.assertGreaterEqual(deferred_before, 5)
        config = load_repo_config(self.repo)
        certificate = verify_repository(
            self.home, self.store, "AlignedHost", config, write_certificate=False
        )
        self.assertEqual(certificate["status"], "verified")
        deferred_after = sum(
            1
            for row in self.store.files("AlignedHost")
            if row["status"] == "substrate_deferred"
        )
        self.assertEqual(deferred_after, deferred_before)

    def test_aria_wake_meets_evidence_floor(self) -> None:
        hits = query(
            self.store,
            "AlignedHost",
            "Use ARIA semantic replay for cooperative mesh session handoff",
            limit=12,
            materialize_substrate=True,
        )
        aria_paths = [
            hit.path
            for hit in hits
            if hit.path.replace("\\", "/").startswith("cortex/aria_meta/vendor/")
        ]
        self.assertGreaterEqual(len(aria_paths), 2, aria_paths)

    def test_geometry_surface_on_context(self) -> None:
        packet = activate_repository(
            self.home,
            self.store,
            Governor(self.home, self.store),
            "AlignedHost",
            "Fix Python service readiness",
            budget=600,
        )
        context = packet["context"]
        self.assertIn("geometry", context)
        self.assertTrue(context["geometry"]["zero_point"])
        self.assertIn("aria_materialization", context)
        self.assertEqual(context["aria_materialization"]["mode"], "dormant")
        authority = context["governor"].get("authority") or {}
        self.assertIsNot(authority.get("cortex_may_authorize_mutation"), True)

    def test_fluency_corpus_min_size_and_zero_errors(self) -> None:
        corpus = (
            Path(__file__).resolve().parents[1]
            / "benchmarks"
            / "corpora"
            / "aria_fluency.json"
        )
        result = evaluate_aria_corpus(load_aria_corpus(corpus))
        self.assertGreaterEqual(result["cases"], 40)
        self.assertEqual(result["false_wakes"], 0, result)
        self.assertEqual(result["missed_wakes"], 0, result)


class ForeignHostMatrixTests(unittest.TestCase):
    def test_foreign_hosts_pass_organ_gates(self) -> None:
        from benchmarks.foreign_host_matrix import run_matrix

        payload = run_matrix()
        self.assertTrue(payload["all_passed"], payload)
        self.assertEqual(payload["passed"], payload["total"])
        self.assertGreaterEqual(payload["total"], 5)


class ResonanceContactTests(unittest.TestCase):
    def test_resonance_bright_when_all_strings_high(self) -> None:
        from cortex.resonance import resonance_intensity

        field = resonance_intensity(
            glow=True,
            break_count=0,
            savings_ratio=0.65,
            deferred_holds=True,
            aria_evidence_count=4,
            geometry_zero_point=True,
            fluency_perfect=True,
            foreign_pass_rate=1.0,
            generic_activate_s=1.2,
            aria_activate_s=5.0,
            bootstrap_s=4.5,
        )
        self.assertTrue(field["glow"])
        self.assertGreaterEqual(field["glow_intensity"], 0.90)
        self.assertEqual(field["brightness"], "bright")
