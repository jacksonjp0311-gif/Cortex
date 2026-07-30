"""v7.1 operation requirements."""

from __future__ import annotations

import unittest

from cortex.constitutional_geometry import coordinate_from_bits
from cortex.constitutional_requirements import (
    OPERATION_REQUIREMENTS,
    coordinate_satisfies,
    missing_axes,
    required_bits,
    requirements_hash,
)


class RequirementsTests(unittest.TestCase):
    def test_promote_requires_1111(self) -> None:
        req = required_bits("promote")
        self.assertEqual(req, (1, 1, 1, 1))
        full = coordinate_from_bits((1, 1, 1, 1))
        self.assertTrue(coordinate_satisfies("promote", full))
        partial = coordinate_from_bits((1, 1, 1, 0))
        self.assertFalse(coordinate_satisfies("promote", partial))
        self.assertEqual(missing_axes("promote", partial), ["witness"])

    def test_adapt_requires_e_a_t(self) -> None:
        req = required_bits("adapt")
        self.assertEqual(req, (1, 1, 1, None))
        ok = coordinate_from_bits((1, 1, 1, 0))
        self.assertTrue(coordinate_satisfies("adapt", ok))
        bad = coordinate_from_bits((1, 0, 1, 0))
        self.assertFalse(coordinate_satisfies("adapt", bad))
        self.assertIn("authority", missing_axes("adapt", bad))

    def test_requirements_hash_stable(self) -> None:
        self.assertEqual(requirements_hash(), requirements_hash())
        self.assertEqual(len(OPERATION_REQUIREMENTS), 6)


if __name__ == "__main__":
    unittest.main()
