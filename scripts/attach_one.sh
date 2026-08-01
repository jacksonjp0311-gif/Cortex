#!/usr/bin/env bash
# Zero-friction Hermetic attach (POSIX).
# Prefers: uvx → pipx → python -m pip install user → python -m cortex.attach
set -euo pipefail
HOST="${1:-.}"
export CORTEX_ATTACH_RITUAL="${CORTEX_ATTACH_RITUAL:-1}"
export CORTEX_HOME="${CORTEX_HOME:-$HOME/.cortex}"

run_attach() {
  if command -v uvx >/dev/null 2>&1; then
    exec uvx --from "git+https://github.com/jacksonjp0311-gif/Cortex@main" cortex-attach "$HOST" "${@:2}"
  fi
  if command -v pipx >/dev/null 2>&1; then
    pipx run --spec "git+https://github.com/jacksonjp0311-gif/Cortex@main" cortex-attach "$HOST" "${@:2}" && exit 0
  fi
  if command -v python3 >/dev/null 2>&1; then PY=python3
  elif command -v python >/dev/null 2>&1; then PY=python
  else
    echo "Python 3.10+ required. Install Python or uv (https://github.com/astral-sh/uv)." >&2
    exit 1
  fi
  "$PY" -m pip install -q --user "git+https://github.com/jacksonjp0311-gif/Cortex@main" 2>/dev/null || \
    "$PY" -m pip install -q "git+https://github.com/jacksonjp0311-gif/Cortex@main"
  exec "$PY" -m cortex.attach_main "$HOST" "${@:2}"
}

run_attach "$@"
