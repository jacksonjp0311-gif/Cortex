from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import load_repo_config
from .indexer import current_manifest_hash
from .verify import verify_repository


def health_report(home: Path, store: Any, governor: Any, repo: str) -> dict[str, Any]:
    repository = store.repo(repo)
    if not repository:
        raise ValueError(f"Unknown repository: {repo}. Run cortex bootstrap first.")
    root = Path(repository["path"])
    config = load_repo_config(root)
    current = current_manifest_hash(root, config) == (repository["manifest_hash"] or "")
    certificate = verify_repository(home, store, repo, config, write_certificate=False)
    drift = "current" if current else "source_or_configuration_drift"
    vectors = store.vector_format_status(repo)
    command = "cortex activate --repo {0} --task \"<task>\" --refresh packet-fast --json".format(repo)
    if not current:
        command = "cortex activate --repo {0} --task \"<task>\" --refresh packet-refresh --json".format(repo)
    elif vectors["legacy_or_invalid"]:
        command = f"cortex migrate-vectors --repo {repo} --json"
    gov = governor.evaluate(repo, manifest_current=current, certificate=certificate)
    from .control_error import build_control_error
    from .identity import home_looks_temporary
    from .progress_glyphs import progress_glyph_registry

    control = build_control_error(
        certificate=certificate,
        governance=gov,
        manifest_current=current,
        retrieval_confidence=0.0,
        aria_materialization={},
    )
    if control.get("must_reverify"):
        command = f"cortex verify --repo {repo} --json"
    temporary_home = home_looks_temporary(home) or home_looks_temporary(
        getattr(config, "cortex_home", None)
    )
    binding_notes: list[str] = []
    if temporary_home:
        binding_notes.append(
            "cortex_home_looks_temporary — re-bootstrap with stable CORTEX_HOME "
            "(e.g. ~/.cortex) for cross-process continuity"
        )
    if control.get("must_reverify") or not current:
        binding_notes.append(
            "reverify_boundary — after mirror/contact stress or manifest drift, "
            "run activate or verify before treating health as steady-state"
        )
    hygiene: dict[str, Any] | None = None
    try:
        from .hygiene import body_hygiene

        hygiene = body_hygiene(home, store, repo, config=config)
        for tip in hygiene.get("advice") or []:
            if tip not in {"hold_course"} and tip not in binding_notes:
                binding_notes.append(f"hygiene:{tip}")
    except Exception:
        hygiene = None
    return {
        "schema_version": "1.4",
        "repo": repo,
        "certificate_status": certificate["status"],
        "governor": gov,
        "block": bool(control.get("block")),
        "immune_action": control.get("immune_action"),
        "control_error": control,
        "drift": {"classification": drift, "manifest_current": current, "volatile_surfaces_excluded": True},
        "vectors": vectors,
        "home": {
            "path": str(home),
            "temporary": temporary_home,
            "config_cortex_home": getattr(config, "cortex_home", None),
        },
        "hygiene": hygiene,
        "binding_notes": binding_notes,
        "progress_glyphs": progress_glyph_registry(),
        "recommended_next_command": command,
        "identity": f"cortex identity --repo {repo} --json",
        "immune": f"cortex immune --repo {repo} --json",
        "hygiene_cmd": f"cortex hygiene --repo {repo} --json",
        "harness": f"cortex harness --repo {repo} --json",
        "teach": "cortex teach",
        "transcend_check": "cortex transcend-check --json",
        "claim_boundary": "Health is local operational telemetry; it grants no mutation authority.",
    }
