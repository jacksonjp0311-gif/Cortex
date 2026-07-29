#!/usr/bin/env bash
# Deliberate INTERNAL ARIA META-LANGUAGE vendor snapshot bump.
# Usage: ./scripts/bash/bump-aria-snapshot.sh /path/to/ARIA [source_commit] [source_release] [evolution_label]
set -euo pipefail

SOURCE="${1:?source ARIA root required}"
SOURCE_COMMIT="${2:-}"
SOURCE_RELEASE="${3:-}"
EVOLUTION_LABEL="${4:-}"
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VENDOR="$REPO_ROOT/cortex/aria_meta/vendor"
IDENTITY="$REPO_ROOT/cortex/aria_meta/INTERNAL_ARIA.json"

for required in MANIFEST.sha256 ARIA-RUNTIME.json ARIA-CONNECT.json LICENSE; do
  if [[ ! -f "$SOURCE/$required" ]]; then
    echo "Source ARIA tree missing required file: $required" >&2
    exit 1
  fi
done

echo "Bumping ARIA snapshot from $SOURCE -> $VENDOR"
rm -rf "$VENDOR"
mkdir -p "$VENDOR"
# Prefer rsync when available; fall back to tar for portability.
if command -v rsync >/dev/null 2>&1; then
  rsync -a --delete \
    --exclude '.git' --exclude '.aria' --exclude '__pycache__' \
    --exclude '.pytest_cache' --exclude 'node_modules' --exclude '.venv' --exclude 'venv' \
    "$SOURCE"/ "$VENDOR"/
else
  tar -C "$SOURCE" \
    --exclude '.git' --exclude '.aria' --exclude '__pycache__' \
    --exclude '.pytest_cache' --exclude 'node_modules' --exclude '.venv' --exclude 'venv' \
    -cf - . | tar -C "$VENDOR" -xf -
fi

# Regenerate MANIFEST.sha256
(
  cd "$VENDOR"
  : > MANIFEST.sha256
  find . -type f ! -path './.git/*' ! -path './.aria/*' ! -path '*/__pycache__/*' \
    ! -name 'MANIFEST.sha256' \
    | sed 's|^\./||' | sort | while read -r rel; do
      hash=$(sha256sum "$rel" | awk '{print $1}')
      printf '%s  %s\n' "$hash" "$rel" >> MANIFEST.sha256
    done
)

python - <<PY
import json
from pathlib import Path
identity_path = Path(r"$IDENTITY")
identity = json.loads(identity_path.read_text(encoding="utf-8"))
if "$SOURCE_COMMIT":
    identity["source_commit"] = "$SOURCE_COMMIT"
if "$SOURCE_RELEASE":
    identity["source_release"] = "$SOURCE_RELEASE"
if "$EVOLUTION_LABEL":
    identity["source_language_evolution"] = "$EVOLUTION_LABEL"
identity["vendoring"] = "git-subtree-squash"
identity["external_runtime_dependency"] = False
identity_path.write_text(json.dumps(identity, indent=2) + "\n", encoding="utf-8")
from cortex.aria_meta import verify_bundle
result = verify_bundle()
print(json.dumps(result, indent=2))
assert result["valid"], result
print(f"Bump complete: {result['checked_files']} files verified.")
PY

echo "Commit vendor separately from Cortex core when practical:"
echo "  git add cortex/aria_meta/vendor cortex/aria_meta/INTERNAL_ARIA.json"
echo '  git commit -m "chore: bump INTERNAL ARIA snapshot"'
