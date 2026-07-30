"""v7.1 four-axis constitutional geometry."""

from __future__ import annotations

import unittest

from cortex.constitutional_geometry import (
    AXIS_ORDER,
    ConstitutionalCoordinate,
    AxisAssessment,
    changed_axes,
    coordinate_from_bits,
    enumerate_coordinates,
    enumerate_coordinates_hash,
    hamming_distance,
)


class ConstitutionalGeometryTests(unittest.TestCase):
    def test_enumerate_16_deterministic(self) -> None:
        a = enumerate_coordinates()
        b = enumerate_coordinates()
        self.assertEqual(len(a), 16)
        self.assertEqual(a, b)
        labels = {tuple(c["bits"]) for c in a}
        self.assertEqual(len(labels), 16)
        h1 = enumerate_coordinates_hash()
        h2 = enumerate_coordinates_hash()
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)

    def test_hamming_and_changed(self) -> None:
        c0 = coordinate_from_bits((0, 0, 0, 0))
        c1 = coordinate_from_bits((1, 1, 1, 1))
        self.assertEqual(hamming_distance(c0, c1), 4)
        self.assertEqual(changed_axes(c0, c1), AXIS_ORDER)
        self.assertEqual(c1.bits(), (1, 1, 1, 1))

    def test_coordinate_from_bits_roundtrip(self) -> None:
        for i in range(16):
            bits = ((i >> 3) & 1, (i >> 2) & 1, (i >> 1) & 1, i & 1)
            c = coordinate_from_bits(bits)
            self.assertEqual(c.bits(), bits)


if __name__ == "__main__":
    unittest.main()
