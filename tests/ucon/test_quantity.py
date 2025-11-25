

import unittest

from ucon import units
from ucon.core import CompositeUnit, Dimension, Scale, Unit
from ucon.quantity import Number, Ratio


class TestNumber(unittest.TestCase):

    number = Number(unit=units.gram, quantity=1)

    def test_as_ratio(self):
        ratio = self.number.as_ratio()
        self.assertIsInstance(ratio, Ratio)
        self.assertEqual(ratio.numerator, self.number)
        self.assertEqual(ratio.denominator, Number())

    @unittest.skip("Requires ConversionGraph implementation")
    def test_simplify(self):
        decagram = Unit(dimension=Dimension.mass, name='gram', scale=Scale.deca)
        kibigram = Unit(dimension=Dimension.mass, name='gram', scale=Scale.kibi)

        ten_decagrams = Number(unit=decagram, quantity=10)
        point_one_decagrams = Number(unit=decagram, quantity=0.1)
        two_kibigrams = Number(unit=kibigram, quantity=2)

        self.assertEqual(Number(unit=units.gram, quantity=100), ten_decagrams.simplify())
        self.assertEqual(Number(unit=units.gram, quantity=1), point_one_decagrams.simplify())
        self.assertEqual(Number(unit=units.gram, quantity=2048), two_kibigrams.simplify())

    @unittest.skip("Requires ConversionGraph implementation")
    def test_to(self):
        kg = Unit(dimension=Dimension.mass, name='gram', scale=Scale.kilo)
        mg = Unit(dimension=Dimension.mass, name='gram', scale=Scale.milli)
        kibigram = Unit(dimension=Dimension.mass, name='gram', scale=Scale.kibi)

        thousandth_of_a_kilogram = Number(unit=kg, quantity=0.001)
        thousand_milligrams = Number(unit=mg, quantity=1000)
        kibigram_fraction = Number(unit=kibigram, quantity=0.0009765625)

        self.assertEqual(thousandth_of_a_kilogram, self.number.to(Scale.kilo))
        self.assertEqual(thousand_milligrams, self.number.to(Scale.milli))
        self.assertEqual(kibigram_fraction, self.number.to(Scale.kibi))

    def test___repr__(self):
        self.assertIn(str(self.number.quantity), str(self.number))
        self.assertIn(str(self.number.unit.scale.value.evaluated), str(self.number))
        self.assertIn(self.number.unit.shorthand, str(self.number))

    def test___truediv__(self):
        dal = Scale.deca * units.gram
        mg = Scale.milli * units.gram
        kibigram = Scale.kibi * units.gram

        some_number = Number(unit=dal, quantity=10)
        another_number = Number(unit=mg, quantity=10)
        that_number = Number(unit=kibigram, quantity=10)

        some_quotient = self.number / some_number
        another_quotient = self.number / another_number
        that_quotient = self.number / that_number

        self.assertEqual(some_quotient.value, 0.01)
        self.assertEqual(another_quotient.value, 100.0)
        self.assertEqual(that_quotient.value, 0.00009765625)

    def test___eq__(self):
        self.assertEqual(self.number, Ratio(self.number))  # 1 gram / 1
        with self.assertRaises(TypeError):
            self.number == 1


class TestNumberEdgeCases(unittest.TestCase):

    def test_density_times_volume_preserves_user_scale(self):
        mL = Scale.milli * units.liter
        density = Ratio(Number(unit=units.gram, quantity=3.119),
                        Number(unit=mL, quantity=1))
        two_mL = Number(unit=mL, quantity=2)

        result = density.evaluate() * two_mL
        self.assertIsInstance(result.unit, CompositeUnit)
        self.assertDictEqual(result.unit.components, {units.gram: 1})
        self.assertAlmostEqual(result.quantity, 6.238, places=12)

    @unittest.skip("Recativate when Unit factorization possible.")
    def test_number_mul_asymmetric_density_volume(self):
        g = units.gram
        mL = Scale.milli * units.liter

        density = Number(unit=g, quantity=3.119) / Number(unit=mL, quantity=1)
        two_mL = Number(unit=mL, quantity=2)

        result = density * two_mL

        assert result.unit == g
        assert abs(result.quantity - 6.238) < 1e-12

    @unittest.skip("Recativate when Unit factorization possible.")
    def test_number_mul_retains_scale_when_scaling_lengths(self):
        km = Scale.kilo * units.meter
        m = units.meter

        n1 = Number(unit=km, quantity=2)   # 2 km
        n2 = Number(unit=m, quantity=500)  # 500 m

        result = n1 * n2

        assert result.unit.dimension == Dimension.area
        # scale stays on unit expression, not folded into numeric
        assert "km" in result.unit.shorthand or "m" in result.unit.shorthand

    @unittest.skip("Recativate when Unit factorization possible.")
    def test_number_mul_mixed_scales_do_not_auto_cancel(self):
        km = Scale.kilo * units.meter
        m = units.meter

        result = Number(unit=km, quantity=1) * Number(unit=m, quantity=1)

        # Should remain composite rather than collapsing to base m^2
        assert isinstance(result.unit, CompositeUnit)
        assert "km" in result.unit.shorthand
        assert "m" in result.unit.shorthand

    @unittest.skip("Recativate when Unit factorization possible.")
    def test_number_div_uses_canonical_rhs_value(self):
        dal = Scale.deca * units.gram   # 10 g
        n = Number(unit=units.gram, quantity=1)

        quotient = n / Number(unit=dal, quantity=10)

        # 1 g / (10 × 10 g) = 0.01
        assert abs(quotient.value - 0.01) < 1e-12

    @unittest.skip("Recativate when Unit factorization possible.")
    def test_ratio_times_number_preserves_user_scale(self):
        mL = Scale.milli * units.liter
        density = Ratio(Number(unit=units.gram, quantity=3.119),
                        Number(unit=mL, quantity=1))
        two_mL = Number(unit=mL, quantity=2)

        result = density * two_mL.as_ratio()
        evaluated = result.evaluate()

        assert evaluated.unit == units.gram
        assert abs(evaluated.quantity - 6.238) < 1e-12

    @unittest.skip("Recativate when Unit factorization possible.")
    def test_number_mul_repeated_scale_interactions_stable(self):
        mL = Scale.milli * units.liter
        density = Number(unit=units.gram, quantity=3.119) / Number(unit=mL, quantity=1)

        n = Number(unit=mL, quantity=2)
        result = density * n

        # Apply density twice
        result2 = density * Number(unit=mL, quantity=result.quantity)

        assert abs(result.quantity - 6.238) < 1e-12
        assert abs(result2.quantity - 6.238) < 1e-12

    def test_default_number_is_dimensionless_one(self):
        n = Number()
        self.assertEqual(n.unit, units.none)
        self.assertEqual(n.unit.scale, Scale.one)
        self.assertEqual(n.quantity, 1)
        self.assertAlmostEqual(n.value, 1.0)
        self.assertIn("1", repr(n))

    @unittest.skip("Requires ConversionGraph implementation")
    def test_to_new_scale_changes_value(self):
        thousand = Unit(dimension=Dimension.none, name='', scale=Scale.kilo)
        n = Number(quantity=1000, unit=thousand)
        converted = n.to(Scale.one)
        self.assertNotEqual(n.value, converted.value)
        self.assertAlmostEqual(converted.value, 1000)

    @unittest.skip("Requires ConversionGraph implementation")
    def test_simplify_uses_value_as_quantity(self):
        thousand = Unit(dimension=Dimension.none, name='', scale=Scale.kilo)
        n = Number(quantity=2, unit=thousand)
        simplified = n.simplify()
        self.assertEqual(simplified.quantity, n.value)
        self.assertNotEqual(simplified.unit.scale, n.unit.scale)
        self.assertEqual(simplified.value, n.value)

    def test_multiplication_combines_units_and_quantities(self):
        n1 = Number(unit=units.joule, quantity=2)
        n2 = Number(unit=units.second, quantity=3)
        result = n1 * n2
        self.assertEqual(result.quantity, 6)
        self.assertEqual(result.unit.dimension, Dimension.energy * Dimension.time)

    @unittest.skip("Requires ConversionGraph implementation")
    def test_division_combines_units_scales_and_quantities(self):
        km = Unit('m', name='meter', dimension=Dimension.length, scale=Scale.kilo)
        n1 = Number(unit=km, quantity=1000)
        n2 = Number(unit=units.second, quantity=2)

        result = n1 / n2     # should yield <500 km/s>

        cu = result.unit
        self.assertIsInstance(cu, CompositeUnit)

        # --- quantity check ---
        self.assertAlmostEqual(result.quantity, 500)

        # --- dimension check ---
        self.assertEqual(cu.dimension, Dimension.velocity)

        # --- scale check: km/s should have a kilo-scaled meter in the numerator ---
        # find the meter-like unit in the components
        meter_like = next(u for u, exp in cu.components.items() if u.dimension == Dimension.length)
        self.assertEqual(meter_like.scale, Scale.kilo)
        self.assertEqual(cu.components[meter_like], 1)  # exponent = 1 in numerator

        # --- symbolic shorthand ---
        self.assertEqual(cu.shorthand, "km/s")

        # --- optional canonicalization ---
        canonical = result.to(Scale.one)
        self.assertAlmostEqual(canonical.quantity, 500000)
        self.assertEqual(canonical.unit.shorthand, "m/s")

    def test_equality_with_non_number_raises_value_error(self):
        n = Number()
        with self.assertRaises(TypeError):
            n == '5'

    def test_equality_between_numbers_and_ratios(self):
        n1 = Number(quantity=10)
        n2 = Number(quantity=10)
        r = Ratio(n1, n2)
        self.assertTrue(r == Number())

    def test_repr_includes_scale_and_unit(self):
        kV = Unit('V', name='volt', dimension=Dimension.voltage, scale=Scale.kilo)
        n = Number(unit=kV, quantity=5)
        rep = repr(n)
        self.assertIn("kV", rep)


class TestRatio(unittest.TestCase):

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
        mL = Unit('L', name='liter', dimension=Dimension.volume, scale=Scale.milli)
        n1 = Number(unit=units.gram, quantity=3.119)
        n2 = Number(unit=mL)
        bromine_density = Ratio(n1, n2)
    
        # How many grams of bromine are in 2 milliliters?
        two_milliliters_bromine = Number(unit=mL, quantity=2)
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
        twenty_kilojoules = Number(
            unit=Unit('J', name='joule', dimension=Dimension.energy, scale=Scale.kilo),
            quantity=20
        )
        ratio = twenty_kilojoules.as_ratio() / seconds_per_hour
        answer = ratio.evaluate()
        self.assertEqual(answer.unit.dimension, Dimension.energy)
        # When the ConversionGraph is implemented, conversion to watt-hours will be possible.
        self.assertEqual(round(answer.value, 5), 0.00556)  # kilowatt * hours

    def test___eq__(self):
        self.assertEqual(self.one_half, self.point_five)
        with self.assertRaises(ValueError):
            self.one_half == 1/2

    def test___repr__(self):
        self.assertEqual(str(self.one_ratio), '<1.0>')
        self.assertEqual(str(self.two_ratio), '<2> / <1.0>')
        self.assertEqual(str(self.two_ratio.evaluate()), '<2.0>')


class TestRatioEdgeCases(unittest.TestCase):

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
