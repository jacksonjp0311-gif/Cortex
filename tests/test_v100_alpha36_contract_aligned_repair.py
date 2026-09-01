"""Alpha.36 contract-aligned external-private evaluator tests."""

from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from cortex.contract_aligned_repair import (
    build_contract_aligned_repair_bundle,
    commission_contract_aligned_repair_forge,
    verify_contract_aligned_repair_bundle,
    verify_contract_aligned_repair_forge_result,
)


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


if __name__ == "__main__":
    unittest.main()
