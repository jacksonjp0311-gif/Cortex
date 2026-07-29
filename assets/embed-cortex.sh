#!/usr/bin/env bash
# Cortex Desktop embed — clone jacksonjp0311-gif/Cortex to your Desktop.
# First-party installer. Run after downloading from the Cortex embed HUD.
set -euo pipefail

REPO_URL="https://github.com/jacksonjp0311-gif/Cortex.git"
# Prefer ~/Desktop; fall back to $HOME if Desktop missing (some Linux setups).
if [[ -d "${HOME}/Desktop" ]]; then
  DEST="${HOME}/Desktop/Cortex"
elif [[ -d "${HOME}/desktop" ]]; then
  DEST="${HOME}/desktop/Cortex"
else
  DEST="${HOME}/Cortex"
fi

echo ""
echo "  CORTEX // DESKTOP EMBED"
echo "  target: ${DEST}"
echo ""

if ! command -v git >/dev/null 2>&1; then
  echo "  ERROR: git not found on PATH."
  exit 1
fi

if [[ -d "${DEST}/.git" ]]; then
  echo "  existing clone detected — git pull"
  git -C "${DEST}" pull --ff-only
elif [[ -e "${DEST}" ]]; then
  echo "  ERROR: ${DEST} exists but is not a git repo. Move/rename it, then re-run."
  exit 1
else
  echo "  cloning…"
  git clone "${REPO_URL}" "${DEST}"
fi

echo ""
echo "  ◈ CORTEX EMBEDDED ON DESKTOP"
echo "  path: ${DEST}"
echo ""
echo "  next:"
echo "    cd \"${DEST}\""
echo "    pip install -e ."
echo "    python -m cortex bootstrap . --name Cortex --json"
echo ""
