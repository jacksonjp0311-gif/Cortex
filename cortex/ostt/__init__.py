"""OSTT compatibility surfaces for Cortex.

The Operator-Structured Transformation Theory (OSTT) layer is deliberately
shadow-only. It describes existing Cortex transitions with typed contracts and
reports which preconditions are satisfied; it does not execute operators,
change routing, or grant mutation authority.
"""

from .contracts import (
    CLAIM,
    GLYPH,
    SCHEMA,
    CORE_CONTRACTS,
    OperatorContract,
    OperatorTrace,
    TypedState,
    audit_runtime,
)

__all__ = [
    "CLAIM",
    "GLYPH",
    "SCHEMA",
    "CORE_CONTRACTS",
    "OperatorContract",
    "OperatorTrace",
    "TypedState",
    "audit_runtime",
]
