
# © 2025 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

from unittest import TestCase

from ucon import units
from ucon.core import Dimension


class TestUnits(TestCase):

    def test_has_expected_basic_units(self):
        expected_basic_units = {'none', 'volt', 'liter', 'gram', 'second', 'kelvin', 'mole', 'coulomb'}
        missing = {name for name in expected_basic_units if not units.have(name)}
        assert not missing, f"Missing expected units: {missing}"

    def test___truediv__(self):
        self.assertEqual(units.none, units.gram / units.gram)
        self.assertEqual(units.gram, units.gram / units.none)

        composite_unit = units.gram / units.liter
        self.assertEqual("g/L", composite_unit.shorthand)
        self.assertEqual(Dimension.density, composite_unit.dimension)
