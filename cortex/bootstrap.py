from __future__ import annotations

import hashlib
import sys
import time
import uuid
from pathlib import Path
from typing import Any

from .config import (
    RepoConfig,
    external_repo_config_path,
    load_repo_config,
    repo_config_path,
    runtime_directory,
)
from .environment import learn_environment
from .graph import resolve_graph
from .indexer import index_repository
from .integration import install_external_attachment, install_integration
from .neuron import compile_interlink
from .telemetry import ingest_git
from .verify import verify_repository


def stable_repository_id(root: Path) -> str:
    normalized = str(root.resolve()).replace("\\", "/").lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:24]


def _is_ci_scratch_home(path: Path | str) -> bool:
    """True only for known CI smoke scratch homes (not all OS temp).

    Operator bodies under ~/.cortex and normal temp test fixtures must still
    require --allow-home-rebind. Sequential CI smokes use explicit prefixes
    (ci-teach-, ci-retrieval-, …) so they can rebind without poisoning durable
    operator identity.
    """
    s = str(Path(path).expanduser().resolve()).replace("\\", "/").lower()
    markers = (
        "ci-teach-",
        "ci-retrieval-",
        "ci-connect-",
        "ci-immune-",
        "ci-mesh-",
        "ci-spectral-",
        "ci-v5-",
        "ci-ma-",
        "ci-multi-",
        "/ci-cortex-",
        "\\ci-cortex-",
    )
    return any(m in s for m in markers)


def bootstrap_repository(
    home: Path,
    store: Any,
    root: Path,
    name: str | None = None,
    *,
    force: bool = False,
    preserve_agents: bool = False,
    external: bool = False,
    allow_home_rebind: bool = False,
) -> dict[str, Any]:
    root = root.expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"Repository directory not found: {root}")
    repository_name = name or root.name
    repository_id = stable_repository_id(root)
    rebind_from: str | None = None
    rebind_auto_disposable = False
    selected_config_exists = (
        external_repo_config_path(root, home).exists()
        if external
        else repo_config_path(root).exists()
    )
    if selected_config_exists:
        config = load_repo_config(root, home, prefer_external=external)
        configured_home = str(config.cortex_home or "").strip()
        requested_home = str(home.resolve())
        if configured_home:
            previous_home = str(Path(configured_home).expanduser().resolve())
            if previous_home.casefold() != requested_home.casefold():
                # Durable operator bodies still require explicit --allow-home-rebind.
                # CI scratch→scratch (teach→retrieval sequential smokes) auto-allows
                # with a receipt so one job does not poison the next.
                disposable_pair = _is_ci_scratch_home(previous_home) and _is_ci_scratch_home(
                    requested_home
                )
                if not allow_home_rebind and not disposable_pair:
                    raise RuntimeError(
                        "Cortex home rebind refused: this repository is already bound to "
                        f"{previous_home}; requested {requested_home}. Re-run with the explicit "
                        "--allow-home-rebind migration flag after verifying identity and lineage."
                    )
                rebind_from = previous_home
                rebind_auto_disposable = disposable_pair and not allow_home_rebind
        config.repository_name = repository_name
        config.repository_id = repository_id
    else:
        config = RepoConfig(
            repository_name=repository_name,
            repository_id=repository_id,
        )
    if preserve_agents:
        config.agent_protocol_mode = "preserve"
    if external:
        config.integration_mode = "external"

    config.engine_python = str(Path(sys.executable))
    engine_root = Path(__file__).resolve().parent.parent
    config.engine_module_root = str(engine_root)
    config.cortex_home = str(home.resolve())
    home_identity = store.get_setting("cortex_home_identity", None)
    if not isinstance(home_identity, dict) or not home_identity.get("home_uuid"):
        home_identity = {
            "schema_version": "cortex-home-identity/1.0",
            "home_uuid": uuid.uuid4().hex,
            "db_generation": 1,
            "created_at": time.time(),
        }
        store.set_setting("cortex_home_identity", home_identity)
    if rebind_from:
        store.set_setting(
            f"home_rebind:{repository_id}",
            {
                "schema_version": "cortex-home-rebind/1.0",
                "repository_id": repository_id,
                "from_home": rebind_from,
                "to_home": str(home.resolve()),
                "explicit": bool(allow_home_rebind),
                "auto_disposable": bool(rebind_auto_disposable),
                "at": time.time(),
            },
        )
    try:
        embedded_relative = engine_root.relative_to(root).as_posix()
    except ValueError:
        embedded_relative = ""
    if embedded_relative and embedded_relative != "." and embedded_relative not in config.exclude:
        config.exclude.append(embedded_relative)
    run_id = f"bootstrap-{int(time.time())}-{uuid.uuid4().hex[:8]}"
    identity_warnings: list[str] = []
    try:
        from .identity import continuity_check, warn_on_attach

        identity_warnings = warn_on_attach(
            store, repository_name, repository_id, root
        )
        continuity = continuity_check(store, path=root)
        if continuity.get("continuity", {}).get("split_identity"):
            identity_warnings.append(
                "split_identity_on_path: durable namespaces must not be merged silently"
            )
    except Exception:
        continuity = None
    store.attach(repository_name, repository_id, root)
    store.begin_bootstrap(run_id, repository_name)

    try:
        integration = (
            install_external_attachment(home, root, config)
            if config.integration_mode == "external"
            else install_integration(root, config)
        )
        index = index_repository(store, repository_name, config, force=force)
        graph = resolve_graph(store, repository_name)
        telemetry = ingest_git(store, repository_name, root, config.git_commit_limit)
        environment = (
            learn_environment(
                root,
                store,
                repository_name,
                runtime_directory(root, config),
            )
            if config.environment_learning_enabled
            else {"available": False, "disabled": True}
        )
        neural = (
            compile_interlink(store, repository_name)
            if config.neural_interlink_enabled
            else {"available": False, "disabled": True}
        )
        # Spectral annotate + optional HNSW (v6.1) — local only
        hnsw_build: dict[str, Any] | None = None
        try:
            from .kernels import annotate_synapses, load_kernel_profile

            load_kernel_profile(store, repository_name)
            if config.neural_interlink_enabled:
                annotate_synapses(store, repository_name)
        except Exception:
            pass
        try:
            from .vectors import build_hnsw_index

            # Always attempt light HNSW after bootstrap so semantic decoder exists
            hnsw_build = build_hnsw_index(store, repository_name)
        except Exception as exc:
            hnsw_build = {"built": False, "error": f"{type(exc).__name__}: {exc}"}
        certificate = verify_repository(home, store, repository_name, config, write_certificate=True)
        store.finish_bootstrap(run_id, certificate["status"], index["manifest_hash"], certificate)
        return {
            "run_id": run_id,
            "repo": repository_name,
            "repository_id": repository_id,
            "root": str(root),
            "integration": integration,
            "index": index,
            "graph": graph,
            "telemetry": telemetry,
            "environment": environment,
            "neural_interlink": neural,
            "hnsw": hnsw_build,
            "certificate": certificate,
            "identity": {
                "body": {
                    "repository_id": repository_id,
                    "home_uuid": home_identity.get("home_uuid"),
                    "db_generation": home_identity.get("db_generation"),
                },
                "home_rebind": {
                    "performed": bool(rebind_from),
                    "from_home": rebind_from,
                    "to_home": str(home.resolve()),
                },
                "warnings": identity_warnings,
                "continuity": (continuity or {}).get("continuity") if continuity else None,
                "path_aliases": (continuity or {}).get("path_aliases") if continuity else None,
                "claim_boundary": (
                    "Same filesystem path with different repo names are separate "
                    "memory namespaces unless explicitly checked."
                ),
            },
            "next_command": {
                "powershell": (
                    f'python -m cortex --home "{home}" activate --repo "{repository_name}" '
                    '--task "<current task>" --json'
                    if config.integration_mode == "external"
                    else '.cortex\\bin\\cortex.ps1 activate -Task "<current task>"'
                ),
                "bash": (
                    f'python -m cortex --home "{home}" activate --repo "{repository_name}" '
                    '--task "<current task>" --json'
                    if config.integration_mode == "external"
                    else './.cortex/bin/cortex.sh activate --task "<current task>"'
                ),
            },
        }
    except Exception as exc:
        failure = {
            "schema_version": "1.0",
            "status": "failed",
            "repo": repository_name,
            "run_id": run_id,
            "error": f"{type(exc).__name__}: {exc}",
            "failed_at": time.time(),
        }
        store.finish_bootstrap(run_id, "failed", "", failure)
        store.update_repo_state(repository_name, bootstrap_status="failed")
        raise
