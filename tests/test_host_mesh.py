"""Host mesh multi-repo observe."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.governor import Governor
from cortex.host_mesh import observe_host, run_host_mesh, set_mesh_role
from cortex.store import Store
from cortex.topology_law import G_LEARNED, classify_edge_kind, topology_law_packet


class HostMeshTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.home = ensure_home(self.base / "home")
        self.engine = Path(__file__).resolve().parents[1]
        self.store = Store(self.home / "cortex.db")
        bootstrap_repository(
            self.home,
            self.store,
            self.engine,
            "MeshHost",
            force=True,
            external=True,
        )
        self.gov = Governor(self.home, self.store)

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_observe_and_mesh(self) -> None:
        one = observe_host(
            self.home, self.store, self.gov, "MeshHost", measure_coherence_field=True
        )
        self.assertTrue(one["attached"])
        self.assertTrue(one["path_exists"])
        self.assertIn(one["role"], {"engine_tree", "engine_alias", "durable_body", "foreign_host"})

        report = run_host_mesh(
            self.home,
            self.store,
            self.gov,
            primary_repo="MeshHost",
            query="governor ranker spectral",
            measure_coherence_field=False,
            persist=True,
        )
        self.assertEqual(report["schema_version"], "cortex-host-mesh/1.1")
        self.assertGreaterEqual(report["host_count"], 1)
        self.assertTrue(report["directives"])
        self.assertIn("next", report)
        self.assertIn("epoch_alignment", report)
        cont = one.get("continuity") or {}
        self.assertIn("observe_only", cont)
        # body_epoch_id present only after seal; observe path must not force seal
        self.assertTrue(
            cont.get("body_epoch_id") is not None
            or cont.get("epoch_present") is False
            or cont.get("error")
        )

    def test_explicit_mesh_role_and_topology_law(self) -> None:
        meta = set_mesh_role(self.store, "MeshHost", "foreign_host")
        self.assertEqual(meta["mesh_role"], "foreign_host")
        one = observe_host(
            self.home, self.store, self.gov, "MeshHost", measure_coherence_field=False
        )
        self.assertEqual(one["role"], "foreign_host")
        law = topology_law_packet()
        self.assertIn("G_host", law["law"])
        self.assertEqual(classify_edge_kind(invented=True), G_LEARNED)


if __name__ == "__main__":
    unittest.main()
