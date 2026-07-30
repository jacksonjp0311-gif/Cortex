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
    gate = assess_operation(op, coordinate)
    try:
        req = list(required_bits(op))
    except KeyError:
        req = [None, None, None, None]

    missing = missing_axes(op, coordinate) if gate.get("missing_axes") != ["unknown_operation"] else ["unknown_operation"]
    bits = coordinate.bits()

    # Next legal steps: single-axis fills in AXIS_ORDER (evidence→authority→epoch→witness)
    next_steps: list[str] = []
    for ax in AXIS_ORDER:
        if ax in missing:
            next_steps.append(SINGLE_AXIS_STEPS.get(ax, f"SATISFY_{ax.upper()}"))

    # Transition toward required target
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
        compound=len(missing) > 1,
        compound_steps=tuple(next_steps) if len(missing) > 1 else None,
    )

    axis_rows = []
    for i, name in enumerate(AXIS_ORDER):
        required = req[i] is not None
        valid = bool(bits[i])
        status = "PASS" if valid else ("MISSING" if required else "N/A")
        glyph = PASS if valid else (MISS if required else META)
        assessment = coordinate.axis(name)
        axis_rows.append(
            {
                "axis": name,
                "glyph": glyph,
                "status": status,
                "required": required,
                "valid": valid,
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
        "coordinate": list(bits),
        "required": req,
        "missing_axes": missing,
        "missing_proofs": missing,
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
        },
    )
    return {
        "allowed": path["allowed"],
        "operation": op,
        "coordinate": path["coordinate"],
        "coordinate_detail": coord.to_dict(),
        "missing_axes": path["missing_axes"],
        "reasons": list(path.get("assessment", {}).get("reasons") or []),
        "required_legal_path": path["next_legal_steps"],
        "path": path,
        "claim_boundary": CLAIM,
    }
