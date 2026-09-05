"""Alternate allowed implementations must survive instrument validation."""
import copy
import difflib
import tempfile
from pathlib import Path

import pytest

from cortex.contract_aligned_repair import (
    audit_contract_aligned_controls,
    build_contract_aligned_repair_bundle,
)


def fixture(overconstrained=False):
    source = "def successor(n):\n    return n\n"
    correct = "def successor(n):\n    return n + 1\n"
    alternate = "def successor(n):\n    return 1.0 + n\n"
    def patch(new):
        return "diff --git a/module.py b/module.py\n" + "".join(difflib.unified_diff(
            source.splitlines(keepends=True), new.splitlines(keepends=True),
            fromfile="a/module.py", tofile="b/module.py",
        ))
    controls = {"successor": [
        {"control_id": "integer", "patch": patch(correct), "expected_pass": True},
        {"control_id": "numeric_equivalent", "patch": patch(alternate), "expected_pass": True},
        {"control_id": "wrong_offset", "patch": patch(correct.replace("+ 1", "+ 2")), "expected_pass": False},
    ]}
    assertion = "from module import successor\nassert successor(5) == 6\n"
    if overconstrained:
        assertion += "assert type(successor(5)) is int\n"
    public, private = build_contract_aligned_repair_bundle(secret_seed="unit-only-control-panel", case_specs=[{
        "case_id": "successor", "source": source,
        "requirements": [{"requirement_id": "R1", "text": "For numeric n, return a number equal to n+1. Integer and float results are equally acceptable."}],
        "private_setup": "",
        "private_assertions": [{"assertion_id": "A1", "requirement_ids": ["R1"], "code": assertion}],
        "patch": patch(correct),
    }])
    return public, private, controls


@pytest.mark.parametrize("overconstrained", [False, True])
def test_control_panel_detects_representation_bias_without_model_calls(overconstrained):
    public, private, controls = fixture(overconstrained)
    with tempfile.TemporaryDirectory() as root:
        result = audit_contract_aligned_controls(public, private, controls, Path(root))
    assert result["state"] == ("EVALUATOR_CHALLENGED" if overconstrained else "CONTROL_PANEL_PASS")
    assert result["additional_model_calls"] == 0
    assert result["observations"][0]["observed_pass"] is True
    assert result["observations"][1]["observed_pass"] is not overconstrained
    assert result["observations"][2]["observed_pass"] is False
    assert result["universal_implementation_equivalence"] is False
    assert result["execution_authorized"] is False


@pytest.mark.parametrize("change", ["duplicate", "no_negative", "caller_truth"])
def test_control_panel_rejects_invalid_panel_before_execution(change):
    public, private, controls = fixture()
    controls = copy.deepcopy(controls)
    if change == "duplicate":
        controls["successor"][1]["patch"] = controls["successor"][0]["patch"]
    elif change == "no_negative":
        controls["successor"] = controls["successor"][:2]
    else:
        controls["successor"][0]["expected_pass"] = 1
    with pytest.raises(ValueError):
        audit_contract_aligned_controls(public, private, controls, Path("unused-controls"))
