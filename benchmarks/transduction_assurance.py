"""Finite, zero-model-call delivery audit. Failed expectations are evidence, not fixes.

Host-authored fixtures run only in disposable repositories. This is not a sandbox
for untrusted code and does not authorize adaptation or certify the whole path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cortex.coding_workspace import _git, create_patch_proposal, verify_patch_in_isolated_worktree  # noqa: E402
from cortex.edit_intent import INTENT_SCHEMA, compile_edit_intent  # noqa: E402
from cortex.epistemic_instrumentation import AUTHORITY  # noqa: E402
from cortex.executable_repair_forge import _verification_contract  # noqa: E402


def controls():
    lines = ''.join(f'v{i} = {i}\n' for i in range(20))
    return [
        ('first_line_import', {'a.py': 'v = 1\n'}, [('a.py', 'v = 1\n', 'import copy\nv = 1\n')]),
        ('interior', {'a.py': 'x = 1\ny = 2\nz = 3\n'}, [('a.py', 'y = 2', 'y = 4')]),
        ('final_line', {'a.py': 'x = 1\ny = 2\n'}, [('a.py', 'y = 2\n', 'y = 3\n')]),
        ('multi_hunk', {'a.py': lines}, [('a.py', 'v0 = 0', 'v0 = 100'), ('a.py', 'v19 = 19', 'v19 = 200')]),
        ('multi_file_nested', {'pkg/a.py': 'v = 1\n', 'b.py': 'v = 2\n'}, [('pkg/a.py', '1', '3'), ('b.py', '2', '4')]),
        ('utf8', {'a.py': "label = 'café'\n"}, [('a.py', 'café', 'naïve')]),
        ('blank_added', {'a.py': 'v = 1\n'}, [('a.py', 'v = 1\n', '\n\nv = 1\n')]),
        ('repeated_target_sequential', {'a.py': 'v = 1\n'}, [('a.py', '1', '2'), ('a.py', '2', '3')]),
        ('no_terminal_newline', {'a.py': 'v = 1'}, [('a.py', '1', '2')]),
    ]


def _repository(root, files, evaluator):
    root.mkdir()
    for name, content in {**files, 'external_test.py': evaluator}.items():
        path = root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode('utf-8'))
    for args in (['init', '-q'], ['config', 'core.autocrlf', 'false'],
                 ['config', 'user.name', 'Cortex audit'], ['config', 'user.email', 'audit@example.invalid'],
                 ['add', '.'], ['commit', '-qm', 'frozen control']):
        if _git(root, args).returncode:
            raise RuntimeError('audit repository setup failed')


def _intent(edits):
    return {'schema_version': INTENT_SCHEMA, 'summary': 'bounded audit control',
            'edits': [dict(zip(('path', 'old', 'new'), edit)) for edit in edits]}


def run_audit(parent: Path):
    rows = []
    for name, files, edits in controls():
        expected = dict(files)
        for path, old, new in edits:
            expected[path] = expected[path].replace(old, new, 1)
        evaluator = 'from pathlib import Path\n' + ''.join(
            f'assert Path({path!r}).read_bytes() == {content.encode("utf-8")!r}\n'
            for path, content in expected.items())
        root = parent/name
        _repository(root, files, evaluator)
        compiled = None
        try:
            compiled = compile_edit_intent(root, _intent(edits), allowed_targets=list(files))
            observed = verify_patch_in_isolated_worktree(root, compiled['proposal'], _verification_contract(compiled['proposal']))
            accepted = observed['status'] == 'verified'
            error = None
        except (ValueError, RuntimeError) as exc:
            accepted = False
            error = type(exc).__name__ + ':' + str(exc)
        rows.append({'control': name, 'expected': 'DELIVER_EXACTLY', 'expectation_met': accepted,
                     'compiled': compiled is not None, 'error': error})

    for name in ('trailing_whitespace', 'stale_preimage', 'unauthorized_target', 'malformed_patch', 'numeric_edit', 'distorted_patch'):
        root = parent/name
        _repository(root, {'a.py': 'v = 1\n'}, "from a import v\nassert v == 2\n")
        edits = [('a.py', '1', '2')]
        if name == 'trailing_whitespace':
            edits = [('a.py', 'v = 1\n', 'v = 2  \n')]
        if name == 'stale_preimage':
            edits = [('a.py', 'missing', '2')]
        if name == 'unauthorized_target':
            edits = [('external_test.py', '2', '1')]
        if name == 'numeric_edit':
            edits = [('a.py', 1, 2)]
        try:
            compiled = compile_edit_intent(root, _intent(edits), allowed_targets=['a.py'])
            patch = compiled['proposal']['patch']
            if name == 'malformed_patch':
                patch = 'not a patch'
            if name == 'distorted_patch':
                patch = patch.replace('+v = 2', '+v = 3')
            proposal = create_patch_proposal(root, patch, 'audit negative')
            observed = verify_patch_in_isolated_worktree(root, proposal, _verification_contract(proposal))
            rejected = observed['status'] != 'verified'
            reason = 'EVALUATOR_REJECTION' if rejected else 'ACCEPTED'
        except (ValueError, RuntimeError) as exc:
            rejected = True
            reason = type(exc).__name__ + ':' + str(exc)
        rows.append({'control': name, 'expected': 'REJECT', 'expectation_met': rejected, 'reason': reason})

    root = parent/'evaluator_changes_candidate'
    _repository(root, {'a.py': 'v = 1\n'}, "from pathlib import Path\nPath('a.py').write_bytes(b'v = 99\\n')\n")
    compiled = compile_edit_intent(root, _intent([('a.py', '1', '2')]), allowed_targets=['a.py'])
    observed = verify_patch_in_isolated_worktree(root, compiled['proposal'], _verification_contract(compiled['proposal']))
    mismatch = observed['postimage_hashes'] != compiled['postimage_hashes']
    rows.append({'control': 'evaluator_changes_candidate', 'expected': 'HOLD_DISTORTED_OBSERVATION',
                 'expectation_met': observed['status'] != 'verified', 'verifier_status': observed['status'],
                 'expected_vs_recorded_postimage_mismatch': mismatch})
    return {'schema_version': 'cortex-transduction-control-audit/1.0',
            'state': 'READY_WITHIN_CONTROLS' if all(r['expectation_met'] for r in rows) else 'HELD',
            'observations': rows, 'expectations_met': sum(r['expectation_met'] for r in rows),
            'control_count': len(rows), 'model_calls': 0, 'evidence_class': 'local_structural_audit',
            'anchors': ['host-authored expected bytes and controls', 'local Git and Python execution'],
            'unresolved': ['finite controls only', 'host execution not independently attested',
                           'raw subprocess observation transport not lossless', 'no recursive organization experiment'],
            'adaptation_authorized': False, **AUTHORITY}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--inspect-result', action='append', default=[])
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('audit output already exists; preserve history')
    if args.inspect_result:
        from cortex.config import cortex_home
        from cortex.store import Store
        from cortex.epistemic_instrumentation import inspect_repair_observation_path
        store = Store(cortex_home()/'cortex.db')
        try:
            report = {'schema_version': 'cortex-historical-path-inspection/1.0', 'model_calls': 0,
                      'views': [inspect_repair_observation_path(store, 'Cortex', h) for h in args.inspect_result],
                      'state': 'HELD', 'adaptation_authorized': False, **AUTHORITY}
        finally:
            store.close()
    else:
        with tempfile.TemporaryDirectory(prefix='cortex-transduction-') as directory:
            report = run_audit(Path(directory))
    report.update(source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  python_version=platform.python_version(), operating_system=platform.system(),
                  implementation_hashes={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
                     ('cortex/edit_intent.py', 'cortex/coding_workspace.py', 'cortex/epistemic_instrumentation.py', 'benchmarks/transduction_assurance.py')})
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'state': report['state'], 'controls': report.get('control_count'),
                      'expectations_met': report.get('expectations_met'), 'model_calls': 0}))


if __name__ == '__main__':
    main()
