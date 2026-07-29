"""Foreign-host proof matrix: geometry must hold outside the Cortex cathedral."""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

# Script execution puts benchmarks/ on sys.path[0]; repo root must be first.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from cortex.activation import activate_repository  # noqa: E402
from cortex.bootstrap import bootstrap_repository  # noqa: E402
from cortex.config import ensure_home  # noqa: E402
from cortex.governor import Governor  # noqa: E402
from cortex.store import Store  # noqa: E402


def _python_host(root: Path) -> None:
    (root / "README.md").write_text(
        "# PyLib\n\n## API\n\nPublic helpers for hashing.\n",
        encoding="utf-8",
    )
    (root / "hashutil.py").write_text(
        "def digest(text: str) -> str:\n    return text[::-1]\n",
        encoding="utf-8",
    )
    (root / "tests").mkdir()
    (root / "tests" / "test_hashutil.py").write_text(
        "from hashutil import digest\n\ndef test_digest():\n    assert digest('ab') == 'ba'\n",
        encoding="utf-8",
    )
    (root / "pyproject.toml").write_text(
        "[project]\nname='pylib'\nversion='0.1.0'\n",
        encoding="utf-8",
    )


def _node_host(root: Path) -> None:
    (root / "README.md").write_text(
        "# NodeService\n\n## Routes\n\nHTTP handlers live in server.js.\n",
        encoding="utf-8",
    )
    (root / "package.json").write_text(
        json.dumps({"name": "node-service", "version": "1.0.0", "main": "server.js"}),
        encoding="utf-8",
    )
    (root / "server.js").write_text(
        "function handle(req) { return { ok: true, path: req }; }\nmodule.exports = { handle };\n",
        encoding="utf-8",
    )
    (root / "server.test.js").write_text(
        "const { handle } = require('./server');\nconsole.assert(handle('/').ok);\n",
        encoding="utf-8",
    )


def _docs_host(root: Path) -> None:
    (root / "README.md").write_text(
        "# Handbook\n\n## Onboarding\n\nStart with architecture notes.\n",
        encoding="utf-8",
    )
    (root / "docs").mkdir()
    (root / "docs" / "architecture.md").write_text(
        "# Architecture\n\nServices communicate over authenticated channels.\n",
        encoding="utf-8",
    )
    (root / "docs" / "auth.md").write_text(
        "# Authentication\n\nTokens are short-lived and rotated.\n",
        encoding="utf-8",
    )


def _go_host(root: Path) -> None:
    (root / "README.md").write_text(
        "# GoService\n\n## Handlers\n\nHTTP handlers live in main.go.\n",
        encoding="utf-8",
    )
    (root / "go.mod").write_text("module example.com/gosvc\n\ngo 1.22\n", encoding="utf-8")
    (root / "main.go").write_text(
        "package main\n\nfunc health() string { return \"ok\" }\n\nfunc main() {}\n",
        encoding="utf-8",
    )
    (root / "main_test.go").write_text(
        "package main\n\nimport \"testing\"\n\nfunc TestHealth(t *testing.T) {\n"
        "\tif health() != \"ok\" { t.Fatal(\"bad\") }\n}\n",
        encoding="utf-8",
    )


def _mixed_host(root: Path) -> None:
    """Polyglot contact: Python API + TS client + ops docs."""

    (root / "README.md").write_text(
        "# MixedStack\n\n## Surfaces\n\nAPI, web client, and runbooks.\n",
        encoding="utf-8",
    )
    (root / "api").mkdir()
    (root / "api" / "app.py").write_text(
        "def handle(path: str) -> dict:\n    return {'path': path, 'ok': True}\n",
        encoding="utf-8",
    )
    (root / "web").mkdir()
    (root / "web" / "client.ts").write_text(
        "export function ping(): string { return 'pong'; }\n",
        encoding="utf-8",
    )
    (root / "ops").mkdir()
    (root / "ops" / "runbook.md").write_text(
        "# Runbook\n\nRestart the API before the web tier.\n",
        encoding="utf-8",
    )
    (root / "package.json").write_text(
        '{"name":"mixed-stack","version":"0.1.0"}\n', encoding="utf-8"
    )
    (root / "pyproject.toml").write_text(
        "[project]\nname='mixed-stack'\nversion='0.1.0'\n", encoding="utf-8"
    )


def _run_host(kind: str, builder) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix=f"foreign-{kind}-") as temporary:
        base = Path(temporary)
        host = base / kind
        host.mkdir()
        builder(host)
        home = ensure_home(base / "home")
        store = Store(home / "cortex.db")
        name = f"Foreign{kind.title()}"
        t0 = time.perf_counter()
        boot = bootstrap_repository(home, store, host, name)
        bootstrap_s = time.perf_counter() - t0
        gov = Governor(home, store)
        t0 = time.perf_counter()
        generic = activate_repository(
            home,
            store,
            gov,
            name,
            "Fix unit tests and improve error handling",
            budget=800,
        )
        generic_s = time.perf_counter() - t0
        sub = (
            (generic["context"].get("neural_interlink") or {})
            .get("metrics", {})
            .get("aria_substrate", {})
        )
        evidence = generic["context"].get("evidence") or []
        authority = (generic["context"].get("governor") or {}).get("authority") or {}
        aria_eligible = int(sub.get("eligible_nodes") or 0)
        deferred = sum(
            1 for row in store.files(name) if row["status"] == "substrate_deferred"
        )
        breaks = []
        if boot["certificate"]["status"] != "verified":
            breaks.append("certificate_not_verified")
        if sub.get("mode") not in {None, "dormant"} and aria_eligible > 0:
            breaks.append("aria_leaked_on_generic")
        if authority.get("cortex_may_authorize_mutation") is True:
            breaks.append("mutation_authority")
        if not evidence:
            breaks.append("empty_evidence")
        if "constitutional_supervision" not in generic["context"]:
            breaks.append("missing_constitutional")
        if "aria_materialization" not in generic["context"]:
            breaks.append("missing_materialization_surface")
        store.close()
        return {
            "kind": kind,
            "bootstrap_seconds": round(bootstrap_s, 4),
            "generic_activate_seconds": round(generic_s, 4),
            "certificate": boot["certificate"]["status"],
            "evidence_count": len(evidence),
            "aria_mode": sub.get("mode"),
            "aria_eligible": aria_eligible,
            "deferred_files": deferred,
            "authority_blocks_mutation": authority.get("cortex_may_authorize_mutation")
            is not True,
            "breaks": breaks,
            "pass": len(breaks) == 0,
        }


def run_matrix() -> dict[str, Any]:
    hosts = [
        ("python", _python_host),
        ("node", _node_host),
        ("docs", _docs_host),
        ("go", _go_host),
        ("mixed", _mixed_host),
    ]
    results = [_run_host(kind, builder) for kind, builder in hosts]
    return {
        "schema_version": "cortex-foreign-host-matrix/1.1",
        "hosts": results,
        "passed": sum(1 for item in results if item["pass"]),
        "total": len(results),
        "all_passed": all(item["pass"] for item in results),
        "contact": "expanded",
        "claim_boundary": (
            "Synthetic foreign hosts measure organ behavior outside Cortex self; "
            "they do not prove production multi-repo quality."
        ),
    }


def main() -> None:
    payload = run_matrix()
    out = Path("benchmarks/results/foreign_host_matrix.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
