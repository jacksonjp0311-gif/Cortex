#!/usr/bin/env bash
# Zero-friction Hermetic attach (POSIX).
# Prefers: uvx → pipx → python -m pip → cortex.attach_main
#
# Run ONCE from your project folder. Do NOT also run uvx/python attach.
#   curl -fsSL .../attach_one.sh | bash -s -- .
set -euo pipefail

HOST="${1:-.}"
export PYTHONUNBUFFERED="${PYTHONUNBUFFERED:-1}"
export CORTEX_HOME="${CORTEX_HOME:-$HOME/.cortex}"

# Reject README placeholders (same trap as Windows path\to\your\project)
case "$HOST" in
  *path/to/your*|*path\to\your*|/path/to/*|C:\\path\\to\\*)
    echo "That path is a README placeholder. cd to your real project first, then pass . (dot)." >&2
    exit 2
    ;;
esac

if [[ ! -d "$HOST" ]]; then
  echo "Host path not found: $HOST  (cd to your project, then run with . )" >&2
  exit 2
fi
# Resolve to absolute when possible (GNU/BSD realpath or python)
if command -v realpath >/dev/null 2>&1; then
  HOST="$(realpath "$HOST")"
elif command -v python3 >/dev/null 2>&1; then
  HOST="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$HOST")"
elif command -v python >/dev/null 2>&1; then
  HOST="$(python -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$HOST")"
fi

# Non-TTY (curl|bash, CI): keep ritual short so it cannot look like a hang
if [[ ! -t 1 ]] && [[ -z "${CORTEX_ATTACH_FAST:-}" ]]; then
  export CORTEX_ATTACH_FAST=1
fi

SPEC='git+https://github.com/jacksonjp0311-gif/Cortex@main'
shift || true
EXTRA=("$@")

if command -v uvx >/dev/null 2>&1; then
  echo "Cortex attach via uvx → $HOST" >&2
  exec uvx --from "$SPEC" cortex-attach "$HOST" "${EXTRA[@]+"${EXTRA[@]}"}"
fi
if command -v pipx >/dev/null 2>&1; then
  echo "Cortex attach via pipx → $HOST" >&2
  exec pipx run --spec "$SPEC" cortex-attach "$HOST" "${EXTRA[@]+"${EXTRA[@]}"}"
fi
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "Python 3.10+ required. Install Python or uv (https://github.com/astral-sh/uv)." >&2
  exit 1
fi
echo "Cortex attach via $PY → $HOST" >&2
"$PY" -m pip install -q --user "$SPEC" 2>/dev/null || \
  "$PY" -m pip install -q "$SPEC"
exec "$PY" -m cortex.attach_main "$HOST" "${EXTRA[@]+"${EXTRA[@]}"}"
