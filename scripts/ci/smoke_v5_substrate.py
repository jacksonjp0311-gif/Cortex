"""CI smoke: v5 multi-res, HNSW, ranker, contracts, agents, causal (this repo only)."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cortex.agents.tokens import ALLOWED_SCOPES, FORBIDDEN_SCOPES, mint_token, register_agent  # noqa: E402
from cortex.bootstrap import bootstrap_repository  # noqa: E402
from cortex.config import ensure_home  # noqa: E402
from cortex.contract.check import DEFAULT_CONTRACT, check_contract  # noqa: E402
from cortex.neuron import compile_interlink  # noqa: E402
from cortex.ranker.model import ensure_ranker, train_from_outcome  # noqa: E402
from cortex.store import Store  # noqa: E402
from cortex.vectors import build_hnsw_index, hnsw_status  # noqa: E402


def main() -> int:
    failures: list[str] = []
    if "host.mutate" in ALLOWED_SCOPES:
        failures.append("host_mutate_allowed")
    if "host.mutate" not in FORBIDDEN_SCOPES:
        failures.append("host_mutate_not_forbidden")

    home = ensure_home(Path(tempfile.mkdtemp(prefix="ci-v5-")) / "home")
    store = Store(home / "cortex.db")
    try:
        boot = bootstrap_repository(home, store, ROOT, "CortexV5CI", force=True, external=True)
        cert = (boot.get("certificate") or {}).get("status")
        if cert not in {"verified", "degraded"}:
            failures.append(f"bootstrap:{cert}")
        state = compile_interlink(
            store, "CortexV5CI", resolutions=("file", "symbol", "basic_block")
        )
        if (state.get("resolutions") or {}).get("file", 0) < 1:
            failures.append("multi_res_file")
        built = build_hnsw_index(store, "CortexV5CI")
        if not built.get("built") and built.get("reason") != "no_vectors":
            failures.append(f"hnsw:{built}")
        ensure_ranker(store, "CortexV5CI")
        train = train_from_outcome(
            store,
            "CortexV5CI",
            outcome_id="ci_out",
            activation_id="ci_act",
            status="verified",
            reward=1.0,
            verification_type="ci",
            governance_mode="normal",
        )
        if not train.get("trained"):
            failures.append("ranker_train")
        chk = check_contract(
            {
                "governor": {"mode": "normal"},
                "control_error": {"block": False},
                "authority": {"cortex_may_mutate": False},
                "claim_boundary": "ci",
                "operational_state": {"evidence_ids": [1]},
            },
            contract=DEFAULT_CONTRACT,
        )
        if not chk.get("passed"):
            failures.append(f"contract:{chk.get('breaks')}")
        reg = register_agent(store, "CortexV5CI", "ci-agent", "CI")
        if not reg.get("registered"):
            failures.append("agent_register")
        bad = mint_token(store, "CortexV5CI", "ci-agent", ["host.mutate"])
        if bad.get("minted"):
            failures.append("host_mutate_minted")
        payload = {
            "passed": not failures,
            "failures": failures,
            "resolutions": state.get("resolutions"),
            "hnsw": hnsw_status(store, "CortexV5CI"),
            "ranker_trained": train.get("trained"),
            "claim_boundary": "Self-host v5 substrate regression only.",
        }
        print(json.dumps(payload, indent=2, default=str))
        return 0 if not failures else 1
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
