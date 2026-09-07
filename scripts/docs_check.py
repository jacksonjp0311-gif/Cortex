"""Dependency-free checks of canonical navigation; historical docs stay preserved.

--refresh-map mechanically updates normalized implementation fingerprints after
an intentional review. It does not change classifications or evidence claims.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
MAP = 'docs/CORTEX_KNOWLEDGE_MAP.json'


def fingerprints(root, data):
    return {p: hashlib.sha256((root/p).read_text(encoding='utf-8').encode()).hexdigest()
            for p in sorted({p for c in data['concepts'] for p in c['implementation']}) if (root/p).is_file()}


def _links(text):
    text = re.sub(r'```.*?```', '', text, flags=re.S)
    return re.findall(r'\]\(([^\s)]+)(?:\s+"[^"]*")?\)', text) + re.findall(r'(?:href|src)="([^"]+)"', text)


def validate(root, data):
    errors = []
    def exists(p):
        target = (root/p).resolve()
        if not target.is_relative_to(root.resolve()) or not target.exists():
            errors.append('missing_or_escaping_path:' + p)
    for p in data['entry_points'].values():
        exists(p)
    roles = {}
    paths = {d['path'] for d in data['documents']}
    for d in data['documents']:
        exists(d['path'])
        if d['canonicality'] == 'CANONICAL_CURRENT':
            if d['role'] in roles:
                errors.append('duplicate_canonical_role:' + d['role'])
            roles[d['role']] = d['path']
        for p in d.get('superseded_by', []):
            exists(p)
            if p not in paths:
                errors.append('unclassified_supersession:' + p)
    ids = [c['id'] for c in data['concepts']]
    if len(ids) != len(set(ids)):
        errors.append('duplicate_concept_id')
    for c in data['concepts']:
        for field in ('implementation', 'documentation', 'tests', 'benchmarks', 'evidence'):
            for p in c[field]:
                exists(p)
        for field in ('depends_on', 'supports', 'related_to', 'supersedes', 'superseded_by'):
            for identity in c[field]:
                if identity not in ids:
                    errors.append('unknown_concept_edge:' + identity)
        if c['authority_effect'] is not False:
            errors.append('map_cannot_authorize:' + c['id'])
    for p in ('llms.txt', '.github/copilot-instructions.md'):
        if 'docs/AGENT_START.md' not in (root/p).read_text(encoding='utf-8'):
            errors.append('machine_entry_drift:' + p)
    version = re.search(r'__version__ = "([^"]+)"', (root/'cortex/__init__.py').read_text()).group(1)
    if data['product_version'] != version:
        errors.append('version_drift')
    if data.get('implementation_hashes') != fingerprints(root, data):
        errors.append('implementation_changed_review_map_and_status')
    checked = set(data['entry_points'].values()) | {
        'docs/DOCUMENTATION_MIGRATION.md',
        'docs/research/TRANSDUCTION_REVISION_2026-09-06.md',
        'docs/research/EPISTEMIC_SUBSTRATE_2026-09-07.md',
        'docs/research/GSO_II_INVARIANT_CLOSURE_2026-09-07.md',
        'docs/research/GSO_IIB_METABOLIC_ASSEMBLY_2026-09-07.md',
        '.github/copilot-instructions.md',
    }
    for p in sorted(checked):
        if not (root/p).exists():
            continue
        for link in _links((root/p).read_text(encoding='utf-8')):
            url = urlsplit(link.strip('<>'))
            if url.scheme or url.netloc:
                continue
            target = (root/p).parent / unquote(url.path) if url.path else root/p
            if not target.exists():
                errors.append('broken_link:' + p + ' -> ' + link)
            elif url.fragment and target.suffix == '.md':
                headings = re.findall(r'^#+\s+(.+)$', target.read_text(encoding='utf-8'), re.M)
                slugs = {re.sub(r'[^\w\- ]', '', h.lower()).replace(' ', '-') for h in headings}
                if unquote(url.fragment) not in slugs:
                    errors.append('unresolved_anchor:' + p + ' -> ' + link)
    archive = data['readme_archive']
    text = (root/archive['path']).read_text(encoding='utf-8')
    payload = text.split(archive['marker'], 1)[1]
    blob = hashlib.sha1(b'blob ' + str(len(payload.encode())).encode() + b'\0' + payload.encode()).hexdigest()
    if blob != archive['git_blob']:
        errors.append('readme_archive_payload_changed')
    for link in _links(payload):
        url = urlsplit(link)
        if not url.scheme and url.path.startswith('assets/'):
            exists(unquote(url.path))
    readme = (root/'README.md').read_text(encoding='utf-8')
    if 'assets/cortex-neural-brain.png' not in readme or readme.count('<td') != 8:
        errors.append('readme_hero_or_grid_missing')
    status_text = (root/'docs/STATUS.md').read_text(encoding='utf-8')
    history_marker = '## Preserved historical gate chronology'
    if history_marker not in status_text:
        errors.append('status_missing_historical_boundary')
    else:
        current_status = status_text.split(history_marker, 1)[0]
        stale_current_assertions = (
            'No shadow organization kernel',
            'Captured streams are\ncurrently buffered in memory',
            'Structured-screen reconstruction still lacks full compiler-to-observed',
        )
        if any(assertion in current_status for assertion in stale_current_assertions):
            errors.append('status_current_surface_contains_superseded_claim')
    status_anchor = re.search(r'Runtime revision anchor: `([0-9a-f]{40})`', status_text)
    if status_anchor and status_anchor.group(1) != data.get('source_commit'):
        errors.append('status_knowledge_map_anchor_drift')
    registry_path = root/'docs/CORTEX_CLAIM_REGISTRY.json'
    if not registry_path.is_file():
        errors.append('missing_canonical_files:docs/CORTEX_CLAIM_REGISTRY.json')
    else:
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        from cortex.assurance import validate_claim_registry
        errors.extend(validate_claim_registry(json.loads(registry_path.read_text(encoding='utf-8')), root=root))
        if data['product_version'] != json.loads(registry_path.read_text(encoding='utf-8')).get('product_version'):
            errors.append('claim_registry_version_drift')
    if 'docs/CORTEX_CLAIM_REGISTRY.json' not in data.get('entry_points', {}) and 'docs/CORTEX_CLAIM_REGISTRY.json' not in {
        d['path'] for d in data.get('documents', [])
    }:
        errors.append('knowledge-map drift:claim_registry_unclassified')
    invariants_path = root/'docs/CORTEX_INVARIANTS.json'
    if not invariants_path.is_file():
        errors.append('missing_canonical_files:docs/CORTEX_INVARIANTS.json')
    else:
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        from cortex.invariants import validate_invariant_registry
        errors.extend(validate_invariant_registry(json.loads(invariants_path.read_text(encoding='utf-8')), root=root))
        if 'docs/CORTEX_INVARIANTS.json' not in {d['path'] for d in data.get('documents', [])}:
            errors.append('knowledge-map drift:invariant_registry_unclassified')
    return sorted(set(errors))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--refresh-map', action='store_true')
    args = parser.parse_args()
    path = ROOT/MAP
    data = json.loads(path.read_text(encoding='utf-8'))
    if args.refresh_map:
        data['implementation_hashes'] = fingerprints(ROOT, data)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    errors = validate(ROOT, data)
    anchor = subprocess.run(['git', 'cat-file', '-e', data['source_commit']+'^{commit}'], cwd=ROOT, capture_output=True)
    if anchor.returncode:
        errors.append('review_anchor_unresolvable')
    print(json.dumps({'valid': not errors, 'errors': errors, 'concepts': len(data['concepts']),
                      'classified_documents': len(data['documents']),
                      'scope': 'canonical local navigation; historical/external URLs not globally crawled'}, indent=2))
    return bool(errors)


if __name__ == '__main__':
    raise SystemExit(main())
