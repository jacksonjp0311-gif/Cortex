"""Portable binary-intel pack format (cortex.binary-intel-pack/1.0).

Packs are content-addressed intelligence modules:
  manifest + markdown cards + optional binary domain field.

Binary is domain geometry / routing — never host authority, never auto-execute.
"""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Any

PACK_SCHEMA = "cortex.binary-intel-pack/1.0"
BINARY_MAGIC = b"CTXBF1\x00\x00"  # 8-byte magic
BINARY_VERSION = 1
BINARY_FORMAT_NAME = "CORTEXBF1"
GLYPH = "▣"  # pack / domain medium (aligned with packet profile glyph family)


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest(pack_dir: Path) -> dict[str, Any]:
    path = pack_dir / "manifest.json"
    if not path.is_file():
        raise FileNotFoundError(f"Pack manifest missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    validate_manifest(data, pack_dir=pack_dir)
    return data


def validate_manifest(data: dict[str, Any], *, pack_dir: Path | None = None) -> None:
    if data.get("schema") != PACK_SCHEMA:
        raise ValueError(
            f"Unsupported pack schema: {data.get('schema')} (want {PACK_SCHEMA})"
        )
    for key in ("id", "version", "name", "domains", "cards"):
        if key not in data:
            raise ValueError(f"Pack manifest missing required field: {key}")
    if not isinstance(data["domains"], list) or not data["domains"]:
        raise ValueError("Pack domains must be a non-empty list")
    if not isinstance(data["cards"], list) or not data["cards"]:
        raise ValueError("Pack cards must be a non-empty list")
    if pack_dir is not None:
        for rel in data["cards"]:
            card = pack_dir / str(rel)
            if not card.is_file():
                raise FileNotFoundError(f"Pack card missing: {rel}")
        binary = data.get("binary") or {}
        if binary.get("path"):
            bpath = pack_dir / str(binary["path"])
            if not bpath.is_file() and not binary.get("optional", True):
                raise FileNotFoundError(f"Required binary missing: {binary['path']}")


def domain_fingerprint(domain: str, keywords: list[str] | None = None) -> bytes:
    """Stable 32-byte fingerprint for a domain (portable, content-addressed)."""

    material = domain.casefold().strip() + "\n" + "\n".join(
        sorted(k.casefold().strip() for k in (keywords or [domain]))
    )
    return hashlib.sha256(material.encode("utf-8")).digest()


def build_binary_field(
    domains: list[str],
    *,
    domain_keywords: dict[str, list[str]] | None = None,
    card_texts: dict[str, str] | None = None,
) -> bytes:
    """Build a compact CORTEXBF1 domain field from domains + optional card text.

    Not a transformer. Sparse domain geometry for zero-in routing.
    """

    domain_keywords = domain_keywords or {}
    card_texts = card_texts or {}
    body = bytearray()
    body.extend(BINARY_MAGIC)
    body.extend(struct.pack("<H", BINARY_VERSION))
    body.extend(struct.pack("<H", len(domains)))
    for domain in domains:
        d = domain.casefold().strip()
        name_b = d.encode("utf-8")
        if len(name_b) > 64:
            raise ValueError(f"Domain name too long: {domain}")
        kws = list(domain_keywords.get(domain) or domain_keywords.get(d) or [d])
        # Fold card tokens mentioning domain into keywords
        for text in card_texts.values():
            low = text.casefold()
            if d in low:
                for token in low.replace("\n", " ").split():
                    if len(token) >= 4 and token not in kws and len(kws) < 48:
                        kws.append(token)
        fp = domain_fingerprint(d, kws)
        # Prototype: hash of sorted keywords into 32 bytes (association seed)
        proto = hashlib.blake2b(
            ("|".join(sorted(kws))).encode("utf-8"), digest_size=32
        ).digest()
        body.extend(struct.pack("<B", len(name_b)))
        body.extend(name_b)
        body.extend(fp)
        body.extend(proto)
    return bytes(body)


def parse_binary_field(data: bytes) -> dict[str, Any]:
    if len(data) < 12 or data[:8] != BINARY_MAGIC:
        raise ValueError(f"Not a {BINARY_FORMAT_NAME} binary field")
    version = struct.unpack_from("<H", data, 8)[0]
    count = struct.unpack_from("<H", data, 10)[0]
    if version != BINARY_VERSION:
        raise ValueError(f"Unsupported {BINARY_FORMAT_NAME} version: {version}")
    offset = 12
    domains: list[dict[str, Any]] = []
    for _ in range(count):
        if offset >= len(data):
            raise ValueError("Truncated CORTEXBF1 field")
        nlen = data[offset]
        offset += 1
        name = data[offset : offset + nlen].decode("utf-8")
        offset += nlen
        fp = data[offset : offset + 32]
        offset += 32
        proto = data[offset : offset + 32]
        offset += 32
        domains.append(
            {
                "domain": name,
                "fingerprint_hex": fp.hex(),
                "prototype_hex": proto.hex(),
            }
        )
    return {
        "format": BINARY_FORMAT_NAME,
        "version": version,
        "domains": domains,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def score_task_against_domains(
    task: str,
    domains: list[str],
    *,
    binary: dict[str, Any] | None = None,
    card_boosts: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Zero-in: score which pack domains the task invokes."""

    text = " ".join(task.casefold().split())
    tokens = set(text.split())
    card_boosts = card_boosts or {}
    binary_domains = {
        d["domain"]: d for d in (binary or {}).get("domains") or [] if d.get("domain")
    }
    scored: list[dict[str, Any]] = []
    for domain in domains:
        d = domain.casefold().strip()
        score = 0.0
        if d in text:
            score += 1.0
        if d in tokens:
            score += 0.5
        # soft stems
        for tok in tokens:
            if len(tok) >= 4 and (tok in d or d in tok):
                score += 0.25
        score += float(card_boosts.get(d) or card_boosts.get(domain) or 0.0)
        if d in binary_domains:
            score += 0.15  # registered binary domain exists
        # common aliases
        aliases = {
            "math": ("math", "mathematics", "algebra", "calculus", "equation"),
            "geometry": ("geometry", "triangle", "circle", "polygon", "spatial"),
            "dialogue": ("conversation", "dialogue", "chat", "speak", "language", "teach"),
            "memory": ("memory", "remember", "recall", "stream", "episodic"),
            "code": ("code", "python", "function", "bug", "test", "implement"),
            "governance": ("govern", "authority", "policy", "immune", "safety"),
            "understanding": ("understand", "comprehend", "meaning", "semantic"),
            "knowledge": ("knowledge", "know", "fact", "learn", "domain", "distill"),
            "interconnect": ("interconnect", "mesh", "connect", "lattice", "pulse", "resonate"),
            "evolution": ("evolve", "evolution", "harness", "ranker", "plasticity", "signal"),
            "general": ("general", "help", "task"),
        }
        for alias in aliases.get(d, ()):
            if alias in text:
                score += 0.35
        scored.append(
            {
                "domain": d,
                "score": round(score, 4),
                "binary": d in binary_domains,
            }
        )
    scored.sort(key=lambda item: (-item["score"], item["domain"]))
    return scored


def expand_threshold(top_score: float) -> bool:
    """Whether domain mass justifies expanding pack cards into the packet."""

    return top_score >= 0.75
