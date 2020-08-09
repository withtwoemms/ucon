from unittest import TestCase

from ucon import Unit
from ucon import Units


class TestUnit(TestCase):

    unit_name = 'second'
    unit_aliases = ('seconds', 'secs', 's', 'S')
    unit = Unit(unit_name, *unit_aliases)

    def test___repr__(self):
        self.assertEqual(f'<{self.unit_name}>', str(self.unit))


class TestUnits(TestCase):

    def test___truediv__(self):
        self.assertEqual(Units.none, Units.gram / Units.gram)
        self.assertEqual(Units.gram, Units.gram / Units.none)
        self.assertEqual(Units.gram, Units.none / Units.gram)

    def test_all(self):
        for unit in Units:
            self.assertIsInstance(unit.value, Unit)
        self.assertIsInstance(Units.all(), dict)

