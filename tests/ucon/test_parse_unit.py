# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
Tests for ucon.parse_unit and the get_unit_by_name deprecation shim (v1.7.0).
"""

import unittest
import warnings

from ucon import Dimension, parse_unit, units
from ucon.core import Unit, UnitProduct, UnknownUnitError
from ucon.resolver import get_unit_by_name


class TestParseUnitBasic(unittest.TestCase):
    """parse_unit smoke parity with prior get_unit_by_name behavior."""

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


class TestGetUnitByNameDeprecation(unittest.TestCase):
    """get_unit_by_name should still work but emit DeprecationWarning."""

    def test_emits_deprecation_warning(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            get_unit_by_name("meter")
        deps = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        self.assertTrue(deps, "expected at least one DeprecationWarning")
        self.assertIn("parse_unit", str(deps[0].message))

    def test_returns_same_result_as_parse_unit(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            self.assertEqual(get_unit_by_name("meter"), parse_unit("meter"))
            self.assertEqual(get_unit_by_name("m/s"), parse_unit("m/s"))
            self.assertEqual(get_unit_by_name("J/(mol*K)"), parse_unit("J/(mol*K)"))

    def test_propagates_unknown_unit_error(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            with self.assertRaises(UnknownUnitError):
                get_unit_by_name("nonsense_unit_xyz")


if __name__ == "__main__":
    unittest.main()
