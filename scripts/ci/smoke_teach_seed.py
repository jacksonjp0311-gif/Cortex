"""CI smoke: teach --seed into isolated home against this repo only."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cortex.config import ensure_home  # noqa: E402
from cortex.teach_seed import seed_into_home  # noqa: E402


def main() -> int:
    home = ensure_home(Path(tempfile.mkdtemp(prefix="ci-teach-")) / "home")
    result = seed_into_home(
        home=home,
        root=ROOT,
        repo_name="CortexCI",
        force_bootstrap=True,
    )
    print(json.dumps(result, indent=2, default=str))
    if not result.get("seeded"):
        return 1
    cons = (result.get("ritual") or {}).get("consolidate") or {}
    if not (cons.get("created") or cons.get("status") in {"created", "duplicate_skip"}):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
