#!/usr/bin/env bash
# Strict isolation: fresh container, dummy host only, attach ritual, wipe.
# Zero contact with a "real" user project; engine code is only the image build context.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
IMAGE="cortex-attach-ritual-test:local"
NAME="cortex-attach-test-$$"

cleanup() {
  docker rm -f "$NAME" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[docker-attach] building image…"
docker build -t "$IMAGE" -f - "$ROOT" <<'DOCKERFILE'
FROM python:3.12-slim-bookworm
WORKDIR /engine
COPY . /engine
RUN pip install --no-cache-dir -e ".[dev]" \
 && useradd -m -u 10001 attachuser
USER attachuser
WORKDIR /home/attachuser
ENV CORTEX_HOME=/home/attachuser/.cortex
ENV CORTEX_ATTACH_RITUAL=0
ENV PYTHONUNBUFFERED=1
DOCKERFILE

echo "[docker-attach] running isolated ritual…"
docker run --name "$NAME" --rm \
  -e CORTEX_HOME=/home/attachuser/.cortex \
  -e CORTEX_ATTACH_RITUAL=0 \
  "$IMAGE" \
  bash -lc '
    set -euo pipefail
    mkdir -p /home/attachuser/dummy_host
    printf "# Dummy Host\n\nAlone no longer.\n" > /home/attachuser/dummy_host/README.md
    printf "def main():\n    return 42\n" > /home/attachuser/dummy_host/app.py
    cd /home/attachuser/dummy_host
    # Ensure no .cortex in host before
    test ! -e .cortex
    python -m cortex attach . --name DummyHost --json --no-ritual --quiet
    # Host still clean (external mode)
    test ! -e .cortex
    # Body exists only under CORTEX_HOME
    test -f "$CORTEX_HOME/cortex.db"
    python -m cortex --home "$CORTEX_HOME" claim --repo DummyHost --json || true
    python -m cortex --home "$CORTEX_HOME" epoch --repo DummyHost --json
    echo "ISOLATION_OK"
  '

echo "[docker-attach] wipe complete (container --rm)."
echo "PASS: docker attach ritual isolation"
