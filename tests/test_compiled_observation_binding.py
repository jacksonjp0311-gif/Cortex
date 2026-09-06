"""Exact-byte compiler delivery controls; no live inference or utility claim."""
from unittest.mock import patch

import pytest

from benchmarks.transduction_assurance import _repository, _intent, controls
from cortex.coding_workspace import verify_patch_in_isolated_worktree, _git
from cortex.edit_intent import compile_edit_intent
from cortex.executable_repair_forge import _verification_contract


@pytest.mark.parametrize("name,files,edits", controls())
def test_compiled_controls(tmp_path, name, files, edits):
    root = tmp_path / name
    _repository(root, files, "print('observed')\n")
    compiled = compile_edit_intent(root, _intent(edits), allowed_targets=list(files))
    result = verify_patch_in_isolated_worktree(root, compiled['proposal'],
        _verification_contract(compiled['proposal']), compilation=compiled)
    assert result['status'] == 'verified'
    assert result['transduction_state'] == 'PASS_WITHIN_DECLARED_SURFACE'
    assert result['transduction_contract']['expected_postimage_hashes'] == result['applied_postimage_hashes'] == result['postimage_hashes']
    assert result['steps'][0]['raw_observation_hash']
    assert result['transduction_contract']['authority_effect'] is False


def fixture(tmp_path, evaluator="print('observed')\n"):
    root = tmp_path / 'repo'
    _repository(root, {'a.py': 'v = 1\n'}, evaluator)
    compiled = compile_edit_intent(root, _intent([('a.py', '1', '2')]), allowed_targets=['a.py'])
    return root, compiled, _verification_contract(compiled['proposal'])


def test_application_corruption_blocks_evaluator(tmp_path):
    root, compiled, contract = fixture(tmp_path)
    def corrupt(workspace, args, patch_text=None):
        result = _git(workspace, args, patch_text)
        if args[:2] == ['apply', '--whitespace=error-all'] and result.returncode == 0:
            (workspace / 'a.py').write_bytes(b'v = 999\n')
        return result
    with patch('cortex.coding_workspace._git', side_effect=corrupt), patch(
        'cortex.coding_workspace.run_host_verification_step') as evaluator:
        with pytest.raises(ValueError, match='PRE_EVAL_ARTIFACT_MISMATCH'):
            verify_patch_in_isolated_worktree(root, compiled['proposal'], contract, compilation=compiled)
        evaluator.assert_not_called()


def test_evaluator_mutation_holds_path(tmp_path):
    root, compiled, contract = fixture(tmp_path, "from pathlib import Path\nPath('a.py').write_bytes(b'v = 3\\n')\n")
    result = verify_patch_in_isolated_worktree(root, compiled['proposal'], contract, compilation=compiled)
    assert result['status'] == 'held'
    assert result['transduction_state'] == 'HELD'


def test_forged_compilation_rejected(tmp_path):
    root, compiled, contract = fixture(tmp_path)
    compiled['postimage_hashes']['a.py'] = '0' * 64
    with pytest.raises(ValueError, match='COMPILER_BINDING_FAILURE'):
        verify_patch_in_isolated_worktree(root, compiled['proposal'], contract, compilation=compiled)
