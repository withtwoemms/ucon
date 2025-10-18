from unittest import TestCase

from ucon import Number
from ucon import Exponent
from ucon import Ratio
from ucon import Scale
from ucon import Dimension
from ucon import units
from ucon.unit import Unit


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


class TestExponentEdgeCases(TestCase):

    def test_valid_exponent_evaluates_correctly(self):
        e = Exponent(10, 3)
        self.assertEqual(e.evaluated, 1000)
        self.assertEqual(e.parts(), (10, 3))
        self.assertIn("^", repr(e))

    def test_invalid_base_raises_value_error(self):
        with self.assertRaises(ValueError):
            Exponent(5, 2)

    def test_exponent_comparisons(self):
        e1 = Exponent(10, 2)
        e2 = Exponent(10, 3)
        self.assertTrue(e1 < e2)
        self.assertTrue(e2 > e1)
        self.assertFalse(e1 == e2)

    def test_division_returns_float_ratio(self):
        e1 = Exponent(10, 3)
        e2 = Exponent(10, 2)
        self.assertEqual(e1 / e2, 10.0)

    def test_equality_with_different_type(self):
        with self.assertRaises(TypeError):
            Exponent(10, 2) == "10^2"


class TestScaleEdgeCases(TestCase):

    def test_division_same_base_scales(self):
        result = Scale.kilo / Scale.milli
        self.assertIsInstance(result, Scale)
        self.assertEqual(result.value.evaluated, 10 ** 6)

    def test_division_same_scale_returns_one(self):
        self.assertEqual(Scale.kilo / Scale.kilo, Scale.one)

    def test_division_different_bases_returns_valid_scale(self):
        result = Scale.kibi / Scale.kilo
        self.assertIsInstance(result, Scale)
        self.assertIn(result, Scale)

    def test_division_with_one(self):
        result = Scale.one / Scale.kilo
        self.assertIsInstance(result, Scale)
        self.assertTrue(hasattr(result, "value"))

    def test_comparisons_and_equality(self):
        self.assertTrue(Scale.kilo > Scale.deci)
        self.assertTrue(Scale.milli < Scale.one)
        self.assertTrue(Scale.kilo == Scale.kilo)

    def test_all_and_by_value_cover_all_enum_members(self):
        all_map = Scale.all()
        by_val = Scale.by_value()
        self.assertTrue(all((val in by_val.values()) for _, val in all_map.items()))


class TestNumberEdgeCases(TestCase):

    def test_default_number_is_dimensionless_one(self):
        n = Number()
        self.assertEqual(n.unit, units.none)
        self.assertEqual(n.scale, Scale.one)
        self.assertEqual(n.quantity, 1)
        self.assertAlmostEqual(n.value, 1.0)
        self.assertIn("1", repr(n))

    def test_to_new_scale_changes_value(self):
        n = Number(quantity=1000, scale=Scale.kilo)
        converted = n.to(Scale.one)
        self.assertNotEqual(n.value, converted.value)
        self.assertAlmostEqual(converted.value, 1000)

    def test_simplify_uses_value_as_quantity(self):
        n = Number(quantity=2, scale=Scale.kilo)
        simplified = n.simplify()
        self.assertEqual(simplified.quantity, n.value)
        self.assertEqual(simplified.unit, n.unit)

    def test_multiplication_combines_units_and_quantities(self):
        n1 = Number(unit=units.joule, quantity=2)
        n2 = Number(unit=units.second, quantity=3)
        result = n1 * n2
        self.assertEqual(result.quantity, 6)
        self.assertEqual(result.unit.dimension, Dimension.energy * Dimension.time)

    def test_division_combines_units_scales_and_quantities(self):
        n1 = Number(unit=units.meter, scale=Scale.kilo, quantity=1000)
        n2 = Number(unit=units.second, scale=Scale.one, quantity=2)
        result = n1 / n2
        self.assertEqual(result.scale, Scale.kilo / Scale.one)
        self.assertEqual(result.unit.dimension, Dimension.velocity)
        self.assertAlmostEqual(result.quantity, 500)

    def test_equality_with_non_number_raises_value_error(self):
        n = Number()
        with self.assertRaises(ValueError):
            _ = (n == "5")

    def test_equality_between_numbers_and_ratios(self):
        n1 = Number(quantity=10)
        n2 = Number(quantity=10)
        r = Ratio(n1, n2)
        self.assertTrue(r == Number())

    def test_repr_includes_scale_and_unit(self):
        n = Number(unit=units.volt, scale=Scale.kilo, quantity=5)
        rep = repr(n)
        self.assertIn("kilo", rep)
        self.assertIn("volt", rep)


class TestRatioEdgeCases(TestCase):

    def test_default_ratio_is_dimensionless_one(self):
        r = Ratio()
        self.assertEqual(r.numerator.unit, units.none)
        self.assertEqual(r.denominator.unit, units.none)
        self.assertAlmostEqual(r.evaluate().value, 1.0)

    def test_reciprocal_swaps_numerator_and_denominator(self):
        n1 = Number(quantity=10)
        n2 = Number(quantity=2)
        r = Ratio(n1, n2)
        reciprocal = r.reciprocal()
        self.assertEqual(reciprocal.numerator, r.denominator)
        self.assertEqual(reciprocal.denominator, r.numerator)

    def test_evaluate_returns_number_division_result(self):
        r = Ratio(Number(unit=units.meter), Number(unit=units.second))
        result = r.evaluate()
        self.assertIsInstance(result, Number)
        self.assertEqual(result.unit.dimension, Dimension.velocity)

    def test_multiplication_between_compatible_ratios(self):
        r1 = Ratio(Number(unit=units.meter), Number(unit=units.second))
        r2 = Ratio(Number(unit=units.second), Number(unit=units.meter))
        product = r1 * r2
        self.assertIsInstance(product, Ratio)
        self.assertEqual(product.evaluate().unit.dimension, Dimension.none)

    def test_multiplication_with_incompatible_units_fallback(self):
        r1 = Ratio(Number(unit=units.meter), Number(unit=units.ampere))
        r2 = Ratio(Number(unit=units.ampere), Number(unit=units.meter))
        result = r1 * r2
        self.assertIsInstance(result, Ratio)

    def test_division_between_ratios_yields_new_ratio(self):
        r1 = Ratio(Number(quantity=2), Number(quantity=1))
        r2 = Ratio(Number(quantity=4), Number(quantity=2))
        result = r1 / r2
        self.assertIsInstance(result, Ratio)
        self.assertAlmostEqual(result.evaluate().value, 1.0)

    def test_equality_with_non_ratio_raises_value_error(self):
        r = Ratio()
        with self.assertRaises(ValueError):
            _ = (r == "not_a_ratio")

    def test_repr_handles_equal_numerator_denominator(self):
        r = Ratio()
        self.assertEqual(str(r.evaluate().value), "1.0")
        rep = repr(r)
        self.assertTrue(rep.startswith("<1"))

    def test_repr_of_non_equal_ratio_includes_slash(self):
        n1 = Number(quantity=2)
        n2 = Number(quantity=1)
        r = Ratio(n1, n2)
        rep = repr(r)
        self.assertIn("/", rep)
