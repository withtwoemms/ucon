from unittest import TestCase

from ucon import Scale
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


class TestScale(TestCase):

    def test___truediv__(self):
        self.assertEqual(Scale.deca, Scale.one / Scale.deci)
        self.assertEqual(Scale.deci, Scale.one / Scale.deca)
        self.assertEqual(Scale._kibi, Scale.one / Scale.kibi)
        self.assertEqual(Scale.milli, Scale.one / Scale.deca / Scale.deca / Scale.deca)
        self.assertEqual(Scale.deca, Scale.kilo / Scale.hecto)
        with self.assertRaises(KeyError):
            Scale.kibi / Scale.kilo

    def test___lt__(self):
        self.assertLess(Scale.kilo, Scale.one)

    def test___gt__(self):
        self.assertGreater(Scale.one, Scale.kilo)

    def test_all(self):
        for scale in Scale:
            self.assertTrue(isinstance(scale.value, int) or isinstance(scale.value, float))
        self.assertIsInstance(Scale.all(), dict)

