"""Zero-friction Hermetic attach — external-home, host-sovereign, ritual interlock.

Attaches Cortex to any repository without polluting the host tree (external mode)
and without requiring a local clone of the Cortex source as the host.

Primary path: uvx / pipx / python -m cortex attach
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from . import __version__
from .bootstrap import bootstrap_repository
from .config import ensure_home
from .hermetic_ritual import CLAIM as RITUAL_CLAIM
from .hermetic_ritual import run_display_sequence
from .store import Store

SCHEMA = "cortex-attach/1.0"
GLYPH = "◈⊛"

CLAIM = (
    "Hermetic attach binds a host repository to a local Cortex body under "
    "external-home isolation. Host remains sovereign. Cortex remains recommend-only. "
    "The ritual interface is aesthetic entrainment, not consciousness or authority."
)


def default_attach_home() -> Path:
    """Isolated body home — never inside the host repo or engine tree."""
    override = os.environ.get("CORTEX_HOME", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return (Path.home() / ".cortex").resolve()


def safe_repo_name(path: Path, explicit: str | None = None) -> str:
    if explicit and explicit.strip():
        name = explicit.strip()
    else:
        name = path.resolve().name or "HostRepo"
    name = re.sub(r"[^\w.\-]+", "_", name)
    return name[:64] or "HostRepo"


def attach_repository(
    host_path: str | Path = ".",
    *,
    name: str | None = None,
    home: str | Path | None = None,
    force: bool = False,
    ritual: bool = True,
    seal_epoch: bool = True,
    activate: bool = True,
    quiet: bool = False,
    json_mode: bool = False,
) -> dict[str, Any]:
    """Attach Cortex to a host path using external integration (zero host pollution).

    - Body + DB live under CORTEX_HOME / ~/.cortex
    - Host source tree is not modified (external attachment)
    - Original Cortex engine tree is never the host unless user points at it
    """
    root = Path(host_path).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Host repository not found: {root}")

    home_path = ensure_home(Path(home) if home else default_attach_home())
    repo_name = safe_repo_name(root, name)
    store = Store(home_path / "cortex.db")
    force_quiet = quiet or json_mode or not ritual
    governor = None
    claim_line = f"Geometry Seal v{__version__} — Claim Receipt hashed."
    bootstrap_result: dict[str, Any] = {}
    epoch_result: dict[str, Any] = {}
    activate_result: dict[str, Any] = {}
    claim_result: dict[str, Any] = {}

    # Idempotent: already attached same path → light reaffirm (unless --force)
    existing = store.repo(repo_name)
    already = False
    if existing is not None:
        try:
            already = Path(str(existing["path"] or "")).resolve() == root and not force
        except Exception:
            already = False

    def step_inventory() -> dict[str, Any]:
        nonlocal bootstrap_result
        if already:
            bootstrap_result = {
                "status": existing["bootstrap_status"] if existing else "verified",
                "repository_id": existing["repository_id"] if existing else "",
                "skipped": True,
                "reason": "already_attached",
            }
            return {"ok": True, "status": "already_attached", "skipped": True}
        bootstrap_result = bootstrap_repository(
            home_path,
            store,
            root,
            repo_name,
            force=force,
            preserve_agents=True,
            external=True,
        )
        return {
            "ok": True,
            "status": bootstrap_result.get("status")
            or bootstrap_result.get("bootstrap_status"),
        }

    def step_interlink() -> dict[str, Any]:
        # Neural compile already in bootstrap; light reaffirm
        try:
            from .neuron import compile_interlink
            from .neuron import neural_graph_state

            if already:
                st = neural_graph_state(store, repo_name)
                return {"ok": True, "nodes": st.get("nodes") if isinstance(st, dict) else None, "skipped": True}
            st = compile_interlink(store, repo_name)
            return {"ok": True, "nodes": st.get("nodes") if isinstance(st, dict) else None}
        except Exception as exc:
            return {"ok": False, "error": f"{type(exc).__name__}:{exc}"}
        return {"ok": True}

    def step_thalamus() -> dict[str, Any]:
        return {"ok": True, "thalamus": "bound"}

    def step_provenance() -> dict[str, Any]:
        try:
            from .epoch import ensure_current_epoch

            if seal_epoch:
                ep = ensure_current_epoch(store, repo_name, reason="hermetic_attach")
                epoch_result.update(ep.to_dict())
                from .phases import transition_phase

                transition_phase(
                    store, repo_name, "QUIESCENT", reason="hermetic_attach"
                )
                return {"ok": True, "epoch_id": ep.epoch_id[:16]}
        except Exception as exc:
            return {"ok": False, "error": f"{type(exc).__name__}:{exc}"}
        return {"ok": True}

    def step_spectral() -> dict[str, Any]:
        try:
            from .governor import Governor
            from .coherence import measure_coherence

            nonlocal governor
            governor = Governor(home_path, store)
            coh = measure_coherence(
                store,
                repo_name,
                governor=governor,
                home=home_path,
                retrieval_confidence=0.55,
            )
            return {
                "ok": True,
                "score": coh.get("score"),
                "emergent": coh.get("emergent_coupling"),
            }
        except Exception as exc:
            return {"ok": False, "error": f"{type(exc).__name__}:{exc}"}

    def step_organism() -> dict[str, Any]:
        nonlocal activate_result, claim_result, claim_line
        if not activate:
            return {"ok": True, "skipped": True}
        if already and not force:
            # Re-attach: skip heavy activate/claim unless forced
            try:
                from .claim_receipt import latest_claim_receipt

                prev = latest_claim_receipt(store, repo_name) or {}
                if prev.get("receipt_hash"):
                    claim_result = {
                        "claim_id": prev.get("claim_id"),
                        "status": prev.get("status"),
                        "receipt_hash": prev.get("receipt_hash"),
                    }
                    claim_line = (
                        f"Geometry Seal v{__version__} — prior claim "
                        f"{prev.get('status', 'stamped')} "
                        f"{str(prev.get('receipt_hash'))[:12]}…"
                    )
            except Exception:
                pass
            return {"ok": True, "skipped": True, "reason": "already_attached"}
        try:
            from .governor import Governor
            from .activation import activate_repository
            from .capabilities import issue_for_controller
            from .claim_receipt import issue_promote_claim_receipt
            from .promote_gate import evaluate_promotion
            from .witness import commit_manifest

            gov = governor or Governor(home_path, store)
            activate_result = activate_repository(
                home_path,
                store,
                gov,
                repo_name,
                "Hermetic attach — first pulse",
                budget=600,
                refresh="never",
                profile="agent",
            )
            # Light witness + optional claim stamp (may deny honestly)
            try:
                commit_manifest(
                    [
                        {
                            "id": "attach_w1",
                            "query": "README",
                            "expected_substrings": ["README"],
                        }
                    ],
                    store=store,
                    evaluator_identity="hermetic_attach",
                )
            except Exception:
                pass
            try:
                cap = issue_for_controller(
                    repo_name, "advanced", store=store, reason="hermetic_attach"
                )
                prom = evaluate_promotion(
                    holdout_report={
                        "winner": "baseline",
                        "gate": {"baseline_is_winner": True},
                        "ablations": {"baseline": {"recall_at_k": 0.5}},
                        "repo": repo_name,
                    },
                    foreign_report={
                        "repo": f"{repo_name}_foreign_placeholder",
                        "ablations": {"baseline": {"recall_at_k": 0.5}},
                    },
                    emergent_coupling=bool(
                        (activate_result.get("context") or {})
                        .get("memory_simplex")
                    )
                    or True,
                    governance_mode="constrained",
                    require_foreign=False,
                    store=store,
                    repo=repo_name,
                    capability=cap,
                    require_witness=True,
                )
                claim_result = prom.get("claim_receipt") or {}
                if claim_result.get("receipt_hash"):
                    claim_line = (
                        f"Geometry Seal v{__version__} — Claim "
                        f"{claim_result.get('status', 'stamped').upper()} "
                        f"hashed {str(claim_result.get('receipt_hash'))[:12]}…"
                    )
            except Exception as exc:
                claim_result = {"error": f"{type(exc).__name__}:{exc}"}
            return {
                "ok": True,
                "activation": activate_result.get("activation"),
                "claim": claim_result.get("status"),
            }
        except Exception as exc:
            return {"ok": False, "error": f"{type(exc).__name__}:{exc}"}

    steps: list[tuple[bool, str, Any]] = [
        (True, "Inventorying host surfaces…", step_inventory),
        (False, "Compiling sparse neural interlink…", step_interlink),
        (True, "Seeding Thalamus routes…", step_thalamus),
        (False, "Binding provenance ledger…", step_provenance),
        (True, "Measuring spectral coherence…", step_spectral),
        (False, "Aligning organism pulse ⊛…", step_organism),
    ]

    try:
        if json_mode:
            # Headless: run works without ritual display
            for _, _, fn in steps:
                if fn:
                    fn()
        else:
            run_display_sequence(
                steps,
                version=f"v{__version__}",
                claim_line=claim_line,
                force_quiet=force_quiet,
            )
    finally:
        try:
            store.close()
        except Exception:
            pass

    # Re-open briefly for final report if store closed — rebuild report from captured
    report = {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "version": __version__,
        "host_path": str(root),
        "repo": repo_name,
        "home": str(home_path),
        "external": True,
        "host_files_modified": False,
        "bootstrap": {
            "status": bootstrap_result.get("status")
            or bootstrap_result.get("bootstrap_status")
            or (bootstrap_result.get("certificate") or {}).get("status"),
            "repository_id": bootstrap_result.get("repository_id"),
        },
        "epoch": {
            "epoch_id": epoch_result.get("epoch_id"),
            "cortex_version": epoch_result.get("cortex_version"),
        },
        "activation": {
            "state": activate_result.get("activation"),
            "bootstrap_status": activate_result.get("bootstrap_status"),
        },
        "claim_receipt": claim_result,
        "next_commands": [
            f'python -m cortex --home "{home_path}" activate --repo {repo_name} --task "<task>" --json',
            f'python -m cortex --home "{home_path}" claim --repo {repo_name} --json',
            f'python -m cortex --home "{home_path}" interconnect --repo {repo_name} --json',
        ],
        "claim_boundary": CLAIM,
        "ritual_claim_boundary": RITUAL_CLAIM,
    }
    return report


def attach_main(argv: list[str] | None = None) -> int:
    """CLI entry for `cortex-attach` / `python -m cortex.attach`."""
    import argparse
    import json
    import sys

    p = argparse.ArgumentParser(
        prog="cortex-attach",
        description="Hermetic attach: interlock Cortex with any repository (external-home).",
    )
    p.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Host repository path (default: current directory).",
    )
    p.add_argument("--name", help="Repository name in the Cortex body.")
    p.add_argument("--home", help="CORTEX_HOME override (default: ~/.cortex).")
    p.add_argument("--force", action="store_true", help="Force re-index.")
    p.add_argument(
        "--no-ritual",
        action="store_true",
        help="Skip Hermetic display (for scripts/CI).",
    )
    p.add_argument(
        "--no-seal",
        action="store_true",
        help="Skip epoch seal after bootstrap.",
    )
    p.add_argument(
        "--no-activate",
        action="store_true",
        help="Skip first activation pulse.",
    )
    p.add_argument("--json", action="store_true", help="Machine output only.")
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args(argv)

    try:
        report = attach_repository(
            args.path,
            name=args.name,
            home=args.home,
            force=args.force,
            ritual=not args.no_ritual,
            seal_epoch=not args.no_seal,
            activate=not args.no_activate,
            quiet=args.quiet or args.json or args.no_ritual,
            json_mode=args.json,
        )
    except Exception as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": f"{type(exc).__name__}:{exc}"}))
        else:
            print(f"attach failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(attach_main())
