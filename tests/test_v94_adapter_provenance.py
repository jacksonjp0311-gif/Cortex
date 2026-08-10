"""Adversarial v9.4 host-controlled adapter provenance boundary tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cortex.adapter_provenance import (
    AdapterProvenanceError,
    EVIDENCE_LIVE,
    EVIDENCE_SIMULATED,
    EVIDENCE_SYNTHETIC,
    EVIDENCE_UNKNOWN,
    register_adapter_provenance,
    resolve_adapter_provenance,
    verify_adapter_provenance,
    verify_adapter_registration,
)
from cortex.model_circulation import FixtureAdapter
from cortex.store import Store
from cortex.will import register_will_principal


class HostAdapter:
    provider_family = "host-provider"
    adapter_id = "tests.host-adapter"
    adapter_version = "1"

    def __init__(
        self,
        *,
        model_id: str = "model-a",
        model_version: str = "2026-08",
        temperature: float = 0.2,
        api_key: str = "profile-secret",
        endpoint: str = "https://api.example.test/v1/chat",
    ) -> None:
        self.model_id = model_id
        self.model_version = model_version
        self.temperature = temperature
        self.api_key = api_key
        self.endpoint = endpoint
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "X-Api-Key": api_key,
            "Accept": "application/json",
        }

    def invoke(self, request: object) -> dict[str, object]:
        return {"request": request, "model": self.model_id}


class HostAdapterSubclass(HostAdapter):
    pass


class SimulationAdapter(HostAdapter):
    adapter_id = "tests.simulation-adapter"


class SpoofedFixtureAdapter(FixtureAdapter):
    provider_family = "claimed-provider"
    adapter_id = "claimed.external"
    adapter_version = "999"
    _cortex_evidence_marker = object()


class V94AdapterProvenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.host = root / "host"
        self.host.mkdir()
        self.store = Store(root / "cortex.db")
        self.repo = "AdapterHost"
        self.store.attach(self.repo, "repo-v94-adapter-host", self.host)
        register_will_principal(
            self.store,
            self.repo,
            "operator",
            "Operator",
            secret="principal-secret-v1",
        )

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def _register(
        self,
        adapter: object,
        *,
        boundary: str = "external_api",
        secret: str = "principal-secret-v1",
        endpoint: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return register_adapter_provenance(
            self.store,
            self.repo,
            adapter,
            boundary_kind=boundary,
            principal_id="operator",
            principal_secret=secret,
            endpoint_descriptor=endpoint or {"region": "test-east"},
        )

    def test_fixture_lineage_can_never_register_or_upgrade(self) -> None:
        fixture = SpoofedFixtureAdapter(model_id="claimed-live-model")
        with self.assertRaisesRegex(AdapterProvenanceError, "fixture lineage"):
            self._register(fixture)

        provenance = resolve_adapter_provenance(self.store, self.repo, fixture)
        self.assertEqual(provenance["evidence_class"], EVIDENCE_SYNTHETIC)
        self.assertEqual(provenance["trust_basis"], "sealed_fixture_lineage")
        self.assertFalse(provenance["empirical"])
        self.assertIsNone(provenance["registration_id"])

    def test_unregistered_nonfixture_is_unknown(self) -> None:
        provenance = resolve_adapter_provenance(self.store, self.repo, HostAdapter())
        self.assertEqual(provenance["evidence_class"], EVIDENCE_UNKNOWN)
        self.assertEqual(provenance["evidence_state"], "unregistered")
        self.assertFalse(provenance["empirical"])
        self.assertIsNone(provenance["registration_id"])

    def test_registration_binds_exact_type_identity_and_nonsecret_config(self) -> None:
        adapter = HostAdapter(api_key="secret-one")
        registration = self._register(adapter)
        resolved = resolve_adapter_provenance(self.store, self.repo, adapter)
        self.assertEqual(resolved["evidence_class"], EVIDENCE_LIVE)
        self.assertEqual(resolved["registration_id"], registration["registration_id"])

        # Credential rotation is excluded from the non-secret profile.
        credential_rotated = HostAdapter(api_key="secret-two")
        self.assertEqual(
            resolve_adapter_provenance(self.store, self.repo, credential_rotated)[
                "registration_id"
            ],
            registration["registration_id"],
        )

        different_config = HostAdapter(temperature=0.7, api_key="secret-two")
        different_model = HostAdapter(model_id="model-b", api_key="secret-two")
        subclass = HostAdapterSubclass(api_key="secret-two")
        for candidate in (different_config, different_model, subclass):
            result = resolve_adapter_provenance(self.store, self.repo, candidate)
            self.assertEqual(result["evidence_class"], EVIDENCE_UNKNOWN)
            self.assertIsNone(result["registration_id"])

        adapter.temperature = 0.9
        self.assertEqual(
            resolve_adapter_provenance(self.store, self.repo, adapter)["evidence_class"],
            EVIDENCE_UNKNOWN,
        )

    def test_endpoint_and_runtime_profile_are_sanitized_before_persistence(self) -> None:
        adapter = HostAdapter(
            api_key="profile-key-secret",
            endpoint=(
                "https://runtime-user:runtime-password@api.example.test/"
                "credential-marker-for-redaction?api_key=query-secret"
            ),
        )
        registration = self._register(
            adapter,
            endpoint={
                "url": (
                    "https://endpoint-user:endpoint-password@edge.example.test/v1/chat"
                    "?token=endpoint-query-secret"
                ),
                "client_secret": "endpoint-client-secret",
                "headers": {
                    "Authorization": "Bearer endpoint-bearer-secret",
                    "X-Api-Key": "endpoint-api-secret",
                },
                "region": "safe-region",
            },
        )
        row = self.store.db.execute(
            "SELECT * FROM model_adapter_registrations WHERE registration_id=?",
            (registration["registration_id"],),
        ).fetchone()
        self.assertIsNotNone(row)
        persisted = json.dumps({key: row[key] for key in row.keys()}, sort_keys=True)
        returned = json.dumps(registration, sort_keys=True)
        for secret in (
            "profile-key-secret",
            "runtime-password",
            "query-secret",
            "endpoint-password",
            "endpoint-query-secret",
            "endpoint-client-secret",
            "endpoint-bearer-secret",
            "endpoint-api-secret",
        ):
            self.assertNotIn(secret, persisted)
            self.assertNotIn(secret, returned)
        self.assertIn("<redacted>", persisted)
        self.assertNotIn("@api.example.test", persisted)
        self.assertNotIn("@edge.example.test", persisted)
        self.assertEqual(registration["host_identity"]["provider_family"], "host-provider")
        self.assertEqual(registration["host_identity"]["model_id"], "model-a")

    def test_one_exact_implementation_profile_cannot_change_boundary_class(self) -> None:
        adapter = HostAdapter()
        first = self._register(adapter, boundary="external_api")
        duplicate = self._register(adapter, boundary="external_api")
        self.assertTrue(first["inserted"])
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(duplicate["registration_id"], first["registration_id"])

        with self.assertRaisesRegex(AdapterProvenanceError, "conflicting boundary"):
            self._register(adapter, boundary="simulation")

    def test_principal_secret_rotation_does_not_rewrite_registration_history(self) -> None:
        adapter = HostAdapter()
        registration = self._register(adapter)
        before = verify_adapter_registration(
            self.store,
            self.repo,
            str(registration["registration_id"]),
        )
        self.assertTrue(before["valid"], before["errors"])

        register_will_principal(
            self.store,
            self.repo,
            "operator",
            "Operator rotated",
            secret="principal-secret-v2",
        )
        after = verify_adapter_registration(
            self.store,
            self.repo,
            str(registration["registration_id"]),
        )
        self.assertTrue(after["valid"], after["errors"])
        self.assertEqual(
            resolve_adapter_provenance(self.store, self.repo, adapter)["registration_id"],
            registration["registration_id"],
        )
        duplicate = self._register(adapter, secret="principal-secret-v2")
        self.assertTrue(duplicate["duplicate"])
        with self.assertRaisesRegex(AdapterProvenanceError, "secret mismatch"):
            self._register(adapter, secret="principal-secret-v1")

    def test_registration_never_claims_provider_attestation(self) -> None:
        adapter = HostAdapter()
        self._register(adapter)
        provenance = resolve_adapter_provenance(self.store, self.repo, adapter)
        self.assertEqual(provenance["provider_attestation"], "not_available")
        self.assertFalse(provenance["provider_attestation_claimed"])
        self.assertIn("not provider attestation", provenance["claim_boundary"])
        check = verify_adapter_provenance(self.store, self.repo, provenance)
        self.assertTrue(check["valid"], check["errors"])

        forged = dict(provenance)
        forged["provider_attestation"] = "provider_verified"
        forged["provider_attestation_claimed"] = True
        forged_check = verify_adapter_provenance(self.store, self.repo, forged)
        self.assertFalse(forged_check["valid"])
        self.assertIn("provider_attestation_claim_invalid", forged_check["errors"])

    def test_provenance_is_bound_to_registration_material(self) -> None:
        adapter = HostAdapter()
        self._register(adapter)
        provenance = resolve_adapter_provenance(self.store, self.repo, adapter)
        for field in (
            "implementation_digest",
            "runtime_profile_digest",
            "host_identity_digest",
            "binding_digest",
            "registration_hash",
        ):
            forged = dict(provenance)
            forged[field] = "0" * 64
            check = verify_adapter_provenance(self.store, self.repo, forged)
            self.assertFalse(check["valid"], field)

        forged_identity = dict(provenance)
        forged_identity["host_identity"] = {
            **dict(provenance["host_identity"]),
            "model_id": "forged-model",
        }
        self.assertFalse(
            verify_adapter_provenance(self.store, self.repo, forged_identity)["valid"]
        )

        forged_empirical = dict(provenance)
        forged_empirical["empirical"] = False
        empirical_check = verify_adapter_provenance(
            self.store,
            self.repo,
            forged_empirical,
        )
        self.assertFalse(empirical_check["valid"])
        self.assertIn("adapter_empirical_flag_invalid", empirical_check["errors"])

    def test_simulation_registration_is_nonempirical(self) -> None:
        adapter = SimulationAdapter()
        self._register(adapter, boundary="simulation")
        provenance = resolve_adapter_provenance(self.store, self.repo, adapter)
        self.assertEqual(provenance["evidence_class"], EVIDENCE_SIMULATED)
        self.assertFalse(provenance["empirical"])
        check = verify_adapter_provenance(self.store, self.repo, provenance)
        self.assertTrue(check["valid"], check["errors"])


if __name__ == "__main__":
    unittest.main()
