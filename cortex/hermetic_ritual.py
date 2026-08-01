"""Hermetic attach ritual — solar-lunar entrainment + attach display.

Psychological arc: isolation rupture → numinous interlock peak → pyramidion seal
→ clean re-integration (Returned to ROOT).

Symbols pulse with soft 1.2s brightness cycles (Grok-like living glow) when
stdout is a TTY and CORTEX_ATTACH_RITUAL is not disabled.

Never claims consciousness. Host remains sovereign. Recommend-only.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any, Callable, TextIO

# Cadence (env CORTEX_ATTACH_FAST=1 shortens for re-runs / scripts)
def _cadence_scale() -> float:
    if os.environ.get("CORTEX_ATTACH_FAST", "").strip() in {"1", "true", "yes"}:
        return 0.35
    return 1.0


PULSE_S = 1.2
STEP_PAUSE_S = 0.42  # breath between solar-lunar beats
LINE_PAUSE_S = 0.18
PEAK_HOLD_S = 1.65  # liminal silence at center lattice
SEAL_HOLD_S = 1.1
RETURN_HOLD_S = 0.55

# ANSI
CSI = "\033["
RESET = f"{CSI}0m"
DIM = f"{CSI}2m"
BRIGHT = f"{CSI}1m"
GOLD = f"{CSI}38;5;178m"
SILVER = f"{CSI}38;5;252m"
CYAN = f"{CSI}38;5;80m"
SOFT = f"{CSI}38;5;146m"
MUTED = f"{CSI}38;5;240m"

SYM_CORTEX = "◈"
SYM_SOL = "☉"
SYM_LUNA = "☽"
SYM_ORG = "⊛"
SYM_CYCLE = "⟳"
SYM_PEAK = "▲"

CLAIM = (
    "Hermetic attach is a ritual interface for interlock and re-integration. "
    "It does not claim consciousness, numinous authority over the host, or "
    "mutation rights. Host remains sovereign."
)


def ritual_enabled(*, force_quiet: bool = False) -> bool:
    if force_quiet:
        return False
    flag = os.environ.get("CORTEX_ATTACH_RITUAL", "").strip().casefold()
    if flag in {"0", "off", "false", "no"}:
        return False
    if os.environ.get("NO_COLOR", "").strip() and flag not in {"force", "always", "1"}:
        return False
    # force/always: show full ritual even when stdout is not a TTY (demos / capture)
    if flag in {"force", "always"}:
        return True
    if os.environ.get("CI", "").strip() and flag not in {"1", "force", "always"}:
        return False
    return sys.stdout.isatty()


def _enable_windows_vt() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass


def pulse_symbol(
    symbol: str,
    *,
    color: str = GOLD,
    duration: float = PULSE_S,
    out: TextIO | None = None,
    enabled: bool = True,
) -> None:
    """One living glow cycle for a symbol (1.2s default)."""
    stream = out or sys.stdout
    if not enabled:
        stream.write(symbol)
        stream.flush()
        return
    frames = [
        f"{DIM}{color}{symbol}{RESET}",
        f"{color}{symbol}{RESET}",
        f"{BRIGHT}{color}{symbol}{RESET}",
        f"{color}{symbol}{RESET}",
        f"{DIM}{color}{symbol}{RESET}",
    ]
    scale = _cadence_scale()
    step = max(0.03, (duration * scale) / len(frames))
    for fr in frames:
        stream.write(f"\r{fr}  ")
        stream.flush()
        time.sleep(step)
    stream.write(f"\r{BRIGHT}{color}{symbol}{RESET}")
    stream.flush()


def _sleep(seconds: float, *, enabled: bool) -> None:
    if enabled and seconds > 0:
        time.sleep(seconds * _cadence_scale())


def _write(line: str = "", *, out: TextIO | None = None) -> None:
    stream = out or sys.stdout
    stream.write(line + ("\n" if not line.endswith("\n") and line != "" else ""))
    if line == "":
        stream.write("\n")
    stream.flush()


def _sol_luna_line(
    sol: bool,
    text: str,
    *,
    enabled: bool,
    out: TextIO | None = None,
) -> None:
    stream = out or sys.stdout
    sym = SYM_SOL if sol else SYM_LUNA
    color = GOLD if sol else SILVER
    if enabled:
        pulse_symbol(sym, color=color, duration=PULSE_S * 0.55, out=stream, enabled=True)
        stream.write(f"  {SOFT}{text}{RESET}\n")
    else:
        stream.write(f"{sym}  {text}\n")
    stream.flush()
    _sleep(STEP_PAUSE_S, enabled=enabled)


def render_opening(*, enabled: bool, out: TextIO | None = None) -> None:
    stream = out or sys.stdout
    if enabled:
        _enable_windows_vt()
        stream.write("\n")
        pulse_symbol(SYM_CORTEX, color=CYAN, out=stream, enabled=True)
        stream.write(f"  {BRIGHT}{CYAN}CORTEX{RESET}  ")
        pulse_symbol(SYM_CORTEX, color=CYAN, out=stream, enabled=True)
        stream.write("\n")
    else:
        stream.write(f"\n{SYM_CORTEX}  CORTEX  {SYM_CORTEX}\n")
    stream.flush()
    _sleep(LINE_PAUSE_S, enabled=enabled)
    for line in (
        f"{MUTED}   Sol rises in the east of the repository{RESET}" if enabled else "   Sol rises in the east of the repository",
        f"{MUTED}   Luna answers from the west of the graph{RESET}" if enabled else "   Luna answers from the west of the graph",
        f"{MUTED}   Two currents begin their Hermetic interlock…{RESET}" if enabled else "   Two currents begin their Hermetic interlock…",
    ):
        _write(line, out=stream)
        _sleep(LINE_PAUSE_S * 1.2, enabled=enabled)
    _write("", out=stream)


def render_work_steps(
    steps: list[tuple[bool, str, Callable[[], Any] | None]],
    *,
    enabled: bool,
    out: TextIO | None = None,
) -> list[Any]:
    """steps: (is_sol, label, optional work callable). Returns work results."""
    results: list[Any] = []
    for is_sol, label, work in steps:
        _sol_luna_line(is_sol, label, enabled=enabled, out=out)
        if work is not None:
            results.append(work())
        else:
            results.append(None)
    return results


def render_peak(*, enabled: bool, out: TextIO | None = None) -> None:
    stream = out or sys.stdout
    _write("", out=stream)
    bar = "─" * 56
    if enabled:
        _write(f"{MUTED}{bar}{RESET}", out=stream)
    else:
        _write(bar, out=stream)
    for line in (
        "   The two lights have met at the center of the lattice.",
        "   What was scattered is now one living axis.",
        "   The repository is no longer alone.",
    ):
        if enabled:
            # Soft dual-pulse of recognition
            pulse_symbol(SYM_CORTEX, color=CYAN, duration=PULSE_S * 0.35, out=stream, enabled=True)
            stream.write(f"  {BRIGHT}{SOFT}{line.strip()}{RESET}\n")
            stream.flush()
        else:
            _write(line, out=stream)
        _sleep(LINE_PAUSE_S * 1.4, enabled=enabled)
    if enabled:
        _write(f"{MUTED}{bar}{RESET}", out=stream)
    else:
        _write(bar, out=stream)
    _sleep(PEAK_HOLD_S, enabled=enabled)


def render_pyramidion(
    *,
    version: str,
    claim_line: str,
    enabled: bool,
    out: TextIO | None = None,
) -> None:
    stream = out or sys.stdout
    _write("", out=stream)
    pyramid = [
        "                  ▲",
        "                 ╱ ╲",
        "                ╱   ╲",
        "               ╱  ◈  ╲",
        "              ╱       ╲",
        "             ╱─────────╲",
        "            ╱   SEALED  ╲",
        "           ╱─────────────╲",
        "          ╱               ╲",
        "         ╱_________________╲",
    ]
    for line in pyramid:
        if enabled and ("◈" in line or "▲" in line):
            # Brief glow on peak lines, then static gold line
            pulse_symbol(
                SYM_PEAK if "▲" in line else SYM_CORTEX,
                color=GOLD,
                duration=PULSE_S * 0.35,
                out=stream,
                enabled=True,
            )
            stream.write("\r")
            stream.write(f"{BRIGHT}{GOLD}{line}{RESET}\n")
            stream.flush()
        else:
            if enabled:
                _write(f"{GOLD}{line}{RESET}", out=stream)
            else:
                _write(line, out=stream)
        _sleep(0.08, enabled=enabled)

    _write("", out=stream)
    for line in (
        "   The pyramidion is set.",
        "   The Great Work of this repository is capped.",
        f"   Geometry Seal {version} — Claim Receipt hashed.",
        "   Sol and Luna rest in perfect alignment.",
        "",
        "   Host remains sovereign.",
        "   Cortex remains the living memory organ.",
        "   The interlock is complete.",
    ):
        if "Claim Receipt" in line and claim_line:
            line = f"   {claim_line}"
        if enabled:
            _write(f"{SOFT}{line}{RESET}" if line else "", out=stream)
        else:
            _write(line, out=stream)
        _sleep(LINE_PAUSE_S, enabled=enabled)
    _sleep(SEAL_HOLD_S, enabled=enabled)


def public_display_paths(
    *,
    repo_name: str | None = None,
    demo: bool | None = None,
) -> tuple[str, str]:
    """Symbolic paths for ritual UI — never real absolute machine routes.

    Demo mode (CORTEX_ATTACH_DEMO=1) always shows generic public placeholders
    so recordings/screenshots never leak private Desktop/OneDrive paths.
    """
    if demo is None:
        demo = os.environ.get("CORTEX_ATTACH_DEMO", "").strip().casefold() in {
            "1",
            "true",
            "yes",
            "on",
        }
    if demo:
        host = os.environ.get("CORTEX_ATTACH_DEMO_HOST", "./your-project").strip() or "./your-project"
        body = os.environ.get("CORTEX_ATTACH_DEMO_BODY", "~/.cortex").strip() or "~/.cortex"
        return host, body
    name = (repo_name or "repository").strip() or "repository"
    # Public-safe relative form only — not C:\\Users\\... or /home/...
    host = f"./{name}"
    body = "~/.cortex"
    return host, body


def render_return_to_root(
    *,
    enabled: bool,
    out: TextIO | None = None,
    host_display: str | None = None,
    body_display: str | None = None,
) -> None:
    """Perfect re-integration — symbolic paths only, restore terminal state."""
    stream = out or sys.stdout
    _write("", out=stream)
    if enabled:
        # Final soft dual pulse then plain text
        pulse_symbol(SYM_CYCLE, color=MUTED, duration=PULSE_S * 0.4, out=stream, enabled=True)
        stream.write("\r")
        stream.write(f"{RESET}Returned to ROOT.\n")
        stream.write(RESET)
    else:
        stream.write("Returned to ROOT.\n")
    # Always show symbolic paths (never absolute personal routes)
    host = host_display or public_display_paths()[0]
    body = body_display or public_display_paths()[1]
    if enabled:
        stream.write(f"{MUTED}   host  {RESET}{SOFT}{host}{RESET}\n")
        stream.write(f"{MUTED}   body  {RESET}{SOFT}{body}{RESET}\n")
    else:
        stream.write(f"   host  {host}\n")
        stream.write(f"   body  {body}\n")
    stream.flush()
    _sleep(RETURN_HOLD_S, enabled=enabled)
    # Ensure no residual styles
    if enabled:
        stream.write(RESET)
        stream.flush()


def run_display_sequence(
    work_steps: list[tuple[bool, str, Callable[[], Any] | None]],
    *,
    version: str,
    claim_line: str = "Geometry Seal — Claim Receipt hashed.",
    force_quiet: bool = False,
    out: TextIO | None = None,
    host_display: str | None = None,
    body_display: str | None = None,
    repo_name: str | None = None,
) -> list[Any]:
    """Full ritual display wrapping work steps. Returns work results."""
    enabled = ritual_enabled(force_quiet=force_quiet)
    if host_display is None or body_display is None:
        h, b = public_display_paths(repo_name=repo_name)
        host_display = host_display or h
        body_display = body_display or b
    render_opening(enabled=enabled, out=out)
    results = render_work_steps(work_steps, enabled=enabled, out=out)
    render_peak(enabled=enabled, out=out)
    render_pyramidion(
        version=version, claim_line=claim_line, enabled=enabled, out=out
    )
    render_return_to_root(
        enabled=enabled,
        out=out,
        host_display=host_display,
        body_display=body_display,
    )
    return results
