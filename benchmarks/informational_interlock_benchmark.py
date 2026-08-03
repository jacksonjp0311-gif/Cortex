"""Deterministic v8.2 E-L-O interlock benchmark and lesion receipt."""

from __future__ import annotations

import json
import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cortex.math_net.info_interlock import interlock_report  # noqa: E402
from cortex.store import Store  # noqa: E402


def main() -> int:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        store = Store(root / "cortex.db")
        store.attach("InterlockBench", "rid", root)
        patterns = ((0, 0), (0, 1), (1, 0), (1, 1))
        try:
            for i in range(256):
                e, learned = patterns[i % 4]
                activation_id = f"act-{i:04d}"
                outcome_id = f"out-{i:04d}"
                store.record_neural_activation(
                    "InterlockBench",
                    "session",
                    {
                        "activation_id": activation_id,
                        "task_hash": "xor",
                        "state_hash": activation_id,
                        "records": [],
                        "traversed_synapses": [],
                    },
                )
                store.record_interlock_observation(
                    "InterlockBench",
                    activation_id=activation_id,
                    session_id="session",
                    body_epoch_id="epoch-v82",
                    task_family="benchmark",
                    evidence_paths=["evidence"] if e else [],
                    learned_paths=["learned"] if learned else [],
                    constitutional_valid=True,
                )
                reward = 1.0 if e ^ learned else -1.0
                store.record_outcome(
                    "InterlockBench",
                    outcome_id=outcome_id,
                    activation_id=activation_id,
                    status="verified" if reward > 0 else "failed",
                    reward=reward,
                    verification_type="deterministic_xor",
                    verification_payload={},
                    credits=[],
                    updates=[],
                    apply_updates=False,
                )
                store.resolve_interlock_outcome(
                    "InterlockBench",
                    activation_id=activation_id,
                    outcome_id=outcome_id,
                    status="verified" if reward > 0 else "failed",
                    reward=reward,
                    verification_type="deterministic_xor",
                )

            timings: list[float] = []
            report = {}
            for _ in range(25):
                started = time.perf_counter()
                report = interlock_report(
                    store, "InterlockBench", include_lesion=False
                )
                timings.append((time.perf_counter() - started) * 1000.0)
            report = interlock_report(store, "InterlockBench", include_lesion=True)
            top = (report.get("top_interlocks") or [{}])[0]
            receipt = {
                "schema_version": "cortex-information-interlock-benchmark/1.0",
                "samples": report["counts"]["valid"],
                "synergy_proxy_bits": top.get("synergy_proxy_bits"),
                "alignment": top.get("alignment"),
                "lesion": report.get("lesion"),
                "latency_ms": {
                    "median": round(statistics.median(timings), 4),
                    "p95": round(sorted(timings)[int(0.95 * (len(timings) - 1))], 4),
                },
                "checks": {
                    "data_ready": report.get("data_ready") is True,
                    "synergy_gt_0_9": float(top.get("synergy_proxy_bits") or 0.0) > 0.9,
                    "lesion_supported": (report.get("lesion") or {}).get("supported") is True,
                    "shadow_only": report.get("mode") == "shadow",
                },
                "claim_boundary": report.get("claim_boundary"),
            }
            receipt["passed"] = all(receipt["checks"].values())
            print(json.dumps(receipt, indent=2))
            return 0 if receipt["passed"] else 1
        finally:
            store.close()


if __name__ == "__main__":
    raise SystemExit(main())
