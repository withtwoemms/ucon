from unittest import TestCase

from ucon import Scale
from ucon import ScaledUnit
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


class TestScaledUnit(TestCase):

    scaled_unit = ScaledUnit(unit=Units.gram, scale=Scale.one)

    def test___repr__(self):
        self.assertIn(str(self.scaled_unit.scale.value), str(self.scaled_unit))
        self.assertIn(self.scaled_unit.scale.name, str(self.scaled_unit))
        self.assertIn(self.scaled_unit.unit.name, str(self.scaled_unit))

    def test_to(self):
        to_scaled_unit = self.scaled_unit.to(Scale.kilo)
        self.assertIsInstance(to_scaled_unit.scale, ScaledUnit.Factor)
        self.assertEqual(1/Scale.kilo.value, to_scaled_unit.scale.value)
        self.assertEqual(Scale.kilo.name, to_scaled_unit.scale.name)

    def test___truediv__(self):
        gram = self.scaled_unit
        milligram = ScaledUnit(unit=Units.gram, scale=Scale.milli)
        volt = ScaledUnit(unit=Units.volt, scale=Scale.milli)
        unitless = ScaledUnit()
        self.assertEqual(1000, (gram/milligram).scale.value)
        self.assertEqual(Units.none, (gram/gram).unit)
        self.assertEqual(Units.gram, (gram/unitless).unit)
        self.assertEqual(Units.gram, (unitless/gram).unit)
        with self.assertRaises(RuntimeError):
            gram / volt

