"""CI smoke: multi-agent mode token gates (this repo only)."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cortex.agents.tokens import (  # noqa: E402
    FORBIDDEN_SCOPES,
    mint_token,
    multi_agent_enabled,
    register_agent,
    set_multi_agent_mode,
)
from cortex.bootstrap import bootstrap_repository  # noqa: E402
from cortex.config import ensure_home  # noqa: E402
from cortex.hippocampus import remember  # noqa: E402
from cortex.store import Store  # noqa: E402


def main() -> int:
    failures: list[str] = []
    if "host.mutate" not in FORBIDDEN_SCOPES:
        failures.append("host_mutate_not_forbidden")
    home = ensure_home(Path(tempfile.mkdtemp(prefix="ci-ma-")) / "home")
    store = Store(home / "cortex.db")
    try:
        boot = bootstrap_repository(home, store, ROOT, "CortexMACI", force=True, external=True)
        if (boot.get("certificate") or {}).get("status") not in {"verified", "degraded"}:
            failures.append("bootstrap")
        if multi_agent_enabled(store, "CortexMACI"):
            failures.append("default_should_be_off")
        set_multi_agent_mode(store, "CortexMACI", True)
        blocked = remember(home, store, "CortexMACI", "discovery", "no-token")
        if not blocked.get("blocked"):
            failures.append("expected_block_without_token")
        register_agent(store, "CortexMACI", "ci", "CI Agent")
        bad = mint_token(store, "CortexMACI", "ci", ["host.mutate"])
        if bad.get("minted"):
            failures.append("host_mutate_minted")
        tok = mint_token(store, "CortexMACI", "ci", ["memory.remember"])
        ok = remember(
            home,
            store,
            "CortexMACI",
            "discovery",
            "with-token",
            token_id=tok.get("token_id"),
        )
        if not (ok.get("recorded") or ok.get("duplicate")):
            failures.append("token_remember_failed")
        set_multi_agent_mode(store, "CortexMACI", False)
        free = remember(home, store, "CortexMACI", "discovery", "single-agent-ok")
        if free.get("blocked"):
            failures.append("single_agent_blocked")
        payload = {
            "passed": not failures,
            "failures": failures,
            "claim_boundary": "Self-host multi-agent gate regression only.",
        }
        print(json.dumps(payload, indent=2, default=str))
        return 0 if not failures else 1
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
