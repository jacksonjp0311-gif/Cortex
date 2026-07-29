"""Machine-checkable continuation contracts — constrain only, never grant."""

from .check import (
    DEFAULT_CONTRACT,
    STRICT_CONTRACT,
    check_contract,
    contract_diff,
)

__all__ = [
    "DEFAULT_CONTRACT",
    "STRICT_CONTRACT",
    "check_contract",
    "contract_diff",
]
