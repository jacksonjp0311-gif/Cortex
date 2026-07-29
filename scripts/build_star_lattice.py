#!/usr/bin/env python3
"""Build first-party Cortex star-lattice SVG from `gh` stargazer timestamps.

No third-party chart hosts. Regenerates assets/star-lattice.svg.

Usage:
  python scripts/build_star_lattice.py
  python scripts/build_star_lattice.py --repo jacksonjp0311-gif/Cortex
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def _gh_json(args: list[str]) -> object:
    cmd = ["gh", "api", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "gh api failed")
    return json.loads(proc.stdout)


def fetch_star_times(repo: str) -> list[datetime]:
    # starred_at requires custom Accept header (star+json)
    cmd = [
        "gh",
        "api",
        f"repos/{repo}/stargazers",
        "-H",
        "Accept: application/vnd.github.star+json",
        "--paginate",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "failed to list stargazers")
    # paginate concatenates JSON arrays
    raw = proc.stdout.strip()
    if not raw:
        return []
    # gh --paginate may emit multiple arrays concatenated
    items: list[dict] = []
    decoder = json.JSONDecoder()
    idx = 0
    while idx < len(raw):
        while idx < len(raw) and raw[idx].isspace():
            idx += 1
        if idx >= len(raw):
            break
        obj, end = decoder.raw_decode(raw, idx)
        if isinstance(obj, list):
            items.extend(obj)
        idx = end
    times: list[datetime] = []
    for row in items:
        ts = row.get("starred_at")
        if not ts:
            continue
        times.append(datetime.fromisoformat(ts.replace("Z", "+00:00")))
    times.sort()
    return times


def cumulative_series(
    times: list[datetime], created: datetime
) -> list[tuple[datetime, int]]:
    points: list[tuple[datetime, int]] = [(created, 0)]
    for i, t in enumerate(times, start=1):
        points.append((t, i))
    if not times:
        points.append((datetime.now(timezone.utc), 0))
    else:
        # hold to now
        points.append((datetime.now(timezone.utc), len(times)))
    return points


def _x(t: datetime, t0: datetime, t1: datetime, left: float, width: float) -> float:
    span = max(1.0, (t1 - t0).total_seconds())
    return left + width * ((t - t0).total_seconds() / span)


def _y(v: float, vmin: float, vmax: float, top: float, height: float) -> float:
    if vmax <= vmin:
        return top + height
    return top + height * (1.0 - (v - vmin) / (vmax - vmin))


def _hud_bracket(x: float, y: float, w: float, h: float, size: float = 14) -> str:
    """Four corner HUD brackets around a region."""
    s = size
    stroke = 'stroke="#22d3ee" stroke-width="1.4" fill="none" stroke-opacity="0.85"'
    return (
        f'<path d="M{x} {y + s} V{y} H{x + s}" {stroke}/>'
        f'<path d="M{x + w - s} {y} H{x + w} V{y + s}" {stroke}/>'
        f'<path d="M{x + w} {y + h - s} V{y + h} H{x + w - s}" {stroke}/>'
        f'<path d="M{x + s} {y + h} H{x} V{y + h - s}" {stroke}/>'
    )


def render_svg(
    points: list[tuple[datetime, int]],
    *,
    repo: str,
    stars: int,
) -> str:
    W, H = 980, 400
    pad_l, pad_r, pad_t, pad_b = 72, 40, 72, 58
    plot_w = W - pad_l - pad_r
    plot_h = H - pad_t - pad_b
    t0, t1 = points[0][0], points[-1][0]
    vmax = max(1, max(p[1] for p in points))
    mono = "ui-monospace, 'Cascadia Code', Consolas, monospace"
    sans = "ui-sans-serif, system-ui, sans-serif"

    coords = [
        (
            _x(t, t0, t1, pad_l, plot_w),
            _y(float(v), 0.0, float(vmax), pad_t, plot_h),
        )
        for t, v in points
    ]
    line = " ".join(f"{x:.2f},{y:.2f}" for x, y in coords)
    area = (
        f"M {coords[0][0]:.2f},{pad_t + plot_h:.2f} "
        + " ".join(f"L {x:.2f},{y:.2f}" for x, y in coords)
        + f" L {coords[-1][0]:.2f},{pad_t + plot_h:.2f} Z"
    )

    # horizontal + vertical neural grid
    grids: list[str] = []
    for i in range(5):
        yy = pad_t + plot_h * i / 4
        val = vmax * (1 - i / 4)
        grids.append(
            f'<line x1="{pad_l}" y1="{yy:.1f}" x2="{pad_l + plot_w}" y2="{yy:.1f}" '
            f'stroke="url(#gridGrad)" stroke-width="1" stroke-dasharray="2 7"/>'
            f'<text x="{pad_l - 14}" y="{yy + 4:.1f}" text-anchor="end" '
            f'fill="#67e8f9" font-family="{mono}" font-size="11" opacity="0.8">'
            f"{int(round(val)):02d}</text>"
        )
    for i in range(1, 8):
        xx = pad_l + plot_w * i / 8
        grids.append(
            f'<line x1="{xx:.1f}" y1="{pad_t}" x2="{xx:.1f}" y2="{pad_t + plot_h}" '
            f'stroke="#334155" stroke-opacity="0.22" stroke-width="0.8"/>'
        )

    # lattice edges: connect consecutive real nodes + skip links (neural mesh)
    real = [
        (xy, p)
        for i, (xy, p) in enumerate(zip(coords, points))
        if not (p[1] == 0 and i == 0)
        and not (i == len(coords) - 1 and len(points) > 1 and p[1] == points[-2][1])
    ]
    mesh: list[str] = []
    for i in range(len(real) - 1):
        (x1, y1), _ = real[i]
        (x2, y2), _ = real[i + 1]
        mesh.append(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="#a855f7" stroke-opacity="0.35" stroke-width="1"/>'
        )
        # vertical drop to baseline (axon)
        mesh.append(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x1:.2f}" y2="{pad_t + plot_h:.2f}" '
            f'stroke="#22d3ee" stroke-opacity="0.08" stroke-width="1" stroke-dasharray="2 4"/>'
        )
    # skip connections every 2nd node
    for i in range(len(real) - 2):
        (x1, y1), _ = real[i]
        (x2, y2), _ = real[i + 2]
        mesh.append(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="#67e8f9" stroke-opacity="0.12" stroke-width="0.8"/>'
        )

    nodes: list[str] = []
    for i, ((x, y), (t, v)) in enumerate(zip(coords, points)):
        if v == 0 and i == 0:
            continue
        if i == len(coords) - 1 and len(points) > 1 and v == points[-2][1]:
            nodes.append(
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4" fill="#22d3ee" opacity="0.3">'
                f'<animate attributeName="opacity" values="0.15;0.45;0.15" dur="2.4s" '
                f'repeatCount="indefinite"/></circle>'
            )
            continue
        # diamond node (◈-like)
        d = 5.5
        diamond = (
            f"M{x:.2f},{y - d:.2f} L{x + d:.2f},{y:.2f} "
            f"L{x:.2f},{y + d:.2f} L{x - d:.2f},{y:.2f} Z"
        )
        nodes.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="14" fill="none" stroke="#a855f7" '
            f'stroke-width="0.7" opacity="0.35"/>'
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="9" fill="none" stroke="#22d3ee" '
            f'stroke-width="0.9" opacity="0.55" stroke-dasharray="3 3">'
            f'<animateTransform attributeName="transform" type="rotate" from="0 {x:.2f} {y:.2f}" '
            f'to="360 {x:.2f} {y:.2f}" dur="14s" repeatCount="indefinite"/></circle>'
            f'<path d="{diamond}" fill="#0ea5e9" stroke="#e0f2fe" stroke-width="1.2" '
            f'filter="url(#glow)">'
            f"<title>{t.date().isoformat()} · ★{v}</title></path>"
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2" fill="#f8fafc"/>'
        )

    xlabels: list[str] = []
    for frac, label_t in ((0.0, t0), (0.5, t0 + (t1 - t0) / 2), (1.0, t1)):
        xx = pad_l + plot_w * frac
        xlabels.append(
            f'<text x="{xx:.1f}" y="{H - 22}" text-anchor="middle" fill="#94a3b8" '
            f'font-family="{mono}" font-size="11">{label_t.date().isoformat()}</text>'
            f'<line x1="{xx:.1f}" y1="{pad_t + plot_h}" x2="{xx:.1f}" '
            f'y2="{pad_t + plot_h + 6}" stroke="#67e8f9" stroke-opacity="0.5"/>'
        )

    # faint hex lattice in background of plot
    hexes: list[str] = []
    hx, hy = 28.0, 24.0
    row = 0
    yy = pad_t + 8
    while yy < pad_t + plot_h - 8:
        xx = pad_l + (0 if row % 2 == 0 else hx * 0.5)
        while xx < pad_l + plot_w - 8:
            hexes.append(
                f'<circle cx="{xx:.1f}" cy="{yy:.1f}" r="1.1" fill="#22d3ee" opacity="0.07"/>'
            )
            xx += hx
        yy += hy
        row += 1

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    brackets = _hud_bracket(pad_l - 6, pad_t - 6, plot_w + 12, plot_h + 12, 12)

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"
     role="img" aria-label="Cortex star lattice — cumulative stargazers">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#01030a"/>
      <stop offset="40%" stop-color="#0a0f1e"/>
      <stop offset="100%" stop-color="#1a1035"/>
    </linearGradient>
    <linearGradient id="neon" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#22d3ee"/>
      <stop offset="45%" stop-color="#38bdf8"/>
      <stop offset="100%" stop-color="#c084fc"/>
    </linearGradient>
    <linearGradient id="neonSoft" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#22d3ee" stop-opacity="0.25"/>
      <stop offset="100%" stop-color="#a855f7" stop-opacity="0.35"/>
    </linearGradient>
    <linearGradient id="fillGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#0ea5e9" stop-opacity="0.42"/>
      <stop offset="55%" stop-color="#7c3aed" stop-opacity="0.12"/>
      <stop offset="100%" stop-color="#020617" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="gridGrad" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#334155" stop-opacity="0.1"/>
      <stop offset="50%" stop-color="#67e8f9" stop-opacity="0.28"/>
      <stop offset="100%" stop-color="#334155" stop-opacity="0.1"/>
    </linearGradient>
    <linearGradient id="headerBar" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#22d3ee" stop-opacity="0"/>
      <stop offset="20%" stop-color="#22d3ee" stop-opacity="0.55"/>
      <stop offset="80%" stop-color="#a855f7" stop-opacity="0.55"/>
      <stop offset="100%" stop-color="#a855f7" stop-opacity="0"/>
    </linearGradient>
    <filter id="glow" x="-80%" y="-80%" width="260%" height="260%">
      <feGaussianBlur stdDeviation="2.8" result="b"/>
      <feMerge>
        <feMergeNode in="b"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
    <filter id="glowStrong" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="5" result="b"/>
      <feMerge>
        <feMergeNode in="b"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
    <pattern id="scan" width="6" height="6" patternUnits="userSpaceOnUse">
      <path d="M0 6 L6 0" stroke="#22d3ee" stroke-opacity="0.035" stroke-width="1"/>
    </pattern>
    <pattern id="noise" width="3" height="3" patternUnits="userSpaceOnUse">
      <rect width="1" height="1" fill="#67e8f9" opacity="0.03"/>
    </pattern>
    <clipPath id="plotClip">
      <rect x="{pad_l}" y="{pad_t}" width="{plot_w}" height="{plot_h}"/>
    </clipPath>
  </defs>

  <!-- chassis -->
  <rect width="{W}" height="{H}" rx="18" fill="url(#bg)"/>
  <rect width="{W}" height="{H}" rx="18" fill="url(#scan)"/>
  <rect width="{W}" height="{H}" rx="18" fill="url(#noise)"/>
  <rect x="1.5" y="1.5" width="{W - 3}" height="{H - 3}" rx="17"
        fill="none" stroke="url(#neon)" stroke-opacity="0.65" stroke-width="1.6"/>
  <rect x="6" y="6" width="{W - 12}" height="{H - 12}" rx="14"
        fill="none" stroke="#334155" stroke-opacity="0.45" stroke-width="0.8"/>

  <!-- top status strip -->
  <line x1="48" y1="52" x2="{W - 48}" y2="52" stroke="url(#headerBar)" stroke-width="1"/>
  <circle cx="28" cy="28" r="5" fill="#22d3ee" filter="url(#glow)">
    <animate attributeName="opacity" values="0.5;1;0.5" dur="1.8s" repeatCount="indefinite"/>
  </circle>
  <text x="42" y="24" fill="#e2e8f0" font-family="{sans}" font-size="15" font-weight="700"
        letter-spacing="0.12em">CORTEX // STAR LATTICE</text>
  <text x="42" y="42" fill="#64748b" font-family="{mono}" font-size="10">
    SIGNAL · CUMULATIVE STARS · FIRST-PARTY CLI · gh api stargazers
  </text>
  <text x="{W - 28}" y="24" text-anchor="end" fill="#c084fc" font-family="{mono}" font-size="12">
    ◈ {repo}
  </text>
  <text x="{W - 28}" y="42" text-anchor="end" fill="#475569" font-family="{mono}" font-size="10">
    SYNC {now}
  </text>

  <!-- plot well -->
  <rect x="{pad_l}" y="{pad_t}" width="{plot_w}" height="{plot_h}"
        fill="#01040c" fill-opacity="0.75" stroke="#1e293b" stroke-opacity="0.8"/>
  {brackets}
  <g clip-path="url(#plotClip)">{"".join(hexes)}</g>
  {"".join(grids)}

  <!-- signal -->
  <g clip-path="url(#plotClip)">
    <path d="{area}" fill="url(#fillGrad)"/>
    <polyline points="{line}" fill="none" stroke="url(#neonSoft)" stroke-width="8"
              stroke-linejoin="round" stroke-linecap="round" opacity="0.55" filter="url(#glowStrong)"/>
    <polyline points="{line}" fill="none" stroke="url(#neon)" stroke-width="2.5"
              stroke-linejoin="round" stroke-linecap="round" filter="url(#glow)"/>
    {"".join(mesh)}
    {"".join(nodes)}
  </g>

  {"".join(xlabels)}

  <!-- footer telemetry -->
  <rect x="24" y="{H - 48}" width="200" height="30" rx="6"
        fill="#0f172a" fill-opacity="0.9" stroke="#22d3ee" stroke-opacity="0.35"/>
  <text x="40" y="{H - 28}" fill="#67e8f9" font-family="{mono}" font-size="11">NODES {len(real):02d}</text>
  <text x="120" y="{H - 28}" fill="#94a3b8" font-family="{mono}" font-size="11">◈ LATTICE</text>

  <rect x="{W - 176}" y="{H - 48}" width="152" height="30" rx="6"
        fill="#0f172a" fill-opacity="0.95" stroke="#a855f7" stroke-opacity="0.7"/>
  <text x="{W - 100}" y="{H - 28}" text-anchor="middle" fill="#f8fafc"
        font-family="{mono}" font-size="14" font-weight="700">★ {stars:02d} STARS</text>
</svg>
'''


def _fingerprint(stars: int, times: list[datetime]) -> str:
    """Stable id of metrics (not wall clock) for change detection."""
    payload = {
        "stars": stars,
        "times": [t.isoformat() for t in times],
    }
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def write_metrics_json(
    path: Path,
    *,
    repo: str,
    stars: int,
    created: datetime,
    times: list[datetime],
) -> None:
    """First-party metrics for the live lattice page (no browser GitHub API).

    Browser clients cannot call stargazers with star+json (401 without a token).
    CI/CLI pulls with `gh` and publishes this JSON next to the HTML.
    """
    payload = {
        "schema": "cortex.star_metrics.v1",
        "repo": repo,
        "stars": stars,
        "created_at": created.isoformat(),
        "times": [t.isoformat() for t in times],
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": "gh api repos/.../stargazers Accept: application/vnd.github.star+json",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _patch_readme_cache_bust(readme: Path, stars: int) -> bool:
    """Point README img at assets/star-lattice.svg?v=<stars> so Camo re-fetches."""
    if not readme.is_file():
        return False
    text = readme.read_text(encoding="utf-8")
    new, n = re.subn(
        r'(src="assets/star-lattice\.svg)(?:\?v=\d+)?"',
        rf'\1?v={stars}"',
        text,
        count=1,
    )
    if n and new != text:
        readme.write_text(new, encoding="utf-8", newline="\n")
        return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description="Build Cortex star-lattice SVG via gh")
    ap.add_argument("--repo", default="jacksonjp0311-gif/Cortex")
    ap.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output SVG path (default: assets/star-lattice.svg)",
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="Rewrite SVG even if star metrics fingerprint unchanged",
    )
    ap.add_argument(
        "--patch-readme",
        action="store_true",
        help="Update README img cache-buster ?v=<star count>",
    )
    args = ap.parse_args()
    root = Path(__file__).resolve().parents[1]
    out = args.out or (root / "assets" / "star-lattice.svg")
    fp_path = out.with_suffix(".fingerprint")

    meta = _gh_json([f"repos/{args.repo}"])
    assert isinstance(meta, dict)
    stars = int(meta.get("stargazers_count") or 0)
    created = datetime.fromisoformat(
        str(meta.get("created_at", "2026-07-11T00:00:00Z")).replace("Z", "+00:00")
    )
    times = fetch_star_times(args.repo)
    metrics_path = root / "assets" / "star-metrics.json"
    star_n = max(stars, len(times))
    # Always publish metrics JSON so the live HTML can reload without api.github.com.
    write_metrics_json(
        metrics_path,
        repo=args.repo,
        stars=star_n,
        created=created,
        times=times,
    )

    fp = _fingerprint(stars, times)
    if not args.force and fp_path.is_file() and fp_path.read_text(encoding="utf-8") == fp:
        if out.is_file():
            print(
                f"unchanged {out} ({stars} stars, {len(times)} timestamps); "
                f"refreshed {metrics_path.name}"
            )
            if args.patch_readme:
                _patch_readme_cache_bust(root / "README.md", stars)
            return 0

    series = cumulative_series(times, created)
    # if gh returned fewer timestamps than star count, lift final value
    if series and series[-1][1] < stars:
        series[-1] = (series[-1][0], stars)

    star_n = max(stars, series[-1][1])
    svg = render_svg(series, repo=args.repo, stars=star_n)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg, encoding="utf-8", newline="\n")
    fp_path.write_text(fp, encoding="utf-8", newline="\n")
    patched = False
    if args.patch_readme:
        patched = _patch_readme_cache_bust(root / "README.md", star_n)
    print(
        f"wrote {out} + {metrics_path.name} ({stars} stars, {len(times)} timestamps)"
        + (" · readme cache-bust" if patched else "")
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
