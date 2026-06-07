# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
Tests for ucon.parse_unit (v2.0).
"""

import unittest

from ucon import Dimension, parse_unit, units
from ucon.core import Unit, UnitProduct, UnknownUnitError


class TestParseUnitBasic(unittest.TestCase):
    """parse_unit smoke tests."""

    def test_atomic_unit(self):
        self.assertEqual(parse_unit("meter"), units.meter)

    def test_atomic_alias(self):
        self.assertEqual(parse_unit("m"), units.meter)

    def test_scaled_unit(self):
        result = parse_unit("km")
        # result is some Unit/UnitProduct over length dimension
        self.assertEqual(result.dimension, Dimension.length)

    def test_composite_unit(self):
        result = parse_unit("m/s")
        self.assertIsInstance(result, UnitProduct)
        self.assertEqual(result.dimension, Dimension.velocity)

    def test_unknown_unit_raises(self):
        with self.assertRaises(UnknownUnitError):
            parse_unit("nonsense_unit_xyz")


if __name__ == "__main__":
    unittest.main()
