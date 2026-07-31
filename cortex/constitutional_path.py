"""v7.1 Legal path planning — observe-only; never mutates or issues authority."""

from __future__ import annotations

from typing import Any

from .constitutional_geometry import (
    AXIS_ORDER,
    CLAIM,
    GLYPH,
    ConstitutionalCoordinate,
    assess_repo_coordinate,
    coordinate_from_bits,
)
from .constitutional_requirements import (
    assess_operation,
    missing_axes,
    required_bits,
)
from .constitutional_transition import SINGLE_AXIS_STEPS, assess_transition

SCHEMA = "cortex-constitutional-path/1.0"

# Display glyphs
PASS = "◆"
MISS = "◈"
META = "◇"


def compile_legal_path(
    operation: str,
    coordinate: ConstitutionalCoordinate | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compile next legal steps for an operation. Never mutates state.

    Does not issue capabilities, promote, or run witness evaluation.
    """
    ctx = dict(context or {})
    store = ctx.get("store")
    repo = ctx.get("repo")
    if coordinate is None:
        if store is not None and repo:
            coordinate = assess_repo_coordinate(
                store,
                str(repo),
                capability=ctx.get("capability"),
                require_witness=bool(ctx.get("require_witness")),
                witness_ok=ctx.get("witness_ok"),
                authority_ok=ctx.get("authority_ok"),
            )
        else:
            coordinate = coordinate_from_bits((0, 0, 0, 0))

    op = (operation or "").casefold().strip()
    live_gate = bool(ctx.get("live_gate"))
    gate = assess_operation(op, coordinate, live_gate=live_gate)
    try:
        req = list(required_bits(op))
    except KeyError:
        req = [None, None, None, None]

    missing = (
        missing_axes(op, coordinate, live_gate=live_gate)
        if gate.get("missing_axes") != ["unknown_operation"]
        else ["unknown_operation"]
    )
    # For path display under live_gate, show gate-eligible bits as validity
    bits = coordinate.gate_bits() if live_gate else coordinate.bits()
    raw_bits = coordinate.bits()

    # Next legal steps: single-axis fills in AXIS_ORDER (evidence→authority→epoch→witness)
    next_steps: list[str] = []
    for ax in missing:
        if ax.endswith("_truth_ineligible"):
            next_steps.append(f"UPGRADE_TRUTH_{ax.replace('_truth_ineligible', '').upper()}")
            continue
        if ax in AXIS_ORDER:
            next_steps.append(SINGLE_AXIS_STEPS.get(ax, f"SATISFY_{ax.upper()}"))

    # Transition toward required target
    missing_axes_clean = [m for m in missing if m in AXIS_ORDER]
    target_bits = []
    for i, r in enumerate(req):
        if r is None:
            target_bits.append(bits[i])
        else:
            target_bits.append(int(r))
    target = coordinate_from_bits(target_bits)
    transition = assess_transition(
        op,
        coordinate,
        target,
        compound=len(missing_axes_clean) > 1,
        compound_steps=tuple(next_steps) if len(missing_axes_clean) > 1 else None,
    )

    axis_rows = []
    for i, name in enumerate(AXIS_ORDER):
        required = req[i] is not None
        assessment = coordinate.axis(name)
        gate_ok = assessment.gate_eligible() if live_gate else bool(raw_bits[i])
        status = "PASS" if gate_ok else ("MISSING" if required else "N/A")
        if required and assessment.valid and not assessment.gate_eligible() and live_gate:
            status = "TRUTH_INELIGIBLE"
        glyph = PASS if gate_ok else (MISS if required else META)
        axis_rows.append(
            {
                "axis": name,
                "glyph": glyph,
                "status": status,
                "required": required,
                "valid": bool(raw_bits[i]),
                "gate_eligible": assessment.gate_eligible(),
                "truth_source": (
                    assessment.truth_source.value
                    if hasattr(assessment.truth_source, "value")
                    else str(assessment.truth_source)
                ),
                "reason": assessment.reason,
            }
        )

    blocked = not gate["allowed"]
    primary_next = next_steps[0] if next_steps else ("ALLOW" if gate["allowed"] else "DENIED")

    text = _render_path(
        operation=op,
        axis_rows=axis_rows,
        bits=bits,
        req=req,
        primary_next=primary_next,
        blocked=blocked,
    )

    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "operation": op,
        "coordinate": list(raw_bits),
        "gate_bits": list(coordinate.gate_bits()),
        "live_gate": live_gate,
        "required": req,
        "missing_axes": missing_axes_clean,
        "missing_proofs": missing_axes_clean,
        "truth_ineligible_axes": gate.get("truth_ineligible_axes") or [],
        "next_legal_steps": next_steps,
        "next_legal_step": primary_next,
        "allowed": gate["allowed"],
        "blocked": blocked,
        "axes": axis_rows,
        "transition": transition.to_dict(),
        "assessment": gate,
        "text": text,
        "mutated": False,
        "issued_capability": False,
        "promoted": False,
        "witness_evaluated": False,
        "claim_boundary": CLAIM,
    }


def _render_path(
    *,
    operation: str,
    axis_rows: list[dict[str, Any]],
    bits: tuple[int, int, int, int],
    req: list[Any],
    primary_next: str,
    blocked: bool,
) -> str:
    lines = [
        f"{GLYPH} CORTEX / CONSTITUTIONAL PATH",
        "│",
    ]
    for row in axis_rows:
        label = f"{row['glyph']} {row['axis']:<30} {row['status']}"
        lines.append(f"├─ {label}")
    lines.append("│")
    lines.append(f"├─ {META} coordinate                       ({bits[0]},{bits[1]},{bits[2]},{bits[3]})")
    req_s = ",".join("·" if r is None else str(r) for r in req)
    lines.append(f"├─ {META} required                         ({req_s})")
    lines.append(f"├─ {MISS if blocked else PASS} next legal step                  {primary_next}")
    op_label = operation.upper() if operation else "OP"
    lines.append(
        f"└─ {META} {op_label:<32} {'BLOCKED' if blocked else 'ALLOWED'}"
    )
    return "\n".join(lines)


def assess_operation_at_boundary(
    store: Any,
    repo: str,
    operation: str,
    *,
    capability: Any | None = None,
    authority_ok: bool | None = None,
    witness_ok: bool | None = None,
    require_witness: bool | None = None,
) -> dict[str, Any]:
    """Boundary gate used by promote / repair_readmit / federate.

    Observe-only coordinate + path; denial includes coordinate, missing axes,
    reasons, and required legal path.
    """
    op = (operation or "").casefold().strip()
    if require_witness is None:
        require_witness = op in {"promote", "repair_readmit"}
    coord = assess_repo_coordinate(
        store,
        repo,
        capability=capability,
        require_witness=bool(require_witness),
        witness_ok=witness_ok,
        authority_ok=authority_ok,
    )
    path = compile_legal_path(
        op,
        coord,
        context={
            "store": store,
            "repo": repo,
            "capability": capability,
            "require_witness": require_witness,
            "witness_ok": witness_ok,
            "authority_ok": authority_ok,
            "live_gate": True,
        },
    )
    # Phase binding: only BOUND is constitutionally compatible for live gates
    phase_binding: dict[str, Any] = {}
    reasons_extra: list[str] = []
    try:
        from .phases import BOUND, phase_binding_status, transition_phase

        # Attempt bind QUIESCENT under verified epoch (mutation path at boundary)
        try:
            transition_phase(
                store, repo, "QUIESCENT", reason=f"geometry_boundary:{op}"
            )
        except Exception:
            pass
        phase_binding = phase_binding_status(store, repo)
        if not phase_binding.get("constitutionally_compatible"):
            path = {
                **path,
                "allowed": False,
                "blocked": True,
                "missing_axes": list(path.get("missing_axes") or [])
                + ["phase_binding"],
                "next_legal_step": "BIND_PHASE_TO_VERIFIED_EPOCH",
                "next_legal_steps": list(path.get("next_legal_steps") or [])
                + ["BIND_PHASE_TO_VERIFIED_EPOCH"],
            }
            reasons_extra = [
                f"phase_binding_{phase_binding.get('binding')}",
                str(phase_binding.get("reason") or "phase_not_bound"),
            ]
    except Exception as exc:
        phase_binding = {"error": f"{type(exc).__name__}:{exc}"}
        reasons_extra = ["phase_binding_unavailable"]

    gate = path.get("assessment") or {}
    reasons = list(gate.get("reasons") or [])
    reasons.extend(reasons_extra)
    for ax in gate.get("truth_ineligible_axes") or []:
        reasons.append(f"truth_ineligible_{ax}")

    allowed = bool(path.get("allowed")) and not reasons_extra
    return {
        "allowed": allowed,
        "operation": op,
        "coordinate": path.get("coordinate") or list(coord.bits()),
        "gate_bits": list(coord.gate_bits()),
        "coordinate_detail": coord.to_dict(),
        "missing_axes": path.get("missing_axes") or [],
        "truth_ineligible_axes": gate.get("truth_ineligible_axes") or [],
        "reasons": list(dict.fromkeys(reasons)),
        "required_legal_path": path.get("next_legal_steps") or [],
        "phase_binding": phase_binding,
        "path": path,
        "claim_boundary": CLAIM,
    }
