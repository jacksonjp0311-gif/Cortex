"""Archive reconstruction checks; synthetic fixtures, zero model calls."""
import copy
import json

from benchmarks.transduction_assurance import _intent
from cortex.edit_intent import compile_edit_intent
from cortex.executable_repair_forge import evaluate_executable_patch
from cortex.structured_repair_screen import _compiled_case_errors


def test_screen_bridge_and_tampering(tmp_path):
    expected = {'case_id': 'binding', 'files': {'a.py': 'v = 1\n'},
                'task': 'Return two', 'private_evaluator_commitment': 'test-commitment'}
    source = tmp_path / 'source'
    source.mkdir()
    (source / 'a.py').write_bytes(b'v = 1\n')
    output = json.dumps(_intent([('a.py', '1', '2')]))
    compiled = compile_edit_intent(source, output, allowed_targets=['a.py'])
    evaluation = evaluate_executable_patch(expected, {'external_test': 'from a import v\nassert v == 2\n'},
        compiled['proposal']['patch'], tmp_path / 'eval', compilation=compiled)
    case = {'compilation': compiled, 'compilation_hash': compiled['compilation_hash'],
            'proposal_hash': compiled['proposal_hash'], 'compiler_error': None,
            'task_success': evaluation['candidate_pass'], 'evaluation': evaluation}
    assert case['task_success']
    assert _compiled_case_errors(expected, case, {'final_answer': output}) == []
    for field in ('applied_postimage_hashes', 'postimage_hashes'):
        altered = copy.deepcopy(case)
        altered['evaluation']['candidate'][field]['a.py'] = '0' * 64
        assert _compiled_case_errors(expected, altered, {'final_answer': output})
    altered = copy.deepcopy(case)
    altered['evaluation']['candidate']['steps'][0]['raw_observation']['stdout_sha256'] = '0' * 64
    assert 'raw_observation_binding_invalid' in _compiled_case_errors(expected, altered, {'final_answer': output})
    assert 'compiler_reconstruction_invalid' in _compiled_case_errors(expected, case,
        {'final_answer': output.replace('"2"', '"3"')})
