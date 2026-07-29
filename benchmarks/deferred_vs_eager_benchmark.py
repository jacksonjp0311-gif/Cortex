"""Compare deferred vs eager ARIA substrate indexing on a synthetic host.

Emits work-proxy economics and bootstrap timing under controlled conditions.
Not a universal performance claim.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import tempfile
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from cortex.aria_meta.substrate import is_internal_aria_path  # noqa: E402
from cortex.bootstrap import bootstrap_repository  # noqa: E402
from cortex.config import RepoConfig, ensure_home, save_repo_config  # noqa: E402
from cortex.store import Store  # noqa: E402


def _build_host(base: Path, *, aria_docs: int = 40) -> Path:
    host = base / "host"
    host.mkdir()
    (host / "README.md").write_text(
        "# Foreign Host\n\n## Architecture\n\nPlanner uses memory.\n\n"
        "## Native ARIA semantic language\n\nOptional mention for probe stress.\n",
        encoding="utf-8",
    )
    (host / "app.py").write_text(
        "def main() -> str:\n    return 'ok'\n",
        encoding="utf-8",
    )
    (host / "pyproject.toml").write_text(
        "[project]\nname='foreign-host'\nversion='0.1.0'\n",
        encoding="utf-8",
    )
    vendor = host / "cortex" / "aria_meta" / "vendor"
    (vendor / "docs").mkdir(parents=True)
    (vendor / "grammar").mkdir(parents=True)
    (vendor / "ARIA-RUNTIME.json").write_text("{}", encoding="utf-8")
    (vendor / "ARIA-CONNECT.json").write_text("{}", encoding="utf-8")
    (vendor / "README.md").write_text("# ARIA\n", encoding="utf-8")
    (vendor / "AGENTS.md").write_text("# agents\n", encoding="utf-8")
    (vendor / "VERSION").write_text("0.0.0\n", encoding="utf-8")
    (vendor / "MANIFEST.sha256").write_text("", encoding="utf-8")
    (vendor / "aria.policy.json").write_text("{}", encoding="utf-8")
    (vendor / "aria.lock.json").write_text("{}", encoding="utf-8")
    (vendor / "grammar" / "semantic-cues.json").write_text(
        json.dumps({"format": "test", "cues": []}), encoding="utf-8"
    )
    (vendor / "grammar" / "glyphs.json").write_text("{}", encoding="utf-8")
    (vendor / "grammar" / "glyph-cards.json").write_text("{}", encoding="utf-8")
    (vendor / "grammar" / "opcodes.json").write_text("{}", encoding="utf-8")
    for index in range(aria_docs):
        (vendor / "docs" / f"spec-{index:03d}.md").write_text(
            f"# Spec {index}\n\nSemantic replay cooperative mesh session handoff notes.\n",
            encoding="utf-8",
        )
    return host


def _run_once(mode: str, host: Path, runs: int) -> dict:
    samples = []
    for _ in range(runs):
        with tempfile.TemporaryDirectory(prefix=f"cortex-{mode}-") as temporary:
            base = Path(temporary)
            home = ensure_home(base / "home")
            store = Store(home / "cortex.db")
            # Pre-seed config mode via bootstrap path: patch after first config write
            started = time.perf_counter()
            result = bootstrap_repository(home, store, host, f"Host{mode.title()}")
            # Re-bootstrap with forced mode on config
            config = RepoConfig(
                repository_name=f"Host{mode.title()}",
                repository_id=result["repository_id"],
                aria_substrate_indexing=mode,
            )
            config.engine_module_root = str(Path(__file__).resolve().parents[1])
            config.cortex_home = str(home)
            save_repo_config(host, config)
            store.close()
            store = Store(home / "cortex.db")
            started = time.perf_counter()
            result = bootstrap_repository(
                home, store, host, f"Host{mode.title()}", force=True
            )
            elapsed = time.perf_counter() - started
            aria = result["index"].get("aria_substrate", {})
            deferred = sum(
                1
                for row in store.files(f"Host{mode.title()}")
                if row["status"] == "substrate_deferred"
            )
            indexed_aria = sum(
                1
                for row in store.files(f"Host{mode.title()}")
                if row["status"] == "indexed" and is_internal_aria_path(row["path"])
            )
            samples.append(
                {
                    "bootstrap_seconds": round(elapsed, 6),
                    "certificate": result["certificate"]["status"],
                    "deferred": deferred,
                    "indexed_aria": indexed_aria,
                    "work_proxy": aria.get("work_proxy"),
                }
            )
            store.close()
    seconds = [sample["bootstrap_seconds"] for sample in samples]
    return {
        "mode": mode,
        "runs": runs,
        "median_bootstrap_seconds": statistics.median(seconds),
        "mean_bootstrap_seconds": statistics.mean(seconds),
        "samples": samples,
        "certificate_verified": all(sample["certificate"] == "verified" for sample in samples),
        "median_deferred": statistics.median([sample["deferred"] for sample in samples]),
        "median_indexed_aria": statistics.median(
            [sample["indexed_aria"] for sample in samples]
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--aria-docs", type=int, default=40)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("benchmarks/results"),
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="cortex-deferred-eager-host-") as temporary:
        host = _build_host(Path(temporary), aria_docs=args.aria_docs)
        deferred = _run_once("deferred", host, args.runs)
        eager = _run_once("eager", host, args.runs)

    speedup = (
        eager["median_bootstrap_seconds"] / deferred["median_bootstrap_seconds"]
        if deferred["median_bootstrap_seconds"]
        else 0.0
    )
    payload = {
        "schema_version": "cortex-deferred-vs-eager/1.0",
        "aria_docs": args.aria_docs,
        "deferred": deferred,
        "eager": eager,
        "bootstrap_speedup_eager_over_deferred": round(speedup, 6),
        "claim_boundary": (
            "Synthetic host comparison of indexing modes only; not universal "
            "repository performance or answer quality."
        ),
    }
    json_path = args.output_dir / "deferred_vs_eager.json"
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    # Minimal SVG chart
    d = deferred["median_bootstrap_seconds"]
    e = eager["median_bootstrap_seconds"]
    max_v = max(d, e, 0.001)
    d_h = int(200 * d / max_v)
    e_h = int(200 * e / max_v)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360" role="img" aria-label="Deferred vs eager bootstrap">
  <rect width="640" height="360" fill="#101418"/>
  <text x="32" y="40" fill="#f0f4f8" font-family="Arial" font-size="20">ARIA substrate: deferred vs eager bootstrap</text>
  <rect x="140" y="{280 - d_h}" width="120" height="{d_h}" fill="#22c55e"/>
  <rect x="360" y="{280 - e_h}" width="120" height="{e_h}" fill="#a878ff"/>
  <text x="150" y="310" fill="#d4dce8" font-family="Arial" font-size="14">deferred {d:.3f}s</text>
  <text x="380" y="310" fill="#d4dce8" font-family="Arial" font-size="14">eager {e:.3f}s</text>
  <text x="32" y="340" fill="#8b9bb4" font-family="Arial" font-size="12">Controlled synthetic host; engineering telemetry only.</text>
</svg>
'''
    (args.output_dir / "deferred_vs_eager.svg").write_text(svg, encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
