"""Alpha.36 contract-aligned external-private evaluator tests."""

from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from cortex.adapter_provenance import register_adapter_provenance
from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.contract_aligned_repair import (
    build_contract_aligned_repair_bundle,
    commission_contract_aligned_repair_forge,
    verify_contract_aligned_repair_bundle,
    verify_contract_aligned_repair_forge_result,
)
from cortex.store import Store
from cortex.structured_repair_screen import freeze_structured_repair_screen
from cortex.will import register_will_principal


def _case() -> dict:
    return {
        "case_id": "bounded_counter",
        "source": (
            "class Counter:\n"
            "    def __init__(self):\n"
            "        self.value = 0\n\n"
            "    def add(self, amount):\n"
            "        self.value += amount\n"
            "        return self.value\n"
        ),
        "requirements": [
            {
                "requirement_id": "R1",
                "text": "add(amount) must reject negative amounts with ValueError without changing value.",
            },
            {
                "requirement_id": "R2",
                "text": "Successful nonnegative additions return and retain the new total.",
            },
        ],
        "private_setup": "from module import Counter\nc = Counter()\n",
        "private_assertions": [
            {
                "assertion_id": "A1",
                "requirement_ids": ["R2"],
                "code": "assert c.add(3) == 3\nassert c.value == 3\n",
            },
            {
                "assertion_id": "A2",
                "requirement_ids": ["R1"],
                "code": (
                    "try:\n"
                    "    c.add(-1)\n"
                    "except ValueError:\n"
                    "    rejected = True\n"
                    "else:\n"
                    "    rejected = False\n"
                    "assert rejected and c.value == 3\n"
                ),
            },
        ],
        "patch": (
            "diff --git a/module.py b/module.py\n"
            "--- a/module.py\n"
            "+++ b/module.py\n"
            "@@ -3,5 +3,7 @@ class Counter:\n"
            "         self.value = 0\n"
            " \n"
            "     def add(self, amount):\n"
            "+        if amount < 0:\n"
            "+            raise ValueError(\"negative amount\")\n"
            "         self.value += amount\n"
            "         return self.value\n"
        ),
    }


def _sha(value: object) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


class ExternalAlignedAdapter:
    provider_family = "external-aligned-provider"
    model_id = "frontier-aligned-model"
    model_version = "2026-09"
    adapter_id = "tests.external-aligned-adapter"
    adapter_version = "1"


class Alpha36ContractAlignedRepairTests(unittest.TestCase):
    def test_valid_alignment_commissions_discriminative_zero_call_forge(self) -> None:
        public, private = build_contract_aligned_repair_bundle(
            secret_seed="alpha36-unit-secret", case_specs=[_case()]
        )
        audit = verify_contract_aligned_repair_bundle(public, private)
        self.assertTrue(audit["valid"], audit["errors"])
        self.assertNotIn("assert c.add", str(public))
        self.assertNotIn('raise ValueError("negative amount")', str(public))
        self.assertIn("R1", public["cases"][0]["executable_case"]["task"])
        with tempfile.TemporaryDirectory() as temp:
            result = commission_contract_aligned_repair_forge(
                public, private, Path(temp)
            )
        result_audit = verify_contract_aligned_repair_forge_result(result)
        self.assertTrue(result_audit["valid"], result_audit["errors"])
        self.assertEqual(result["state"], "CONTRACT_ALIGNED_REPAIR_FORGE_READY")
        self.assertEqual(result["additional_model_calls"], 0)
        self.assertTrue(result["structural_contract_alignment_established"])
        self.assertFalse(result["semantic_entailment_established"])
        for field in (
            "host_mutate_authorized",
            "execution_authorized",
            "memory_admission_authorized",
            "policy_effect",
        ):
            self.assertFalse(result[field])

    def test_unmapped_hidden_assertion_is_rejected(self) -> None:
        case = _case()
        case["private_assertions"].append(
            {
                "assertion_id": "A3",
                "requirement_ids": [],
                "code": "assert c.value != 99\n",
            }
        )
        with self.assertRaisesRegex(ValueError, "requires unique public requirement references"):
            build_contract_aligned_repair_bundle(secret_seed="secret", case_specs=[case])

    def test_unknown_requirement_reference_is_rejected(self) -> None:
        case = _case()
        case["private_assertions"][0]["requirement_ids"] = ["R3"]
        with self.assertRaisesRegex(ValueError, "unknown public requirement"):
            build_contract_aligned_repair_bundle(secret_seed="secret", case_specs=[case])

    def test_uncovered_public_requirement_is_rejected(self) -> None:
        case = _case()
        case["private_assertions"] = [case["private_assertions"][0]]
        with self.assertRaisesRegex(ValueError, "every public requirement"):
            build_contract_aligned_repair_bundle(secret_seed="secret", case_specs=[case])

    def test_private_setup_cannot_hide_an_assertion(self) -> None:
        case = _case()
        case["private_setup"] += "assert c.value == 0\n"
        with self.assertRaisesRegex(ValueError, "may not contain assertions"):
            build_contract_aligned_repair_bundle(secret_seed="secret", case_specs=[case])

    def test_private_or_public_tampering_breaks_alignment(self) -> None:
        public, private = build_contract_aligned_repair_bundle(
            secret_seed="alpha36-unit-secret", case_specs=[_case()]
        )
        changed_public = copy.deepcopy(public)
        changed_public["cases"][0]["requirements"][0]["text"] = "different semantics"
        self.assertFalse(
            verify_contract_aligned_repair_bundle(changed_public, private)["valid"]
        )
        changed_private = copy.deepcopy(private)
        changed_private["cases"][0]["alignment"]["private_assertions"][0][
            "requirement_ids"
        ] = ["R1"]
        self.assertFalse(
            verify_contract_aligned_repair_bundle(public, changed_private)["valid"]
        )

    def test_structured_screen_preregistration_binds_alignment_proof(self) -> None:
        specs = []
        for index in range(4):
            case = _case()
            case["case_id"] = f"aligned_{index}"
            specs.append(case)
        public, private = build_contract_aligned_repair_bundle(
            secret_seed="alpha37-unit-secret", case_specs=specs
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = commission_contract_aligned_repair_forge(
                public, private, root / "forge"
            )
            result["public_corpus"] = public
            result["result_hash"] = _sha(
                {key: value for key, value in result.items() if key != "result_hash"}
            )
            home = ensure_home(root / "home")
            host = root / "host"
            host.mkdir()
            (host / "README.md").write_text("alpha37\n", encoding="utf-8")
            store = Store(home / "cortex.db")
            try:
                repo = "Alpha37Host"
                bootstrap_repository(home, store, host, repo)
                adapter = ExternalAlignedAdapter()
                register_will_principal(
                    store,
                    repo,
                    "alpha37-operator",
                    "Alpha.37 test operator",
                    secret="alpha37-secret",
                )
                register_adapter_provenance(
                    store,
                    repo,
                    adapter,
                    boundary_kind="external_api",
                    principal_id="alpha37-operator",
                    principal_secret="alpha37-secret",
                    endpoint_descriptor={"transport": "test_external_boundary"},
                    model_family="frontier-aligned-family",
                    capability_class="structured_code_repair",
                )
                prereg = freeze_structured_repair_screen(
                    store,
                    repo,
                    forge_artifact=result,
                    private_bundle=private,
                    adapter=adapter,
                )
                binding = prereg["contract_alignment_binding"]
                self.assertEqual(binding["alignment_result_hash"], result["result_hash"])
                self.assertEqual(binding["aligned_corpus_hash"], public["corpus_hash"])
                self.assertTrue(binding["all_private_assertions_publicly_mapped"])
                self.assertFalse(binding["semantic_entailment_established"])
                changed = copy.deepcopy(result)
                changed["all_public_requirements_covered"] = False
                with self.assertRaisesRegex(ValueError, "contract-aligned"):
                    freeze_structured_repair_screen(
                        store,
                        repo,
                        forge_artifact=changed,
                        private_bundle=private,
                        adapter=adapter,
                    )
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
