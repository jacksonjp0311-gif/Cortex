"""Small pure-Python linear algebra for graph operators (no numpy required)."""

from __future__ import annotations

import math
from typing import Sequence


def matvec(n: int, rows: list[list[tuple[int, float]]], v: list[float]) -> list[float]:
    out = [0.0] * n
    for i in range(n):
        s = 0.0
        for j, a in rows[i]:
            s += a * v[j]
        out[i] = s
    return out


def identity_minus(n: int, rows: list[list[tuple[int, float]]], alpha: float) -> list[list[tuple[int, float]]]:
    """Build sparse rows for (I - alpha M) given M as sparse rows."""
    diag = [1.0] * n
    out: list[list[tuple[int, float]]] = [[] for _ in range(n)]
    for i in range(n):
        acc: dict[int, float] = {i: 1.0}
        for j, a in rows[i]:
            acc[j] = acc.get(j, 0.0) - alpha * a
        out[i] = sorted(acc.items())
    return out


def power_iteration_laplacian(
    n: int,
    L_rows: list[list[tuple[int, float]]],
    *,
    iters: int = 40,
) -> tuple[float, list[float]]:
    """Approximate largest eigenvalue of L (not λ2). Use for scale only."""
    if n == 0:
        return 0.0, []
    v = [1.0 / math.sqrt(n)] * n
    lam = 0.0
    for _ in range(iters):
        w = matvec(n, L_rows, v)
        norm = math.sqrt(sum(x * x for x in w)) or 1.0
        v = [x / norm for x in w]
        Lw = matvec(n, L_rows, v)
        lam = sum(v[i] * Lw[i] for i in range(n))
    return float(lam), v


def fiedler_inverse_iteration(
    n: int,
    L_rows: list[list[tuple[int, float]]],
    degrees: list[float],
    *,
    iters: int = 50,
) -> tuple[float, list[float]]:
    """Rough λ2 via projection off constants + power on shifted system.

    For small graphs we use Rayleigh on residual after mean removal.
    """
    if n <= 1:
        return 0.0, [1.0] * n
    # Start orthogonal to constants
    v = [1.0 if i % 2 == 0 else -1.0 for i in range(n)]
    mean = sum(v) / n
    v = [x - mean for x in v]
    norm = math.sqrt(sum(x * x for x in v)) or 1.0
    v = [x / norm for x in v]
    lam = 0.0
    for _ in range(iters):
        w = matvec(n, L_rows, v)
        mean_w = sum(w) / n
        w = [x - mean_w for x in w]
        norm = math.sqrt(sum(x * x for x in w)) or 1.0
        v = [x / norm for x in w]
        Lw = matvec(n, L_rows, v)
        mean_l = sum(Lw) / n
        Lw = [x - mean_l for x in Lw]
        lam = sum(v[i] * Lw[i] for i in range(n))
    return max(0.0, float(lam)), v


def heat_apply(
    n: int,
    L_rows: list[list[tuple[int, float]]],
    s: list[float],
    t: float,
    *,
    steps: int = 12,
) -> list[float]:
    """Approximate e^{-tL} s via Euler: (I - (t/steps) L)^steps s."""
    if n == 0:
        return []
    dt = float(t) / max(1, steps)
    v = list(s)
    for _ in range(max(1, steps)):
        Lv = matvec(n, L_rows, v)
        v = [v[i] - dt * Lv[i] for i in range(n)]
        # numerical floor
        for i in range(n):
            if v[i] < 0:
                v[i] = 0.0
    return v


def personalized_pagerank(
    n: int,
    adj_rows: list[list[tuple[int, float]]],
    seed: Sequence[int],
    *,
    alpha: float = 0.85,
    iters: int = 30,
) -> list[float]:
    """PPR on row-stochastic-ish adjacency (weighted out-normalized)."""
    if n == 0:
        return []
    # Build column-stochastic transition P: j -> i
    out_deg = [sum(a for _, a in adj_rows[i]) for i in range(n)]
    # adj_rows is out-edges from i; for PPR we need in-edges or iterate from j
    p = [0.0] * n
    if not seed:
        p = [1.0 / n] * n
    else:
        for i in seed:
            if 0 <= i < n:
                p[i] += 1.0 / len(seed)
    teleport = list(p)
    for _ in range(iters):
        new = [(1.0 - alpha) * teleport[i] for i in range(n)]
        for j in range(n):
            if out_deg[j] <= 0:
                # dangling: distribute
                share = alpha * p[j] / n
                for i in range(n):
                    new[i] += share
                continue
            for i, w in adj_rows[j]:
                new[i] += alpha * p[j] * (w / out_deg[j])
        p = new
    return p
