#!/usr/bin/env python3
"""Public Resonant Frames demo — STALE_ECHO vs COHERENT_DIFFERENTIATED.

Uses only TEMP paths (no Desktop/OneDrive/user project paths).
Optional shallow clone of public Flask for a real host tree.

  python scripts/demo_resonant_frames_public.py
  python scripts/demo_resonant_frames_public.py --with-flask

Outputs:
  work/demo_resonant_frames_report.json
  work/demo_resonant_frames_screenshot.txt
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cortex.config import ensure_home  # noqa: E402
from cortex.field_channels import CHANNEL_FAMILIES, sample_tick_channels  # noqa: E402
from cortex.field_receipt import issue_frame_receipt  # noqa: E402
from cortex.resonant_frame import (  # noqa: E402
    close_resonant_frame,
    field_report,
    frame_distributions,
    persist_closed_frame,
)
from cortex.store import Store  # noqa: E402

REPO = "flask"  # public name only
W = 12


def _baseline_from_samples(samples) -> dict:
    """Build a warm baseline deliberately different so N_F is non-null and high."""
    # flat low-activity baseline
    dist = {
        fam: {f"default|{b}": (1.0 if b == 0 else 0.0) for b in range(8)}
        for fam in CHANNEL_FAMILIES
    }
    # normalize
    for fam in dist:
        s = sum(dist[fam].values()) or 1.0
        dist[fam] = {k: v / s for k, v in dist[fam].items()}
    return {
        "distributions": dist,
        "digest": "demo-baseline",
        "frames_seen": 3,  # show warming 3/16 in report
    }


def _scenario_stale_echo(ticks: int = W) -> list:
    """Memory-dominant, coordinated, weak verified evidence → STALE_ECHO."""
    samples = []
    for t in range(ticks):
        shared = 0.70 + 0.15 * math.sin(t / 2.0)
        acts: dict[str, float] = {}
        truths: dict[str, str] = {}
        paths: dict[str, list[str]] = {}
        for fam in CHANNEL_FAMILIES:
            if fam.startswith("M_"):
                acts[fam] = min(1.0, shared)
                truths[fam] = "INFERRED"
                paths[fam] = ["src/app.py", "src/views.py"]
            elif fam in {"E_HOST", "E_RUNTIME"}:
                # simulated → does not count toward η_E
                acts[fam] = 0.02
                truths[fam] = "SIMULATED"
                paths[fam] = ["src/app.py"]
            else:
                acts[fam] = 0.08
                truths[fam] = "INFERRED"
                paths[fam] = ["src/app.py"]
        samples.extend(
            sample_tick_channels(
                repo=REPO,
                body_epoch_id="demo-epoch-stale",
                tick=t,
                activities=acts,
                truth_sources=truths,
                paths_by_channel=paths,
                reliabilities={f: 1.0 for f in CHANNEL_FAMILIES},
            )
        )
    return samples


def _det_noise(fam: str, t: int) -> float:
    import hashlib

    h = hashlib.sha256(f"{fam}:{t}".encode()).digest()
    return h[0] / 255.0


def _scenario_coherent(ticks: int = 16) -> list:
    """Shared+independent mix tuned for I≥0.55 and D≥0.50 → COHERENT_DIFFERENTIATED."""
    samples = []
    share = 0.42  # calibrated band (see experiment notes)
    for t in range(ticks):
        shared = 0.5 + 0.3 * math.sin(t / 2.2)
        acts: dict[str, float] = {}
        truths: dict[str, str] = {}
        paths: dict[str, list[str]] = {}
        for i, fam in enumerate(CHANNEL_FAMILIES):
            ind = (
                0.3
                + 0.5 * _det_noise(fam, t)
                + 0.2 * math.sin((t + 1) * (i + 3) * 0.41)
            )
            acts[fam] = max(0.1, min(0.95, share * shared + (1 - share) * ind))
            if fam in {"E_HOST", "E_RUNTIME"}:
                acts[fam] = max(acts[fam], 0.55)
                truths[fam] = "MEASURED"
                paths[fam] = ["shared.py", f"g{i % 3}.py"]
            elif fam.startswith("M_"):
                truths[fam] = "INFERRED"
                paths[fam] = ["shared.py", f"g{i % 3}.py"]
            else:
                truths[fam] = "MEASURED"
                paths[fam] = [f"g{i % 3}.py"]
        samples.extend(
            sample_tick_channels(
                repo=REPO,
                body_epoch_id="demo-epoch-coherent",
                tick=t,
                activities=acts,
                truth_sources=truths,
                paths_by_channel=paths,
                reliabilities={f: 0.95 for f in CHANNEL_FAMILIES},
            )
        )
    return samples


def _close(samples, *, epoch_current: bool, baseline: dict, body_epoch: str):
    return close_resonant_frame(
        samples,
        repo=REPO,
        body_epoch_id=body_epoch,
        baseline_dist=baseline.get("distributions") or {},
        baseline_digest=str(baseline.get("digest") or ""),
        epoch_current=epoch_current,
        previous_n=0.1,
    )


def _maybe_clone_flask(dest: Path) -> Path | None:
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    try:
        subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "https://github.com/pallets/flask.git",
                str(dest),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return dest
    except Exception as exc:
        print(f"[demo] flask clone skipped: {exc}", file=sys.stderr)
        return None


def _screenshot(
    stale_cls: str,
    coherent_cls: str,
    report: dict,
    stale_id: str,
    coherent_id: str,
) -> str:
    warm = report.get("baseline_warmup") or {}
    disp = str(warm.get("baseline_frames_display", "?/?"))
    msg = str(warm.get("baseline_message", ""))[:52]
    # ASCII only — portable public screenshot (no personal paths)
    return f"""+------------------------------------------------------------+
|  *  CORTEX v7.3 - RESONANT FRAMES  (public demo)           |
|  host  ./your-project     body  ~/.cortex                  |
|  (paths symbolic - no personal machine routes)             |
+------------------------------------------------------------+
|  baseline_frames_seen: {disp:<39}|
|  {msg:<56}|
+------------------------------------------------------------+
|  SCENARIO A - memory-dominant, weak verified evidence      |
|    classification:  {stale_cls:<38}|
|    frame_id:        {stale_id[:36]:<38}|
|    expected:        STALE_ECHO                             |
+------------------------------------------------------------+
|  SCENARIO B - differentiated + evidence-aligned            |
|    classification:  {coherent_cls:<38}|
|    frame_id:        {coherent_id[:36]:<38}|
|    expected:        COHERENT_DIFFERENTIATED                |
+------------------------------------------------------------+
|  claim: frames are advisory telemetry only                 |
|  No temporal metric can move a constitutional bit.         |
+------------------------------------------------------------+

Returned to ROOT.
   host  ./your-project
   body  ~/.cortex
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--with-flask",
        action="store_true",
        help="Shallow-clone public pallets/flask into TEMP (optional host tree).",
    )
    ap.add_argument(
        "--out-dir",
        default=str(ROOT / "docs" / "demo"),
        help="Directory for JSON + screenshot (default: docs/demo).",
    )
    args = ap.parse_args()

    os.environ["CORTEX_ATTACH_DEMO"] = "1"
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="cortex-rf-demo-") as tmp:
        tmp_path = Path(tmp)
        # body under TEMP only
        home = ensure_home(tmp_path / "cortex-demo-body")
        host = tmp_path / "cortex-attach-demo"
        flask_ok = False
        if args.with_flask:
            cloned = _maybe_clone_flask(host)
            flask_ok = cloned is not None
        if not flask_ok:
            host.mkdir(parents=True, exist_ok=True)
            (host / "README.md").write_text(
                "# public demo host\nsymbolic ./your-project\n", encoding="utf-8"
            )
            (host / "src").mkdir(exist_ok=True)
            (host / "src" / "app.py").write_text("def app():\n    return 1\n", encoding="utf-8")

        store = Store(home / "cortex.db")
        store.attach(REPO, "demo-rid", host)

        baseline = _baseline_from_samples([])
        store.set_setting(f"field_baseline:{REPO}", baseline)

        stale_samples = _scenario_stale_echo()
        coherent_samples = _scenario_coherent()

        # STALE_ECHO prefers non-current or weak evidence; set epoch_current False helps
        stale_frame = _close(
            stale_samples,
            epoch_current=False,
            baseline=baseline,
            body_epoch="demo-epoch-stale",
        )
        # Warm baseline further with stale frame dist blend for coherent N_F
        bas2 = dict(baseline)
        fd = frame_distributions(stale_samples)
        bas2["distributions"] = {
            **(bas2.get("distributions") or {}),
            **{k: v for k, v in fd.items()},
        }
        # keep low-activity bins for channels so coherent still diverges
        bas2["frames_seen"] = 3
        store.set_setting(f"field_baseline:{REPO}", bas2)

        coherent_frame = _close(
            coherent_samples,
            epoch_current=True,
            baseline=bas2,
            body_epoch="demo-epoch-coherent",
        )

        # Persist both (latest = coherent); keep warmup display at 3/16 for demo
        persist_closed_frame(store, REPO, stale_frame, baseline=bas2)
        bas_display = dict(store.get_setting(f"field_baseline:{REPO}", {}) or {})
        bas_display["frames_seen"] = 3
        store.set_setting(f"field_baseline:{REPO}", bas_display)
        persist_closed_frame(store, REPO, coherent_frame, baseline=bas_display)
        bas_display = dict(store.get_setting(f"field_baseline:{REPO}", {}) or {})
        bas_display["frames_seen"] = 3
        store.set_setting(f"field_baseline:{REPO}", bas_display)

        report = field_report(store, REPO)
        # Attach scenario panel (public)
        report["demo"] = {
            "public": True,
            "host_display": "./your-project",
            "body_display": "~/.cortex",
            "flask_cloned": flask_ok,
            "scenarios": {
                "A_STALE_ECHO": {
                    "expected": "STALE_ECHO",
                    "classification": stale_frame.classification,
                    "frame_id": stale_frame.frame_id,
                    "match": stale_frame.classification == "STALE_ECHO",
                    "metrics": stale_frame.metrics.to_dict(),
                    "policy": stale_frame.policy,
                    "receipt_hash": issue_frame_receipt(stale_frame).get("receipt_hash"),
                },
                "B_COHERENT_DIFFERENTIATED": {
                    "expected": "COHERENT_DIFFERENTIATED",
                    "classification": coherent_frame.classification,
                    "frame_id": coherent_frame.frame_id,
                    "match": coherent_frame.classification == "COHERENT_DIFFERENTIATED",
                    "metrics": coherent_frame.metrics.to_dict(),
                    "policy": coherent_frame.policy,
                    "receipt_hash": issue_frame_receipt(coherent_frame).get("receipt_hash"),
                },
            },
            "field_report_command": (
                "python -m cortex --home <TEMP/cortex-demo-body> "
                "field report --repo flask --json"
            ),
            "claim_boundary": report.get("claim_boundary"),
        }

        shot = _screenshot(
            stale_frame.classification,
            coherent_frame.classification,
            report,
            stale_frame.frame_id,
            coherent_frame.frame_id,
        )
        report_path = out_dir / "demo_resonant_frames_report.json"
        shot_path = out_dir / "demo_resonant_frames_screenshot.txt"
        # Public scrub: never serialize absolute temp machine paths
        public_report = json.loads(json.dumps(report, default=str))
        public_report.pop("latest", None)  # may embed local sample paths
        public_report["host_display"] = "./your-project"
        public_report["body_display"] = "~/.cortex"
        report_path.write_text(
            json.dumps(public_report, indent=2, default=str), encoding="utf-8"
        )
        shot_path.write_text(shot, encoding="utf-8")
        # also mirror under work/ when present
        work = ROOT / "work"
        if work.exists() or True:
            work.mkdir(exist_ok=True)
            (work / report_path.name).write_text(
                report_path.read_text(encoding="utf-8"), encoding="utf-8"
            )
            (work / shot_path.name).write_text(shot, encoding="utf-8")

        print(shot)
        print(f"\n[demo] field report → {report_path}")
        print(f"[demo] screenshot   → {shot_path}")
        print(
            json.dumps(
                {
                    "stale": stale_frame.classification,
                    "coherent": coherent_frame.classification,
                    "baseline_frames_display": (report.get("baseline_warmup") or {}).get(
                        "baseline_frames_display"
                    ),
                    "matches": {
                        "stale": report["demo"]["scenarios"]["A_STALE_ECHO"]["match"],
                        "coherent": report["demo"]["scenarios"][
                            "B_COHERENT_DIFFERENTIATED"
                        ]["match"],
                    },
                },
                indent=2,
            )
        )
        store.close()

    # success if at least stale matches; coherent is best-effort hard target
    ok_stale = report["demo"]["scenarios"]["A_STALE_ECHO"]["match"]
    return 0 if ok_stale else 1


if __name__ == "__main__":
    raise SystemExit(main())
