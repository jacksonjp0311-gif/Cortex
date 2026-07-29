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


class OrganismInterlinkTests(unittest.TestCase):
    def test_activate_emits_organism_pulse_chain(self) -> None:
        home = ensure_home(Path(tempfile.mkdtemp(prefix="org-")) / "home")
        repo = Path(tempfile.mkdtemp(prefix="org-repo-"))
        (repo / "README.md").write_text("# O\n\n## API\n\nBody.\n", encoding="utf-8")
        (repo / "core.py").write_text("def core() -> int:\n    return 1\n", encoding="utf-8")
        store = Store(home / "cortex.db")
        bootstrap_repository(home, store, repo, "OrgHost")
        first = activate_repository(
            home, store, Governor(home, store), "OrgHost", "First pulse", budget=500
        )
        org1 = first.get("organism") or {}
        self.assertEqual(org1.get("glyph"), "⊛")
        self.assertTrue(org1.get("co_process"))
        self.assertIn("pulse", org1)
        self.assertIn("body", org1)
        self.assertIn("nervous", org1["body"])
        self.assertIn("immune", org1["body"])
        self.assertIn("reflexes", org1["body"])
        ctx = first.get("context") or {}
        self.assertIn("organism", ctx)
        second = activate_repository(
            home, store, Governor(home, store), "OrgHost", "Second pulse", budget=500
        )
        org2 = second.get("organism") or {}
        self.assertEqual(org2.get("prior_pulse"), org1.get("pulse"))
        self.assertNotEqual(org2.get("pulse"), org1.get("pulse"))
        # Living: remember continues pulse (diastole)
        from cortex.hippocampus import remember
        from cortex.organism import breathe

        mem = remember(
            home, store, "OrgHost", "discovery", "living-beat-fact"
        )
        self.assertIn("organism_pulse", mem)
        self.assertTrue(mem.get("organism_pulse"))
        breath = breathe(
            home, store, Governor(home, store), "OrgHost", budget=400
        )
        self.assertEqual((breath.get("organism") or {}).get("phase"), "breathe")
        store.close()


class ProgressStackTests(unittest.TestCase):
    def test_profiles_and_control_error(self) -> None:
        from cortex.control_error import build_control_error
        from cortex.profiles import project_packet

        err = build_control_error(
            certificate={"status": "verified"},
            governance={"mode": "read_only"},
            manifest_current=True,
            retrieval_confidence=0.9,
            aria_materialization={"mode": "dormant"},
        )
        self.assertFalse(err["work_allowed"])
        self.assertTrue(err["must_reverify"])
        full = {
            "schema_version": "1.3",
            "task": "t",
            "repository": {"name": "R"},
            "governor": {"mode": "normal"},
            "control_error": err,
            "instructions": ["1"],
            "agent_protocol": {"hard_stops": [], "state": {"allowed_actions": ["read"]}},
            "evidence": [{"path": "a.py", "line_range": [1, 2], "kind": "source", "score": 1.0}],
            "aria_materialization": {"mode": "dormant", "materialized": False},
            "geometry": {"zero_point": True, "axes": {}},
            "efficiency": {},
            "packet_hash": "x",
        }
        agent = project_packet(full, "agent")
        minimal = project_packet(full, "minimal")
        debug = project_packet(full, "debug")
        self.assertEqual(agent["profile"], "agent")
        self.assertIn("control_error", agent)
        self.assertIn("governor", agent)
        self.assertEqual(minimal["profile"], "minimal")
        self.assertIn("evidence", minimal)
        self.assertEqual(debug["profile"], "debug")

    def test_remember_idempotent(self) -> None:
        home = ensure_home(Path(tempfile.mkdtemp(prefix="idem-")) / "home")
        repo = Path(tempfile.mkdtemp(prefix="idem-repo-"))
        (repo / "README.md").write_text("# I\n\n## API\n\nx\n", encoding="utf-8")
        (repo / "a.py").write_text("def a():\n    return 1\n", encoding="utf-8")
        store = Store(home / "cortex.db")
        bootstrap_repository(home, store, repo, "IdemHost")
        from cortex.session_ritual import run_session_ritual

        once = run_session_ritual(
            home,
            store,
            Governor(home, store),
            "IdemHost",
            "idempotent ritual",
            memories=[{"kind": "discovery", "text": "same-fact-twice"}],
            consolidate_session=True,
        )
        self.assertTrue(
            once["consolidate"].get("created")
            or once["consolidate"].get("status") == "created"
        )
        from cortex.hippocampus import remember

        # After consolidate, open a new session and verify de-dupe within it.
        activate_repository(
            home, store, Governor(home, store), "IdemHost", "retry session", budget=400
        )
        remember(home, store, "IdemHost", "discovery", "unique-once")
        third = remember(home, store, "IdemHost", "discovery", "unique-once")
        self.assertTrue(third.get("duplicate") or third.get("status") == "duplicate_skip")
        store.close()

    def test_progress_glyphs_registry(self) -> None:
        from cortex.progress_glyphs import progress_glyph_registry

        reg = progress_glyph_registry()
        self.assertGreaterEqual(len(reg["glyphs"]), 7)
        self.assertFalse(reg["automatic_execution"])


class TranscendProtocolTests(unittest.TestCase):
    def test_protocol_and_nexus_carry_agent_protocol(self) -> None:
        from cortex.context import build_context, cortex_context_protocol, nexus_packet

        home = ensure_home(Path(tempfile.mkdtemp(prefix="tx-")) / "home")
        repo = Path(tempfile.mkdtemp(prefix="tx-repo-"))
        (repo / "README.md").write_text("# T\n\n## API\n\nX\n", encoding="utf-8")
        (repo / "app.py").write_text("def f():\n    return 1\n", encoding="utf-8")
        store = Store(home / "cortex.db")
        bootstrap_repository(home, store, repo, "TxHost")
        ctx = build_context(
            home, store, Governor(home, store), "TxHost", "Protocol surface", 400
        )
        self.assertIn("agent_protocol", ctx)
        self.assertIn("entrypoints", ctx["agent_protocol"])
        proto = cortex_context_protocol(ctx)
        self.assertEqual(proto["protocol"], "cortex-context/1.1")
        self.assertIn("agent_protocol", proto)
        self.assertIn("instructions", proto)
        nexus = nexus_packet(ctx)
        self.assertIn("agent_protocol", nexus)
        self.assertIn("instructions", nexus)
        store.close()

    def test_read_only_instructions_force_stop(self) -> None:
        from cortex.context import _agent_instructions, _agent_protocol

        lines = _agent_instructions({}, {"mode": "read_only"})
        self.assertTrue(any("READ_ONLY" in line for line in lines))
        protocol = _agent_protocol(
            repo="R",
            task="t",
            aria_materialization={},
            governance={"mode": "read_only"},
            deferred_remaining=0,
        )
        self.assertFalse(protocol["state"]["work_allowed"])
        self.assertIn("repository_mutation", protocol["hard_stops"])
        constrained = _agent_instructions({}, {"mode": "constrained"})
        self.assertTrue(any("CONSTRAINED" in line for line in constrained))

    def test_mcp_exposes_ritual_and_activate_tools(self) -> None:
        from cortex.mcp import TOOLS

        names = {tool["name"] for tool in TOOLS}
        self.assertIn("cortex_ritual", names)
        self.assertIn("cortex_activate", names)
        self.assertIn("cortex_context", names)
        for tool in TOOLS:
            self.assertIn("mutation", tool["description"].casefold())


class SessionRitualTests(unittest.TestCase):
    def test_ritual_activate_remember_consolidate(self) -> None:
        from cortex.session_ritual import run_session_ritual

        home = ensure_home(Path(tempfile.mkdtemp(prefix="ritual-")) / "home")
        repo = Path(tempfile.mkdtemp(prefix="ritual-repo-"))
        (repo / "README.md").write_text("# Ritual\n\n## API\n\nRun helpers.\n", encoding="utf-8")
        (repo / "app.py").write_text("def run() -> str:\n    return 'ok'\n", encoding="utf-8")
        store = Store(home / "cortex.db")
        bootstrap_repository(home, store, repo, "RitualHost")
        result = run_session_ritual(
            home,
            store,
            Governor(home, store),
            "RitualHost",
            "Document the session ritual loop",
            memories=[
                {
                    "kind": "discovery",
                    "text": "Ritual closes activate-remember-consolidate on one substrate",
                }
            ],
            consolidate_session=True,
        )
        self.assertEqual(result["activation"], "ready")
        self.assertTrue(result["remembered"])
        self.assertTrue(result["consolidate"].get("created"))
        self.assertEqual(result["ritual"], ["activate", "remember", "consolidate"])
        self.assertFalse(result["authority"]["cortex_may_mutate"])
        packet = activate_repository(
            home,
            store,
            Governor(home, store),
            "RitualHost",
            "Inspect agent protocol",
            budget=400,
        )
        protocol = packet["context"].get("agent_protocol")
        self.assertIsNotNone(protocol)
        self.assertIn("steps", protocol)
        self.assertIn("new_memory_database", protocol["refuse"])
        store.close()
