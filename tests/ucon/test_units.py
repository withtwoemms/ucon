

from unittest import TestCase

from ucon import units
from ucon.dimension import Dimension
from ucon.unit import Unit


class TestUnits(TestCase):

    def test_has_expected_basic_units(self):
        expected_basic_units = {'none', 'volt', 'liter', 'gram', 'second', 'kelvin', 'mole', 'coulomb'}
        missing = {name for name in expected_basic_units if not units.have(name)}
        assert not missing, f"Missing expected units: {missing}"

    def test___truediv__(self):
        self.assertEqual(units.none, units.gram / units.gram)
        self.assertEqual(units.gram, units.gram / units.none)

        self.assertEqual(Unit(name='(g/L)', dimension=Dimension.density), units.gram / units.liter)
