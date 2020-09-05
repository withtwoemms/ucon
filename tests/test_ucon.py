from unittest import TestCase

from ucon import Number
from ucon import Exponent
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
        self.assertEqual(Scale.kibi, Scale.mebi / Scale.kibi)
        self.assertEqual(Scale.milli, Scale.one / Scale.deca / Scale.deca / Scale.deca)
        self.assertEqual(Scale.deca, Scale.kilo / Scale.hecto)
        self.assertEqual(Scale._kibi, Scale.one / Scale.kibi)
        self.assertEqual(Scale.kibi, Scale.kibi / Scale.one)
        self.assertEqual(Scale.one, Scale.kibi / Scale.kibi)
        self.assertEqual(Scale.one, Scale.kibi / Scale.kilo)

    def test___lt__(self):
        self.assertLess(Scale.one, Scale.kilo)

    def test___gt__(self):
        self.assertGreater(Scale.kilo, Scale.one)

    def test_all(self):
        for scale in Scale:
            self.assertTrue(isinstance(scale.value, Exponent))
        self.assertIsInstance(Scale.all(), dict)


class TestScaledUnit(TestCase):

    scaled_unit = ScaledUnit(unit=Units.gram, scale=Scale.one)

    def test___repr__(self):
        self.assertIn(str(self.scaled_unit.unit.name), str(self.scaled_unit))
        self.assertIn(str(self.scaled_unit.scale.value.evaluated), str(self.scaled_unit))
        self.assertIn(self.scaled_unit.unit.name, str(self.scaled_unit))

    def test___truediv__(self):
        gram = self.scaled_unit
        milligram = ScaledUnit(unit=Units.gram, scale=Scale.milli)
        volt = ScaledUnit(unit=Units.volt, scale=Scale.milli)
        unitless = ScaledUnit()

        self.assertEqual(1000, (gram/milligram).scale.value.evaluated)
        self.assertEqual(Units.none, (gram/gram).unit)
        self.assertEqual(Units.gram, (gram/unitless).unit)
        self.assertEqual(Units.gram, (unitless/gram).unit)
        with self.assertRaises(RuntimeError):
            gram / volt


class TestNumber(TestCase):

    gram = ScaledUnit(unit=Units.gram, scale=Scale.one)
    milligram = ScaledUnit(unit=Units.gram, scale=Scale.milli)
    decagram = ScaledUnit(unit=Units.gram, scale=Scale.deca)
    kibigram = ScaledUnit(unit=Units.gram, scale=Scale.kibi)

    number = Number(unit=gram, quantity=1)

    def test_simplify(self):
        ten_decagrams = Number(unit=self.decagram, quantity=10)
        point_one_decagrams = Number(unit=self.decagram, quantity=0.1)
        two_kibigrams = Number(unit=self.kibigram, quantity=2)

        self.assertEqual(Number(unit=self.gram, quantity=100), ten_decagrams.simplify())
        self.assertEqual(Number(unit=self.gram, quantity=1), point_one_decagrams.simplify())
        self.assertEqual(Number(unit=self.gram, quantity=2048), two_kibigrams.simplify())

    def test___repr__(self):
        self.assertIn(str(self.number.quantity), str(self.number))
        self.assertIn(str(self.number.unit.scale.value.evaluated), str(self.number))
        self.assertIn(self.number.unit.unit.name, str(self.number))

    def test___truediv__(self):
        some_number = Number(unit=self.decagram, quantity=10)
        another_number = Number(unit=self.milligram, quantity=10)
        that_number = Number(unit=self.kibigram, quantity=10)

        some_quotient = self.number / some_number
        another_quotient = self.number / another_number
        that_quotient = self.number / that_number

        self.assertEqual(some_quotient.value, 0.01)
        self.assertEqual(another_quotient.value, 100.0)
        self.assertEqual(that_quotient.value, 0.00009765625)

