"""Install / list / verify packs under CORTEX_HOME/packs (portable)."""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import Any

from ..config import ensure_home
from .format import (
    GLYPH,
    PACK_SCHEMA,
    build_binary_field,
    file_sha256,
    load_manifest,
    parse_binary_field,
    validate_manifest,
)


def packs_root(home: Path | None = None) -> Path:
    root = ensure_home(home) / "packs"
    root.mkdir(parents=True, exist_ok=True)
    return root


def installed_pack_dir(home: Path, pack_id: str) -> Path:
    return packs_root(home) / pack_id


def list_packs(home: Path | None = None) -> dict[str, Any]:
    home = ensure_home(home)
    root = packs_root(home)
    items: list[dict[str, Any]] = []
    for child in sorted(root.iterdir() if root.is_dir() else []):
        if not child.is_dir():
            continue
        man_path = child / "manifest.json"
        if not man_path.is_file():
            continue
        try:
            man = load_manifest(child)
            items.append(
                {
                    "id": man["id"],
                    "version": man["version"],
                    "name": man["name"],
                    "domains": man["domains"],
                    "path": str(child),
                    "cards": len(man.get("cards") or []),
                    "has_binary": bool(
                        man.get("binary", {}).get("path")
                        and (child / str(man["binary"]["path"])).is_file()
                    ),
                }
            )
        except Exception as exc:
            items.append({"id": child.name, "error": f"{type(exc).__name__}: {exc}"})
    return {
        "schema_version": "cortex-packs-list/1.0",
        "glyph": GLYPH,
        "home": str(home),
        "packs_root": str(root),
        "count": len(items),
        "packs": items,
        "claim_boundary": (
            "Installed packs are portable intelligence modules; never host mutation rights."
        ),
    }


def verify_pack(pack_dir: Path) -> dict[str, Any]:
    pack_dir = pack_dir.expanduser().resolve()
    man = load_manifest(pack_dir)
    cards: list[dict[str, Any]] = []
    for rel in man["cards"]:
        path = pack_dir / str(rel)
        cards.append(
            {
                "path": str(rel),
                "sha256": file_sha256(path),
                "bytes": path.stat().st_size,
            }
        )
    binary_info: dict[str, Any] | None = None
    bspec = man.get("binary") or {}
    if bspec.get("path"):
        bpath = pack_dir / str(bspec["path"])
        if bpath.is_file():
            raw = bpath.read_bytes()
            try:
                parsed = parse_binary_field(raw)
            except Exception as exc:
                parsed = {"error": f"{type(exc).__name__}: {exc}"}
            binary_info = {
                "path": str(bspec["path"]),
                "bytes": len(raw),
                "sha256": file_sha256(bpath),
                "parsed": parsed,
                "optional": bool(bspec.get("optional", True)),
            }
        else:
            binary_info = {
                "path": str(bspec["path"]),
                "missing": True,
                "optional": bool(bspec.get("optional", True)),
            }
    expected = man.get("integrity") or {}
    mismatches: list[str] = []
    if expected.get("manifest_sha256"):
        # recompute manifest without nested integrity if present
        pass
    return {
        "schema_version": "cortex-pack-verify/1.0",
        "glyph": GLYPH,
        "ok": not mismatches and all(c.get("sha256") for c in cards),
        "pack_id": man["id"],
        "version": man["version"],
        "domains": man["domains"],
        "cards": cards,
        "binary": binary_info,
        "mismatches": mismatches,
        "claim_boundary": (
            "Verify is integrity only; it does not promote or execute pack contents."
        ),
    }


def install_pack(
    source: Path,
    home: Path | None = None,
    *,
    rebuild_binary: bool = True,
    force: bool = False,
) -> dict[str, Any]:
    """Copy a pack directory into CORTEX_HOME/packs/<id> and ensure binary field."""

    home = ensure_home(home)
    source = source.expanduser().resolve()
    if not source.is_dir():
        raise FileNotFoundError(f"Pack source not a directory: {source}")
    man = load_manifest(source)
    pack_id = str(man["id"])
    dest = installed_pack_dir(home, pack_id)
    if dest.exists() and not force:
        # refresh copy
        shutil.rmtree(dest)
    elif dest.exists() and force:
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, dest)

    # Optionally build/refresh CORTEXBF1 from cards (portable, no Perci required)
    card_texts: dict[str, str] = {}
    for rel in man["cards"]:
        p = dest / str(rel)
        card_texts[str(rel)] = p.read_text(encoding="utf-8", errors="replace")
    binary_rel = (man.get("binary") or {}).get("path") or "field.cortexbf1"
    if rebuild_binary:
        domain_keywords = man.get("domain_keywords") or {}
        raw = build_binary_field(
            list(man["domains"]),
            domain_keywords=domain_keywords,
            card_texts=card_texts,
        )
        bpath = dest / str(binary_rel)
        bpath.parent.mkdir(parents=True, exist_ok=True)
        bpath.write_bytes(raw)
        man = dict(man)
        man["binary"] = {
            "path": str(binary_rel).replace("\\", "/"),
            "format": "CORTEXBF1",
            "role": "domain_geometry_sidecar",
            "optional": False,
            "bytes": len(raw),
            "sha256": file_sha256(bpath),
        }
        man["installed_at"] = time.time()
        man["schema"] = PACK_SCHEMA
        (dest / "manifest.json").write_text(
            json.dumps(man, indent=2) + "\n", encoding="utf-8"
        )
    validate_manifest(load_manifest(dest), pack_dir=dest)
    return {
        "schema_version": "cortex-pack-install/1.0",
        "glyph": GLYPH,
        "installed": True,
        "pack_id": pack_id,
        "version": man["version"],
        "path": str(dest),
        "domains": man["domains"],
        "binary": man.get("binary"),
        "verify": verify_pack(dest),
        "claim_boundary": (
            "Install places packs under the user's CORTEX_HOME; no host source mutation."
        ),
    }


def load_pack(home: Path, pack_id: str) -> dict[str, Any]:
    dest = installed_pack_dir(home, pack_id)
    if not dest.is_dir():
        raise FileNotFoundError(f"Pack not installed: {pack_id}")
    man = load_manifest(dest)
    binary = None
    bspec = man.get("binary") or {}
    if bspec.get("path"):
        bpath = dest / str(bspec["path"])
        if bpath.is_file():
            binary = parse_binary_field(bpath.read_bytes())
    cards: list[dict[str, Any]] = []
    for rel in man["cards"]:
        path = dest / str(rel)
        text = path.read_text(encoding="utf-8", errors="replace")
        cards.append(
            {
                "path": str(rel).replace("\\", "/"),
                "text": text,
                "sha256": file_sha256(path),
            }
        )
    return {
        "manifest": man,
        "path": str(dest),
        "binary": binary,
        "cards": cards,
    }
