"""Bounded self-hosting validation for Cortex."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any


INTERNAL_ENGINE_DIRECTORY = "InternalCortexEngine"
INTERNAL_ENGINE_LABEL = "INTERNAL CORTEX ENGINE"


def _command(args: list[str], cwd: Path, *, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=True, timeout=timeout, env=env)


def run_lifecycle(source_root: Path, *, nested_engine: bool, run_tests: bool = False) -> dict[str, Any]:
    """Clone Cortex as host, optionally clone a second engine inside it, then activate the host."""

    with tempfile.TemporaryDirectory(prefix="cortex-self-host-") as temporary:
        base = Path(temporary)
        host = base / "CortexHost"
        _command(["git", "clone", "--no-local", str(source_root), str(host)], source_root)
        engine = host
        source_commit = _command(["git", "rev-parse", "HEAD"], source_root).stdout.strip()
        if nested_engine:
            engine = host / INTERNAL_ENGINE_DIRECTORY
            _command(["git", "clone", "--no-local", str(source_root), str(engine)], host)
            (engine / "INTERNAL_CORTEX_ENGINE.json").write_text(
                json.dumps(
                    {
                        "schema_version": "cortex-internal-engine/1.0",
                        "label": INTERNAL_ENGINE_LABEL,
                        "role": "internal_self_host_engine",
                        "source_commit": source_commit,
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

        engine_commit = _command(["git", "rev-parse", "HEAD"], engine).stdout.strip()
        engine_version = _command(
            [sys.executable, "-c", "import cortex; print(cortex.__version__)"], engine
        ).stdout.strip()

        home = base / "home"
        started = time.perf_counter()
        bootstrap = _command(
            [sys.executable, "-m", "cortex", "--home", str(home), "bootstrap", str(host), "--name", "CortexSelfHost", "--json"],
            engine,
        )
        bootstrap_seconds = time.perf_counter() - started
        bootstrap_payload = json.loads(bootstrap.stdout)

        started = time.perf_counter()
        activation = _command(
            [sys.executable, "-m", "cortex", "--home", str(home), "activate", "--repo", "CortexSelfHost", "--task", "Map Cortex self-hosting architecture", "--json"],
            engine,
        )
        activation_seconds = time.perf_counter() - started
        activation_payload = json.loads(activation.stdout)
        tests_ok = None
        if run_tests:
            tests_ok = _command([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"], engine).returncode == 0
        config = json.loads((host / ".cortex" / "config.json").read_text(encoding="utf-8"))
        return {
            "mode": "nested_clone" if nested_engine else "host_engine",
            "engine_label": INTERNAL_ENGINE_LABEL if nested_engine else "HOST CORTEX ENGINE",
            "engine_role": "internal_self_host_engine" if nested_engine else "host_repository_engine",
            "source_commit": source_commit,
            "engine_commit": engine_commit,
            "engine_commit_current": engine_commit == source_commit,
            "engine_version": engine_version,
            "bootstrap_seconds": round(bootstrap_seconds, 6),
            "activation_seconds": round(activation_seconds, 6),
            "certificate": bootstrap_payload["certificate"]["status"],
            "activation": activation_payload["activation"],
            "indexed_files": bootstrap_payload["index"]["indexed_files_total"],
            "context_evidence": len(activation_payload["context"]["evidence"]),
            "nested_engine_excluded": INTERNAL_ENGINE_DIRECTORY in config["exclude"] if nested_engine else True,
            "clone_engine": str(engine.relative_to(base)),
            "tests_ok": tests_ok,
        }


def run_self_test(source_root: Path | None = None, *, run_tests: bool = True) -> dict[str, Any]:
    source = (source_root or Path(__file__).resolve().parents[1]).resolve()
    result = run_lifecycle(source, nested_engine=True, run_tests=run_tests)
    result["self_hosted"] = True
    result["source"] = str(source)
    return result
