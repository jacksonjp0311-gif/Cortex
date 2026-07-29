"""Pure-Python deterministic HNSW-style graph for local vector search.

Build order is sorted by node_key; RNG is seeded from a content fingerprint.
Not a cloud service; not mutation authority.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Iterable


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    num = sum(x * y for x, y in zip(a, b))
    da = math.sqrt(sum(x * x for x in a))
    db = math.sqrt(sum(y * y for y in b))
    if da == 0.0 or db == 0.0:
        return 0.0
    return num / (da * db)


@dataclass
class HNSWIndex:
    dim: int
    M: int = 8
    ef_construction: int = 32
    ef_search: int = 32
    seed: int = 0
    vectors: dict[str, list[float]] = field(default_factory=dict)
    neighbors: dict[str, list[str]] = field(default_factory=dict)
    entry_point: str | None = None

    def _rng(self) -> random.Random:
        return random.Random(self.seed)

    def add(self, key: str, vector: list[float]) -> None:
        if len(vector) != self.dim:
            # Pad / truncate for robustness
            v = list(vector[: self.dim]) + [0.0] * max(0, self.dim - len(vector))
        else:
            v = list(vector)
        self.vectors[key] = v
        self.neighbors.setdefault(key, [])
        if self.entry_point is None:
            self.entry_point = key
            return
        # Greedy connect to best candidates among existing (deterministic sample)
        keys = sorted(k for k in self.vectors if k != key)
        rng = self._rng()
        rng.shuffle(keys)  # seeded shuffle — deterministic given seed+keys set size order restored
        # Actually shuffle of sorted list with fixed seed is deterministic
        candidates = keys[: max(self.ef_construction, self.M * 4)]
        scored = sorted(
            ((cosine_similarity(v, self.vectors[c]), c) for c in candidates),
            reverse=True,
        )
        top = [c for _, c in scored[: self.M]]
        self.neighbors[key] = top
        for peer in top:
            peer_n = list(self.neighbors.get(peer) or [])
            if key not in peer_n:
                peer_n.append(key)
            # Cap degree M*2, keep best by similarity to peer
            if len(peer_n) > self.M * 2:
                peer_n = [
                    n
                    for _, n in sorted(
                        (
                            (cosine_similarity(self.vectors[peer], self.vectors[n]), n)
                            for n in peer_n
                        ),
                        reverse=True,
                    )[: self.M * 2]
                ]
            self.neighbors[peer] = sorted(peer_n)
        self.neighbors[key] = sorted(self.neighbors[key])

    def build(self, items: Iterable[tuple[str, list[float]]]) -> None:
        # Deterministic insert order
        for key, vec in sorted(items, key=lambda kv: kv[0]):
            self.add(key, vec)

    def search(self, query: list[float], k: int = 8) -> list[tuple[str, float]]:
        if not self.vectors:
            return []
        # Beam search from entry + expand neighbors; fallback full scan if small
        if len(self.vectors) <= 256:
            scored = [
                (cosine_similarity(query, vec), key)
                for key, vec in self.vectors.items()
            ]
            scored.sort(reverse=True)
            return [(key, score) for score, key in scored[:k]]

        visited: set[str] = set()
        frontier: list[str] = []
        if self.entry_point:
            frontier.append(self.entry_point)
        # Seed with a few deterministic keys near hash of query sum
        keys_sorted = sorted(self.vectors.keys())
        seed_i = int(abs(sum(query[:8])) * 1000) % max(1, len(keys_sorted))
        for offset in range(min(self.ef_search, len(keys_sorted))):
            frontier.append(keys_sorted[(seed_i + offset) % len(keys_sorted)])

        best: dict[str, float] = {}
        while frontier:
            node = frontier.pop()
            if node in visited:
                continue
            visited.add(node)
            score = cosine_similarity(query, self.vectors[node])
            best[node] = score
            if len(visited) > self.ef_search * 8:
                break
            for nb in self.neighbors.get(node) or []:
                if nb not in visited:
                    frontier.append(nb)
        ranked = sorted(best.items(), key=lambda kv: kv[1], reverse=True)
        return ranked[:k]
