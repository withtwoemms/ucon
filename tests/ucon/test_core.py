import math
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
    kibibyte = Exponent(2, 10)
    mebibyte = Exponent(2, 20)

    def test___init__(self):
        with self.assertRaises(ValueError):
            Exponent(5, 3)  # no support for base 5 logarithms

    def test_parts(self):
        self.assertEqual((10, 3), self.thousand.parts())
        self.assertEqual((10, -3), self.thousandth.parts())

    def test_evaluated_property(self):
        self.assertEqual(1000, self.thousand.evaluated)
        self.assertAlmostEqual(0.001, self.thousandth.evaluated)
        self.assertEqual(1024, self.kibibyte.evaluated)
        self.assertEqual(1048576, self.mebibyte.evaluated)

    def test___truediv__(self):
         # same base returns a new Exponent
        ratio = self.thousand / self.thousandth
        self.assertIsInstance(ratio, Exponent)
        self.assertEqual(ratio.base, 10)
        self.assertEqual(ratio.power, 6)
        self.assertEqual(ratio.evaluated, 1_000_000)

        # different base returns numeric float
        val = self.thousand / self.kibibyte
        self.assertIsInstance(val, float)
        self.assertAlmostEqual(1000 / 1024, val)

    def test___mul__(self):
        product = self.kibibyte * self.mebibyte
        self.assertIsInstance(product, Exponent)
        self.assertEqual(product.base, 2)
        self.assertEqual(product.power, 30)
        self.assertEqual(product.evaluated, 2**30)

        # cross-base multiplication returns numeric
        val = self.kibibyte * self.thousand
        self.assertIsInstance(val, float)
        self.assertAlmostEqual(1024 * 1000, val)

    def test___hash__(self):
        a = Exponent(10, 3)
        b = Exponent(10, 3)
        self.assertEqual(hash(a), hash(b))
        self.assertEqual(len({a, b}), 1) # both should hash to same value

    def test___float__(self):
        self.assertEqual(float(self.thousand), 1000.0)

    def test___int__(self):
        self.assertEqual(int(self.thousand), 1000)

    def test_comparisons(self):
        self.assertTrue(self.thousand > self.thousandth)
        self.assertTrue(self.thousandth < self.thousand)
        self.assertTrue(self.kibibyte < self.mebibyte)
        self.assertTrue(self.kibibyte == Exponent(2, 10))

        with self.assertRaises(TypeError):
            _ = self.thousand == 1000  # comparison to non-Exponent

    def test___repr__(self):
        self.assertIn("Exponent", repr(Exponent(10, -3)))

    def test___str__(self):
        self.assertEqual(str(self.thousand), '10^3')
        self.assertEqual(str(self.thousandth), '10^-3')

    def test_to_base(self):
        e = Exponent(2, 10)
        converted = e.to_base(10)
        self.assertIsInstance(converted, Exponent)
        self.assertEqual(converted.base, 10)
        self.assertAlmostEqual(converted.power, math.log10(1024), places=10)

        with self.assertRaises(ValueError):
            e.to_base(5)


class TestScale(TestCase):

    def test___truediv__(self):
        self.assertEqual(Scale.deca, Scale.one / Scale.deci)
        self.assertEqual(Scale.deci, Scale.one / Scale.deca)
        self.assertEqual(Scale.kibi, Scale.mebi / Scale.kibi)
        self.assertEqual(Scale.milli, Scale.one / Scale.deca / Scale.deca / Scale.deca)
        self.assertEqual(Scale.deca, Scale.kilo / Scale.hecto)
        self.assertEqual(Scale._kibi, Scale.one / Scale.kibi)
        self.assertEqual(Scale.kibi, Scale.kibi / Scale.one)
        self.assertEqual(Scale.one, Scale.one / Scale.one)
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


class TestScaleDivisionAdditional(TestCase):

    def test_division_same_base_large_gap(self):
        # kilo / milli = mega
        self.assertEqual(Scale.kilo / Scale.milli, Scale.mega)
        # milli / kilo = micro
        self.assertEqual(Scale.milli / Scale.kilo, Scale.micro)

    def test_division_cross_base_scales(self):
        # Decimal vs binary cross-base — should return nearest matching scale
        result = Scale.kilo / Scale.kibi
        self.assertIsInstance(result, Scale)
        # They’re roughly equal, so nearest should be Scale.one
        self.assertEqual(result, Scale.one)

    def test_division_binary_inverse_scales(self):
        self.assertEqual(Scale.kibi / Scale.kibi, Scale.one)
        self.assertEqual(Scale.kibi / Scale.mebi, Scale._kibi)
        self.assertEqual(Scale.mebi / Scale.kibi, Scale.kibi)

    def test_division_unmatched_returns_nearest(self):
        # giga / kibi is a weird combo → nearest mega or similar
        result = Scale.giga / Scale.kibi
        self.assertIsInstance(result, Scale)
        self.assertIn(result, Scale)

    def test_division_type_safety(self):
        # Ensure non-Scale raises NotImplemented
        with self.assertRaises(TypeError):
            Scale.kilo / 42


class TestScaleNearestAdditional(TestCase):

    def test_nearest_handles_zero(self):
        self.assertEqual(Scale.nearest(0), Scale.one)

    def test_nearest_handles_negative_values(self):
        # Only magnitude matters, not sign
        self.assertEqual(Scale.nearest(-1000), Scale.kilo)
        self.assertEqual(Scale.nearest(-0.001), Scale.milli)

    def test_nearest_with_undershoot_bias_effect(self):
        # Lower bias should make undershoot (ratios < 1) less penalized
        # This test ensures the bias argument doesn’t break ordering
        s_default = Scale.nearest(50_000, undershoot_bias=0.75)
        s_stronger_bias = Scale.nearest(50_000, undershoot_bias=0.9)
        # The result shouldn't flip to something wildly different
        self.assertIn(s_default, [Scale.kilo, Scale.mega])
        self.assertIn(s_stronger_bias, [Scale.kilo, Scale.mega])

    def test_nearest_respects_binary_preference_flag(self):
        # Confirm that enabling binary changes candidate set
        decimal_result = Scale.nearest(2**10)
        binary_result = Scale.nearest(2**10, include_binary=True)
        self.assertNotEqual(decimal_result, binary_result)
        self.assertEqual(binary_result, Scale.kibi)

    def test_nearest_upper_and_lower_extremes(self):
        self.assertEqual(Scale.nearest(10**9), Scale.giga)
        self.assertEqual(Scale.nearest(10**-9), Scale.nano)


class TestScaleInternals(TestCase):

    def test_decimal_and_binary_sets_are_disjoint(self):
        decimal_bases = {s.value.base for s in Scale._decimal_scales()}
        binary_bases = {s.value.base for s in Scale._binary_scales()}
        self.assertNotEqual(decimal_bases, binary_bases)
        self.assertEqual(decimal_bases, {10})
        self.assertEqual(binary_bases, {2})

    def test_all_and_by_value_consistency(self):
        mapping = Scale.all()
        value_map = Scale.by_value()
        # Each value’s evaluated form should appear in by_value keys
        for (base, power), name in mapping.items():
            val = Scale[name].value.evaluated
            self.assertIn(round(val, 15), value_map)

    def test_all_and_by_value_are_cached(self):
        # Call multiple times and ensure they’re same object (cached)
        self.assertIs(Scale.all(), Scale.all())
        self.assertIs(Scale.by_value(), Scale.by_value())


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

    def test_extreme_powers(self):
        e = Exponent(10, 308)
        self.assertTrue(math.isfinite(e.evaluated))
        e_small = Exponent(10, -308)
        self.assertGreater(e.evaluated, e_small.evaluated)

    def test_precision_rounding_in_hash(self):
        a = Exponent(10, 6)
        b = Exponent(10, 6 + 1e-16)
        # rounding in hash avoids floating drift
        self.assertEqual(hash(a), hash(b))

    def test_negative_and_zero_power(self):
        e0 = Exponent(10, 0)
        e_neg = Exponent(10, -1)
        self.assertEqual(e0.evaluated, 1.0)
        self.assertEqual(e_neg.evaluated, 0.1)
        self.assertLess(e_neg, e0)

    def test_valid_exponent_evaluates_correctly(self):
        base, power = 10, 3
        e = Exponent(base, power)
        self.assertEqual(e.evaluated, 1000)
        self.assertEqual(e.parts(), (base, power))
        self.assertEqual(f'{base}^{power}', str(e))
        self.assertEqual(f'Exponent(base={base}, power={power})', repr(e))

    def test_invalid_base_raises_value_error(self):
        with self.assertRaises(ValueError):
            Exponent(5, 2)

    def test_exponent_comparisons(self):
        e1 = Exponent(10, 2)
        e2 = Exponent(10, 3)
        self.assertTrue(e1 < e2)
        self.assertTrue(e2 > e1)
        self.assertFalse(e1 == e2)

    def test_division_returns_exponent(self):
        e1 = Exponent(10, 3)
        e2 = Exponent(10, 2)
        self.assertEqual(e1 / e2, Exponent(10, 1))

    def test_equality_with_different_type(self):
        with self.assertRaises(TypeError):
            Exponent(10, 2) == "10^2"


class TestScaleEdgeCases(TestCase):

    def test_nearest_prefers_decimal_by_default(self):
        self.assertEqual(Scale.nearest(1024), Scale.kilo)
        self.assertEqual(Scale.nearest(50_000), Scale.kilo)
        self.assertEqual(Scale.nearest(1/1024), Scale.milli)

    def test_nearest_includes_binary_when_opted_in(self):
        self.assertEqual(Scale.nearest(1/1024, include_binary=True), Scale._kibi)
        self.assertEqual(Scale.nearest(1024, include_binary=True), Scale.kibi)
        self.assertEqual(Scale.nearest(50_000, include_binary=True), Scale.kibi)
        self.assertEqual(Scale.nearest(2**20, include_binary=True), Scale.mebi)

    def test_nearest_subunit_behavior(self):
        self.assertEqual(Scale.nearest(0.0009), Scale.milli)
        self.assertEqual(Scale.nearest(1e-7), Scale.micro)

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
