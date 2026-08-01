"""Forward-compatible version gates for historical release receipts."""

from __future__ import annotations

import re


def release_at_least(current: str, minimum: tuple[int, int, int]) -> bool:
    """Return whether *current* is at or beyond a historical release floor."""

    match = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:[.+-]|$)", str(current).strip())
    if match is None:
        return False
    return tuple(int(part) for part in match.groups()) >= minimum
