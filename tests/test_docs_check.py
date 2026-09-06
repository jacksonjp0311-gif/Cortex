"""Canonical navigation checks are bounded structural tests, not human studies."""
import copy
import json
from pathlib import Path

from scripts.docs_check import validate

ROOT = Path(__file__).resolve().parents[1]


def data():
    return json.loads((ROOT/'docs/CORTEX_KNOWLEDGE_MAP.json').read_text(encoding='utf-8'))


def test_canonical_navigation_and_preserved_readme():
    assert validate(ROOT, data()) == []


def test_duplicate_canonical_roles_rejected():
    changed = data()
    changed['documents'].append(copy.deepcopy(next(d for d in changed['documents'] if d['role'] == 'HUMAN_ENTRY')))
    assert 'duplicate_canonical_role:HUMAN_ENTRY' in validate(ROOT, changed)


def test_dangling_paths_and_relationships_rejected():
    changed = data()
    changed['concepts'][0]['implementation'].append('cortex/nonexistent.py')
    changed['concepts'][0]['depends_on'].append('invented')
    errors = validate(ROOT, changed)
    assert 'missing_or_escaping_path:cortex/nonexistent.py' in errors
    assert 'unknown_concept_edge:invented' in errors


def test_stale_version_fingerprint_and_archive_rejected():
    changed = data()
    changed['product_version'] = 'old'
    changed['implementation_hashes'] = {}
    changed['readme_archive']['git_blob'] = '0' * 40
    errors = validate(ROOT, changed)
    assert 'version_drift' in errors
    assert 'implementation_changed_review_map_and_status' in errors
    assert 'readme_archive_payload_changed' in errors
