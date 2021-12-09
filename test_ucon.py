from unittest import TestCase

from ucon import Number
from ucon import Exponent
from ucon import Ratio
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

    def test_has_expected_basic_units(self):
        expected_basic_units = {'none', 'volt', 'liter', 'gram', 'second', 'kelvin', 'mole', 'coulomb'}
        self.assertEqual(set(item.name for item in Units), expected_basic_units)

    def test___truediv__(self):
        self.assertEqual(Units.none, Units.gram / Units.gram)
        self.assertEqual(Units.gram, Units.gram / Units.none)
        self.assertEqual(Units.gram, Units.none / Units.gram)

        with self.assertRaises(ValueError):
            Units.gram / Units.liter

    def test_all(self):
        for unit in Units:
            self.assertIsInstance(unit.value, Unit)
        self.assertIsInstance(Units.all(), dict)


class TestExponent(TestCase):

    thousand = Exponent(10, 3)
    thousandth = Exponent(10, -3)

    def test___init__(self):
        with self.assertRaises(ValueError):
            Exponent(5, 3)  # no support for base 5 logarithms

    def test_parts(self):
        self.assertEqual((10, 3), self.thousand.parts())
        self.assertEqual((10, -3), self.thousandth.parts())

    def test___truediv__(self):
        self.assertEqual(1000, self.thousand.evaluated)
        self.assertEqual(float(1/1000), self.thousandth.evaluated)
        self.assertEqual(float(1000000), (self.thousand / self.thousandth))

    def test___lt__(self):
        self.assertLess(self.thousandth, self.thousand)

    def test___gt__(self):
        self.assertGreater(self.thousand, self.thousandth)

    def test___repr__(self):
        self.assertEqual(str(self.thousand), '<10^3>')
        self.assertEqual(str(self.thousandth), '<10^-3>')


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


class TestNumber(TestCase):

    number = Number(unit=Units.gram, quantity=1)

    def test_as_ratio(self):
        ratio = self.number.as_ratio()
        self.assertIsInstance(ratio, Ratio)
        self.assertEqual(ratio.numerator, self.number)
        self.assertEqual(ratio.denominator, Number())

    def test_simplify(self):
        ten_decagrams = Number(unit=Units.gram, scale=Scale.deca, quantity=10)
        point_one_decagrams = Number(unit=Units.gram, scale=Scale.deca, quantity=0.1)
        two_kibigrams = Number(unit=Units.gram, scale=Scale.kibi, quantity=2)

        self.assertEqual(Number(unit=Units.gram, quantity=100), ten_decagrams.simplify())
        self.assertEqual(Number(unit=Units.gram, quantity=1), point_one_decagrams.simplify())
        self.assertEqual(Number(unit=Units.gram, quantity=2048), two_kibigrams.simplify())

    def test_to(self):
        thousandth_of_a_kilogram = Number(unit=Units.gram, scale=Scale.kilo, quantity=0.001)
        thousand_milligrams = Number(unit=Units.gram, scale=Scale.milli, quantity=1000)
        kibigram_fraction = Number(unit=Units.gram, scale=Scale.kibi, quantity=0.0009765625)

        self.assertEqual(thousandth_of_a_kilogram, self.number.to(Scale.kilo))
        self.assertEqual(thousand_milligrams, self.number.to(Scale.milli))
        self.assertEqual(kibigram_fraction, self.number.to(Scale.kibi))

    def test___repr__(self):
        self.assertIn(str(self.number.quantity), str(self.number))
        self.assertIn(str(self.number.scale.value.evaluated), str(self.number))
        self.assertIn(self.number.unit.name, str(self.number))

    def test___truediv__(self):
        some_number = Number(unit=Units.gram, scale=Scale.deca, quantity=10)
        another_number = Number(unit=Units.gram, scale=Scale.milli, quantity=10)
        that_number = Number(unit=Units.gram, scale=Scale.kibi, quantity=10)

        some_quotient = self.number / some_number
        another_quotient = self.number / another_number
        that_quotient = self.number / that_number

        self.assertEqual(some_quotient.value, 0.01)
        self.assertEqual(another_quotient.value, 100.0)
        self.assertEqual(that_quotient.value, 0.00009765625)

    def test___eq__(self):
        self.assertEqual(self.number, Ratio(self.number))  # 1 gram / 1
        with self.assertRaises(ValueError):
            self.number == 1


class TestRatio(TestCase):

    point_five = Number(quantity=0.5)
    one = Number()
    two = Number(quantity=2)
    three = Number(quantity=3)
    four = Number(quantity=4)

    one_half = Ratio(numerator=one, denominator=two)
    three_fourths = Ratio(numerator=three, denominator=four)
    one_ratio = Ratio(numerator=one)
    three_halves = Ratio(numerator=three, denominator=two)
    two_ratio = Ratio(numerator=two, denominator=one)

    bromine_density = Ratio(Number(Units.gram, quantity=3.119), Number(Units.liter, Scale.milli))

    def test_evaluate(self):
        self.assertEqual(self.one_ratio.numerator, self.one)
        self.assertEqual(self.one_ratio.denominator, self.one)
        self.assertEqual(self.one_ratio.evaluate(), self.one)
        self.assertEqual(self.two_ratio.evaluate(), self.two)

    def test_reciprocal(self):
        self.assertEqual(self.two_ratio.reciprocal().numerator, self.one)
        self.assertEqual(self.two_ratio.reciprocal().denominator, self.two)
        self.assertEqual(self.two_ratio.reciprocal().evaluate(), self.point_five)

    def test___mul__(self):
        # Does commutivity hold?
        self.assertEqual(self.three_halves * self.one_half, self.three_fourths)
        self.assertEqual(self.one_half * self.three_halves, self.three_fourths)

        # How many grams of bromine are in 2 milliliters?
        two_milliliters_bromine = Number(Units.liter, Scale.milli, 2)
        answer = two_milliliters_bromine.as_ratio() * self.bromine_density
        self.assertEqual(answer.evaluate().value, 6.238) # Grams

    def test___eq__(self):
        self.assertEqual(self.one_half, self.point_five)
        with self.assertRaises(ValueError):
            self.one_half == 1/2

    def test___repr__(self):
        self.assertEqual(str(self.one_ratio), '<1.0 >')
        self.assertEqual(str(self.two_ratio), '<2 > / <1 >')
        self.assertEqual(str(self.two_ratio.evaluate()), '<2.0 >')

