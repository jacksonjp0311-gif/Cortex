"""Multi-file wiring fixtures are synthetic; these are not held-out model tasks."""
import json
import time
from unittest.mock import patch

import pytest

from cortex.adapter_provenance import register_adapter_provenance
from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.contract_aligned_repair import build_contract_aligned_repair_bundle, commission_contract_aligned_repair_forge, _sha
from cortex.epistemic_instrumentation import audit_instrument
from cortex.edit_intent import INTENT_SCHEMA
from cortex.executable_repair_forge import validate_source_files
from cortex.native_agent import CapabilityGrant, ToolRegistry
from cortex.store import Store
from cortex.structured_repair_screen import freeze_structured_repair_screen, execute_structured_repair_screen, verify_structured_repair_screen, _repeat_binding_errors
from cortex.will import register_will_principal
from test_v100_alpha36_contract_aligned_repair import _case, ExternalAlignedAdapter


@pytest.mark.parametrize("name", ["../escape.py", "/abs.py", "C:/bad.py", "a\\bad.py", "external_test.py", ".git/config", ".GIT/config", "CON.py", "a/../x.py"])
def test_unsafe_sources_fail_closed(name):
    with pytest.raises(ValueError):
        validate_source_files({name: "pass"})


def test_multifile_audit_to_native_screen_and_reconstruction(tmp_path):
    home = ensure_home(tmp_path / "home")
    host = tmp_path / "host"
    host.mkdir()
    (host / "README.md").write_text("unit fixture", encoding="utf-8")
    store = Store(home / "cortex.db")
    try:
        bootstrap_repository(home, store, host, "test")
        specs, controls, answers = [], {}, []
        for i in range(4):
            case = _case()
            path = f"pkg/counter_{i}.py"
            case["case_id"] = f"unit_{i}"
            case["files"] = {path: case.pop("source"), "pkg/__init__.py": "", "presentation.py": "def label(x): return str(x)\n"}
            case["private_setup"] = case["private_setup"].replace("from module", f"from pkg.counter_{i}")
            case["patch"] = case["patch"].replace("module.py", path)
            specs.append(case)
            controls[case["case_id"]] = [
                {"control_id": "positive", "patch": case["patch"], "expected_pass": True},
                {"control_id": "alternate", "patch": case["patch"].replace("amount < 0", "0 > amount"), "expected_pass": True},
                {"control_id": "negative", "patch": case["patch"].replace("amount < 0", "amount < -100"), "expected_pass": False},
            ]
            answers.append(json.dumps({"schema_version": INTENT_SCHEMA, "summary": "unit repair",
                "edits": [{"path": path, "old": "        self.value += amount", "new": "        if amount < 0:\n            raise ValueError('negative')\n        self.value += amount"}]}))
        public, private = build_contract_aligned_repair_bundle(secret_seed="unit-only", case_specs=specs)
        assert public["schema_version"].endswith("/2.0")
        instrument = audit_instrument(store, "test", public=public, private=private, controls=controls, root=tmp_path / "controls", source_commit="b" * 40)
        assert instrument["instrument"]["state"] == "READY"
        forge = commission_contract_aligned_repair_forge(public, private, tmp_path / "forge")
        forge["public_corpus"] = public
        forge["result_hash"] = _sha({k: v for k, v in forge.items() if k != "result_hash"})
        adapter = ExternalAlignedAdapter(answers)
        register_will_principal(store, "test", "unit", "Unit", secret="unit-only")
        register_adapter_provenance(store, "test", adapter, boundary_kind="external_api", principal_id="unit", principal_secret="unit-only", endpoint_descriptor={"transport": "unit_test"}, model_family="unit", capability_class="unit")
        prereg = freeze_structured_repair_screen(store, "test", forge_artifact=forge, private_bundle=private, adapter=adapter,
             screening_control_audit=instrument["audit"], instrument_receipt_hash=instrument["receipt_hash"], task_stratum="L2")
        assert prereg["schema_version"].endswith("/1.3")
        bad = {**prereg, "context_treatment": "semantic_lesson"}
        assert _repeat_binding_errors(store, "test", bad)
        now = time.time()
        result = execute_structured_repair_screen(store, "test", preregistration=prereg, private_bundle=private["executable_private_bundle"], adapter=adapter, tools=ToolRegistry(), grant=CapabilityGrant(workspace_root=str(host), allowed_tools=(), principal_id="unit", purpose="test", issued_at=now, expires_at=now+180, max_tool_calls=0, max_total_tool_seconds=0))
        assert result["screen"]["success_count"] == 4
        assert result["baseline_calibrated"] is False
        verified = verify_structured_repair_screen(store, "test", result_receipt_hash=result["receipt_hash"])
        assert verified["valid"], verified
        with patch("cortex.structured_repair_screen.NativeAgentRuntime") as runtime:
            with pytest.raises(ValueError):
                execute_structured_repair_screen(store, "test", preregistration=prereg, private_bundle=private["executable_private_bundle"], adapter=adapter, tools=ToolRegistry(), grant=CapabilityGrant(workspace_root=str(host), allowed_tools=(), principal_id="unit", purpose="test", issued_at=now, expires_at=now+180, max_tool_calls=0, max_total_tool_seconds=0))
            runtime.assert_not_called()
    finally:
        store.close()
