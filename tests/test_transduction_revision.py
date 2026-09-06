import pytest

from cortex.edit_intent import (
    INTENT_SCHEMA, _compile_edit_intent, compile_edit_intent,
    verify_edit_intent_compilation,
)


@pytest.mark.parametrize('value', [1, True, None, {}, []])
def test_nonstring_edits_rejected_without_coercion(tmp_path, value):
    (tmp_path/'a.py').write_text('v = 1\n')
    with pytest.raises(ValueError, match='strings'):
        compile_edit_intent(tmp_path, {'schema_version': INTENT_SCHEMA, 'summary': 'test',
            'edits': [{'path': 'a.py', 'old': value, 'new': '2'}]}, allowed_targets=['a.py'])


@pytest.mark.parametrize('payload', ['[]', 'null', '1'])
def test_nonobject_json_rejected(tmp_path, payload):
    with pytest.raises(ValueError, match='JSON object'):
        compile_edit_intent(tmp_path, payload, allowed_targets=['a.py'])


def test_legacy_compilation_identity_is_reconstructed_not_upgraded(tmp_path):
    (tmp_path/'a.py').write_text('v = 1\n')
    payload = {'schema_version': INTENT_SCHEMA, 'summary': 'test',
               'edits': [{'path': 'a.py', 'old': '1', 'new': '2'}]}
    old = _compile_edit_intent(tmp_path, payload, allowed_targets=['a.py'], legacy=True)
    new = compile_edit_intent(tmp_path, payload, allowed_targets=['a.py'])
    assert old['schema_version'].endswith('/1.0') and new['schema_version'].endswith('/2.0')
    assert old['compilation_hash'] != new['compilation_hash']
    assert verify_edit_intent_compilation(tmp_path, old)['valid']
    assert verify_edit_intent_compilation(tmp_path, new)['valid']
