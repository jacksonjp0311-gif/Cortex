"""OSTT compatibility surfaces for Cortex.

The Operator-Structured Transformation Theory (OSTT) layer is deliberately
shadow-only. It describes existing Cortex transitions with typed contracts and
reports which preconditions are satisfied; it does not execute operators,
change routing, or grant mutation authority.
"""

from .contracts import (
    ActivationObservationInput,
    CLAIM,
    GLYPH,
    SCHEMA,
    CORE_CONTRACTS,
    OperatorContract,
    OperatorTrace,
    MeasuredActivationTransition,
    TypedState,
    audit_runtime,
)
from .residuals import (
    DEFAULT_EPSILON,
    DEFAULT_MAX_BURDEN,
    RESIDUAL_GLYPH,
    RESIDUAL_SCHEMA,
    ResidualReceipt,
    residual_evidence_report,
)
from .activation import activation_observation_receipt
from .conformance import (
    CLAIM_BOUNDARY as ACTIVATION_CONFORMANCE_CLAIM,
    activation_cohort_report,
    activation_receipt_report,
    build_activation_conformance_receipt,
    finalize_activation_observation,
    verify_activation_receipt,
)

__all__ = [
    "ActivationObservationInput",
    "MeasuredActivationTransition",
    "CLAIM",
    "GLYPH",
    "SCHEMA",
    "CORE_CONTRACTS",
    "OperatorContract",
    "OperatorTrace",
    "TypedState",
    "audit_runtime",
    "DEFAULT_EPSILON",
    "DEFAULT_MAX_BURDEN",
    "RESIDUAL_GLYPH",
    "RESIDUAL_SCHEMA",
    "ResidualReceipt",
    "residual_evidence_report",
    "activation_observation_receipt",
    "ACTIVATION_CONFORMANCE_CLAIM",
    "activation_cohort_report",
    "activation_receipt_report",
    "build_activation_conformance_receipt",
    "finalize_activation_observation",
    "verify_activation_receipt",
]
