
# © 2025 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

from unittest import TestCase

from ucon import Dimension, parse_unit, units
from ucon.core import UnknownUnitError


class TestUnits(TestCase):

    def test_has_expected_basic_units(self):
        expected_basic_units = {'volt', 'liter', 'gram', 'second', 'kelvin', 'mole', 'coulomb'}
        missing = set()
        for name in expected_basic_units:
            try:
                parse_unit(name)
            except UnknownUnitError:
                missing.add(name)
        assert not missing, f"Missing expected units: {missing}"
        # 'none' is a sentinel Unit() not registered in the resolver;
        # confirm it's still exported as a module attribute.
        assert hasattr(units, 'none'), "sentinel 'none' should be exported"

    def test___truediv__(self):
        self.assertEqual(units.none, units.gram / units.gram)
        self.assertEqual(units.gram, units.gram / units.none)

        composite_unit = units.gram / units.liter
        self.assertEqual("g/L", composite_unit.shorthand)
        self.assertEqual(Dimension.density, composite_unit.dimension)
