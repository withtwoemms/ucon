from unittest import TestCase

from ucon import Number
from ucon import Exponent
from ucon import Ratio
from ucon import Scale
from ucon import Dimension
from ucon import units
from ucon.unit import Unit


class TestUnit(TestCase):

    unit_name = 'second'
    unit_type = 'time'
    unit_aliases = ('seconds', 'secs', 's', 'S')
    unit = Unit(*unit_aliases, name=unit_name, dimension=Dimension.time)

    def test___repr__(self):
        self.assertEqual(f'<{self.unit_type} | {self.unit_name}>', str(self.unit))


class TestUnits(TestCase):

    def test_has_expected_basic_units(self):
        expected_basic_units = {'none', 'volt', 'liter', 'gram', 'second', 'kelvin', 'mole', 'coulomb'}
        missing = {name for name in expected_basic_units if not units.have(name)}
        assert not missing, f"Missing expected units: {missing}"

    def test___truediv__(self):
        self.assertEqual(units.none, units.gram / units.gram)
        self.assertEqual(units.gram, units.gram / units.none)

        self.assertEqual(Unit(name='(g/L)', dimension=Dimension.density), units.gram / units.liter)


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

    number = Number(unit=units.gram, quantity=1)

    def test_as_ratio(self):
        ratio = self.number.as_ratio()
        self.assertIsInstance(ratio, Ratio)
        self.assertEqual(ratio.numerator, self.number)
        self.assertEqual(ratio.denominator, Number())

    def test_simplify(self):
        ten_decagrams = Number(unit=units.gram, scale=Scale.deca, quantity=10)
        point_one_decagrams = Number(unit=units.gram, scale=Scale.deca, quantity=0.1)
        two_kibigrams = Number(unit=units.gram, scale=Scale.kibi, quantity=2)

        self.assertEqual(Number(unit=units.gram, quantity=100), ten_decagrams.simplify())
        self.assertEqual(Number(unit=units.gram, quantity=1), point_one_decagrams.simplify())
        self.assertEqual(Number(unit=units.gram, quantity=2048), two_kibigrams.simplify())

    def test_to(self):
        thousandth_of_a_kilogram = Number(unit=units.gram, scale=Scale.kilo, quantity=0.001)
        thousand_milligrams = Number(unit=units.gram, scale=Scale.milli, quantity=1000)
        kibigram_fraction = Number(unit=units.gram, scale=Scale.kibi, quantity=0.0009765625)

        self.assertEqual(thousandth_of_a_kilogram, self.number.to(Scale.kilo))
        self.assertEqual(thousand_milligrams, self.number.to(Scale.milli))
        self.assertEqual(kibigram_fraction, self.number.to(Scale.kibi))

    def test___repr__(self):
        self.assertIn(str(self.number.quantity), str(self.number))
        self.assertIn(str(self.number.scale.value.evaluated), str(self.number))
        self.assertIn(self.number.unit.name, str(self.number))

    def test___truediv__(self):
        some_number = Number(unit=units.gram, scale=Scale.deca, quantity=10)
        another_number = Number(unit=units.gram, scale=Scale.milli, quantity=10)
        that_number = Number(unit=units.gram, scale=Scale.kibi, quantity=10)

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

    def test_evaluate(self):
        self.assertEqual(self.one_ratio.numerator, self.one)
        self.assertEqual(self.one_ratio.denominator, self.one)
        self.assertEqual(self.one_ratio.evaluate(), self.one)
        self.assertEqual(self.two_ratio.evaluate(), self.two)

    def test_reciprocal(self):
        self.assertEqual(self.two_ratio.reciprocal().numerator, self.one)
        self.assertEqual(self.two_ratio.reciprocal().denominator, self.two)
        self.assertEqual(self.two_ratio.reciprocal().evaluate(), self.point_five)

    def test___mul__commutivity(self):
        # Does commutivity hold?
        self.assertEqual(self.three_halves * self.one_half, self.three_fourths)
        self.assertEqual(self.one_half * self.three_halves, self.three_fourths)

    def test___mul__(self):
        bromine_density = Ratio(Number(units.gram, quantity=3.119), Number(units.liter, Scale.milli))
    
        # How many grams of bromine are in 2 milliliters?
        two_milliliters_bromine = Number(units.liter, Scale.milli, 2)
        ratio = two_milliliters_bromine.as_ratio() * bromine_density
        answer = ratio.evaluate()
        self.assertEqual(answer.unit.dimension, Dimension.mass)
        self.assertEqual(answer.value, 6.238) # Grams

    def test___truediv__(self):
        seconds_per_hour = Ratio(
            numerator=Number(unit=units.second, quantity=3600),
            denominator=Number(unit=units.hour, quantity=1)
        )

        # How many Wh from 20 kJ?
        twenty_kilojoules = Number(unit=units.joule, scale=Scale.kilo, quantity=20)
        ratio = twenty_kilojoules.as_ratio() / seconds_per_hour
        answer = ratio.evaluate()
        self.assertEqual(answer.unit.dimension, Dimension.energy)
        self.assertEqual(round(answer.value, 5), 5.55556)  # Watt * hours

    def test___eq__(self):
        self.assertEqual(self.one_half, self.point_five)
        with self.assertRaises(ValueError):
            self.one_half == 1/2

    def test___repr__(self):
        self.assertEqual(str(self.one_ratio), '<1.0 >')
        self.assertEqual(str(self.two_ratio), '<2 > / <1 >')
        self.assertEqual(str(self.two_ratio.evaluate()), '<2.0 >')
