"""v7.1 Transition assessment — one-axis and compound paths; deny free diagonals."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Sequence

from .constitutional_geometry import (
    AXIS_ORDER,
    CLAIM,
    ConstitutionalCoordinate,
    changed_axes,
    hamming_distance,
)
from .constitutional_requirements import KNOWN_OPERATIONS, assess_operation

SCHEMA = "cortex-constitutional-transition/1.0"


@dataclass(frozen=True)
class TransitionAssessment:
    allowed: bool
    operation: str
    source_bits: tuple[int, int, int, int]
    target_bits: tuple[int, int, int, int]
    changed_axes: tuple[str, ...]
    diagonal: bool
    reasons: tuple[str, ...]
    required_steps: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["schema_version"] = SCHEMA
        d["claim_boundary"] = CLAIM
        return d


# Declared compound transitions: operation → allowed multi-axis change sets
# with required internal steps. Keys are frozensets of axis names.
COMPOUND_TRANSITIONS: dict[str, dict[frozenset[str], tuple[str, ...]]] = {
    "promote": {
        frozenset({"witness"}): ("COMMIT_WITNESS", "VERIFY_WITNESS"),
        frozenset({"authority", "witness"}): (
            "ISSUE_CAPABILITY",
            "COMMIT_WITNESS",
            "VERIFY_WITNESS",
        ),
        frozenset({"evidence", "authority", "epoch", "witness"}): (
            "VERIFY_EVIDENCE",
            "ISSUE_CAPABILITY",
            "VERIFY_EPOCH",
            "COMMIT_WITNESS",
            "VERIFY_WITNESS",
        ),
    },
    "repair_readmit": {
        frozenset({"witness"}): ("VERIFY_REPAIR", "COMMIT_WITNESS"),
        frozenset({"evidence", "authority", "epoch", "witness"}): (
            "VERIFY_EVIDENCE",
            "ISSUE_REPAIR_CAPABILITY",
            "VERIFY_EPOCH",
            "VERIFY_REPAIR",
            "COMMIT_WITNESS",
        ),
    },
    "adapt": {
        frozenset({"authority"}): ("ISSUE_CAPABILITY", "BIND_EPOCH"),
        frozenset({"evidence", "authority", "epoch"}): (
            "VERIFY_EVIDENCE",
            "ISSUE_CAPABILITY",
            "VERIFY_EPOCH",
        ),
    },
    "federate": {
        frozenset({"authority"}): ("ISSUE_FEDERATION_CAPABILITY", "VERIFY_EPOCH"),
        frozenset({"evidence", "authority", "epoch"}): (
            "VERIFY_EVIDENCE",
            "ISSUE_FEDERATION_CAPABILITY",
            "VERIFY_EPOCH",
        ),
    },
    "repair": {
        frozenset({"authority"}): ("ISSUE_REPAIR_CAPABILITY",),
        frozenset({"authority", "epoch"}): ("VERIFY_EPOCH", "ISSUE_REPAIR_CAPABILITY"),
    },
    "retrieve": {
        frozenset({"evidence"}): ("VERIFY_EVIDENCE",),
        frozenset({"epoch"}): ("VERIFY_EPOCH",),
        frozenset({"evidence", "epoch"}): ("VERIFY_EVIDENCE", "VERIFY_EPOCH"),
    },
}

# Legal single-axis flips toward validity (0→1) with named step
SINGLE_AXIS_STEPS: dict[str, str] = {
    "evidence": "VERIFY_EVIDENCE",
    "authority": "ISSUE_CAPABILITY",
    "epoch": "VERIFY_EPOCH",
    "witness": "COMMIT_WITNESS",
}


def assess_transition(
    operation: str,
    source: ConstitutionalCoordinate | Sequence[int],
    target: ConstitutionalCoordinate | Sequence[int] | None = None,
    *,
    compound: bool = False,
    compound_steps: Sequence[str] | None = None,
    allow_unknown_axes: bool = False,
) -> TransitionAssessment:
    """Assess moving from source toward target (or toward operation requirements).

    Rules:
    - one-axis transition is not automatically legal (must map to a known step)
    - multi-axis = diagonal; denied unless compound=True with steps or declared compound
    - unknown operations deny
    - unknown axis state (bits not 0/1) denies
    """
    op = (operation or "").casefold().strip()
    if op not in KNOWN_OPERATIONS:
        sb = _as_bits(source)
        return TransitionAssessment(
            allowed=False,
            operation=operation,
            source_bits=sb,
            target_bits=sb,
            changed_axes=(),
            diagonal=False,
            reasons=(f"unknown_operation:{operation}",),
            required_steps=(),
        )

    try:
        sb = _as_bits(source)
        if target is None:
            # Target = source with required axes set to 1
            from .constitutional_requirements import required_bits

            req = required_bits(op)
            tb = tuple(
                (sb[i] if r is None else int(r)) for i, r in enumerate(req)
            )  # type: ignore[misc]
            tb = (int(tb[0]), int(tb[1]), int(tb[2]), int(tb[3]))
        else:
            tb = _as_bits(target)
    except ValueError as exc:
        return TransitionAssessment(
            allowed=False,
            operation=op,
            source_bits=(0, 0, 0, 0),
            target_bits=(0, 0, 0, 0),
            changed_axes=(),
            diagonal=False,
            reasons=(f"unknown_axis_state:{exc}",),
            required_steps=(),
        )

    if not allow_unknown_axes:
        for name, b in zip(AXIS_ORDER, sb + tb):
            if b not in (0, 1):
                return TransitionAssessment(
                    allowed=False,
                    operation=op,
                    source_bits=sb,
                    target_bits=tb,
                    changed_axes=(),
                    diagonal=False,
                    reasons=("unknown_axis_state",),
                    required_steps=(),
                )

    changed = changed_axes(sb, tb)
    dist = hamming_distance(sb, tb)
    diagonal = dist > 1

    # Already at target
    if dist == 0:
        # Still need operation satisfaction from source if source is a coordinate
        if isinstance(source, ConstitutionalCoordinate):
            gate = assess_operation(op, source)
            if gate["allowed"]:
                return TransitionAssessment(
                    True, op, sb, tb, (), False, (), ()
                )
            return TransitionAssessment(
                False,
                op,
                sb,
                tb,
                (),
                False,
                tuple(gate.get("reasons") or ["requirements_unmet"]),
                tuple(f"SATISFY_{a.upper()}" for a in (gate.get("missing_axes") or [])),
            )
        return TransitionAssessment(True, op, sb, tb, (), False, (), ())

    # One-axis: legal only if 0→1 on a known axis step (not automatic)
    if dist == 1:
        axis = changed[0]
        # Denying 1→0 flips as recovery requires explicit compound
        si = AXIS_ORDER.index(axis)
        if sb[si] == 1 and tb[si] == 0:
            return TransitionAssessment(
                False,
                op,
                sb,
                tb,
                changed,
                False,
                ("axis_clear_requires_compound_or_explicit_revoke",),
                (f"EXPLICIT_CLEAR_{axis.upper()}",),
            )
        step = SINGLE_AXIS_STEPS.get(axis)
        if not step:
            return TransitionAssessment(
                False,
                op,
                sb,
                tb,
                changed,
                False,
                ("one_axis_transition_not_auto_legal",),
                (),
            )
        return TransitionAssessment(
            True,
            op,
            sb,
            tb,
            changed,
            False,
            (),
            (step,),
        )

    # Diagonal (multi-axis)
    steps: tuple[str, ...] = ()
    if compound_steps:
        steps = tuple(compound_steps)
        if len(steps) < dist:
            return TransitionAssessment(
                False,
                op,
                sb,
                tb,
                changed,
                True,
                ("compound_steps_insufficient", "diagonal_denied"),
                steps,
            )
        return TransitionAssessment(
            True,
            op,
            sb,
            tb,
            changed,
            True,
            (),
            steps,
        )

    if compound:
        declared = COMPOUND_TRANSITIONS.get(op, {})
        key = frozenset(changed)
        if key in declared:
            return TransitionAssessment(
                True, op, sb, tb, changed, True, (), declared[key]
            )
        # try any declared superset covering changed
        for k, v in declared.items():
            if key <= k:
                return TransitionAssessment(True, op, sb, tb, changed, True, (), v)
        return TransitionAssessment(
            False,
            op,
            sb,
            tb,
            changed,
            True,
            ("diagonal_not_declared_compound",),
            tuple(SINGLE_AXIS_STEPS[a] for a in changed if a in SINGLE_AXIS_STEPS),
        )

    return TransitionAssessment(
        False,
        op,
        sb,
        tb,
        changed,
        True,
        ("diagonal_denied", "compound_not_declared"),
        tuple(SINGLE_AXIS_STEPS[a] for a in changed if a in SINGLE_AXIS_STEPS),
    )


def _as_bits(
    c: ConstitutionalCoordinate | Sequence[int],
) -> tuple[int, int, int, int]:
    if isinstance(c, ConstitutionalCoordinate):
        b = c.bits()
    else:
        if len(c) != 4:
            raise ValueError("bits length must be 4")
        b = tuple(int(x) for x in c)  # type: ignore[assignment]
        if any(x not in (0, 1) for x in b):
            raise ValueError("bits must be 0 or 1")
        b = (int(b[0]), int(b[1]), int(b[2]), int(b[3]))
    return b
