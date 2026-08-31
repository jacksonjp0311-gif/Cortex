"""Forward-compatible version gates for historical release receipts."""

from __future__ import annotations

import re


def release_at_least(current: str, minimum: tuple[int, int, int]) -> bool:
    """Return whether *current* is at or beyond a historical release floor."""

    # Cortex package versions use PEP 440 alpha suffixes (for example
    # ``10.0.0a12``). Historical receipt gates compare only the three-part
    # release tuple, so a valid suffix must not make a newer alpha look older
    # than v7/v8. A non-digit boundary also rejects an accidental fourth
    # numeric component.
    match = re.match(
        r"^(\d+)\.(\d+)\.(\d+)(?:(?:a|b|rc)\d+|\.post\d+|\.dev\d+|[-+][A-Za-z0-9][A-Za-z0-9.-]*)?$",
        str(current).strip(),
        flags=re.IGNORECASE,
    )
    if match is None:
        return False
    return tuple(int(part) for part in match.groups()) >= minimum
