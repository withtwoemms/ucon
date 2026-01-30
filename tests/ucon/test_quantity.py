# © 2025 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

import unittest

from ucon import units
from ucon.core import UnitProduct, UnitFactor, Dimension, Scale, Unit
from ucon.quantity import Number, Ratio


class TestNumber(unittest.TestCase):

    number = Number(unit=units.gram, quantity=1)

    def test_as_ratio(self):
        ratio = self.number.as_ratio()
        self.assertIsInstance(ratio, Ratio)
        self.assertEqual(ratio.numerator, self.number)
        self.assertEqual(ratio.denominator, Number())

    def test_simplify_scaled_unit(self):
        """Test simplify() removes scale prefix and adjusts quantity."""
        decagram = Scale.deca * units.gram
        ten_decagrams = Number(unit=decagram, quantity=10)
        result = ten_decagrams.simplify()
        # 10 decagrams = 100 grams
        self.assertAlmostEqual(result.quantity, 100.0, places=10)
        # Unit should be base gram (Scale.one)
        self.assertEqual(result.unit.shorthand, "g")

    def test_to_converts_between_units(self):
        """Test Number.to() converts between compatible units."""
        # 1 gram to kilogram
        kg = Scale.kilo * units.gram
        result = self.number.to(kg)
        self.assertAlmostEqual(result.quantity, 0.001, places=10)

        # 1 gram to milligram
        mg = Scale.milli * units.gram
        result = self.number.to(mg)
        self.assertAlmostEqual(result.quantity, 1000.0, places=10)

        # 1 kilogram to gram
        one_kg = Number(unit=kg, quantity=1)
        result = one_kg.to(units.gram)
        self.assertAlmostEqual(result.quantity, 1000.0, places=10)

    def test___repr__(self):
        """Test Number repr contains quantity and unit shorthand."""
        repr_str = repr(self.number)
        self.assertIn(str(self.number.quantity), repr_str)
        self.assertIn(self.number.unit.shorthand, repr_str)

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
        self.assertIsInstance(result.unit, UnitProduct)
        self.assertDictEqual(result.unit.factors, {units.gram: 1})
        self.assertAlmostEqual(result.quantity, 6.238, places=12)

        mg = Scale.milli * units.gram
        mg_factor = UnitFactor(unit=units.gram, scale=Scale.milli)
        mg_density = Ratio(Number(unit=mg, quantity=3119), Number(unit=mL, quantity=1))

        mg_result = mg_density.evaluate() * two_mL
        self.assertIsInstance(mg_result.unit, UnitProduct)
        self.assertDictEqual(mg_result.unit.factors, {mg_factor: 1})
        self.assertAlmostEqual(mg_result.quantity, 6238, places=12)

    def test_number_mul_asymmetric_density_volume(self):
        g = units.gram
        mL = Scale.milli * units.liter

        density = Number(unit=g, quantity=3.119) / Number(unit=mL, quantity=1)
        two_mL = Number(unit=mL, quantity=2)

        result = density * two_mL

        assert result.unit == g
        assert abs(result.quantity - 6.238) < 1e-12

    def test_number_mul_retains_scale_when_scaling_lengths(self):
        km = Scale.kilo * units.meter
        m = units.meter

        n1 = Number(unit=km, quantity=2)   # 2 km
        n2 = Number(unit=m, quantity=500)  # 500 m

        result = n1 * n2

        assert result.unit.dimension == Dimension.area
        # scale stays on unit expression, not folded into numeric
        assert "km" in result.unit.shorthand or "m" in result.unit.shorthand

    def test_number_mul_mixed_scales_do_not_auto_cancel(self):
        km = Scale.kilo * units.meter
        m = units.meter

        result = Number(unit=km, quantity=1) * Number(unit=m, quantity=1)

        # Should remain composite rather than collapsing to base m^2
        assert isinstance(result.unit, UnitProduct)
        assert "km" in result.unit.shorthand
        assert "m" in result.unit.shorthand

    def test_number_div_uses_canonical_rhs_value(self):
        dal = Scale.deca * units.gram   # 10 g
        n = Number(unit=units.gram, quantity=1)

        quotient = n / Number(unit=dal, quantity=10)

        # 1 g / (10 × 10 g) = 0.01
        assert abs(quotient.value - 0.01) < 1e-12

    def test_ratio_times_number_preserves_user_scale(self):
        mL = Scale.milli * units.liter
        density = Ratio(Number(unit=units.gram, quantity=3.119),
                        Number(unit=mL, quantity=1))
        two_mL = Number(unit=mL, quantity=2)

        result = density * two_mL.as_ratio()
        evaluated = result.evaluate()

        assert evaluated.unit == units.gram
        assert abs(evaluated.quantity - 6.238) < 1e-12

    def test_default_number_is_dimensionless_one(self):
        """Default Number() is dimensionless with quantity=1."""
        n = Number()
        self.assertEqual(n.unit, units.none)
        self.assertEqual(n.quantity, 1)
        self.assertAlmostEqual(n.value, 1.0)
        self.assertIn("1", repr(n))

    def test_to_different_scale_changes_quantity(self):
        """Converting to a different scale changes the quantity."""
        km = Scale.kilo * units.meter
        n = Number(quantity=5, unit=km)  # 5 km
        converted = n.to(units.meter)    # convert to meters
        # quantity changes: 5 km = 5000 m
        self.assertNotEqual(n.quantity, converted.quantity)
        self.assertAlmostEqual(converted.quantity, 5000.0, places=10)

    def test_simplify_uses_value_as_quantity(self):
        """Simplify converts scaled quantity to base scale quantity."""
        km = Scale.kilo * units.meter
        n = Number(quantity=2, unit=km)  # 2 km
        simplified = n.simplify()
        # simplified.quantity should be the canonical magnitude (2 * 1000 = 2000)
        self.assertAlmostEqual(simplified.quantity, 2000.0, places=10)
        # canonical magnitude (physical quantity) is preserved
        self.assertAlmostEqual(simplified._canonical_magnitude, n._canonical_magnitude, places=10)

    def test_multiplication_combines_units_and_quantities(self):
        n1 = Number(unit=units.joule, quantity=2)
        n2 = Number(unit=units.second, quantity=3)
        result = n1 * n2
        self.assertEqual(result.quantity, 6)
        self.assertEqual(result.unit.dimension, Dimension.energy * Dimension.time)

    def test_division_combines_units_scales_and_quantities(self):
        """Division creates composite unit with preserved scales."""
        km = Scale.kilo * units.meter
        n1 = Number(unit=km, quantity=1000)  # 1000 km
        n2 = Number(unit=units.second, quantity=2)

        result = n1 / n2  # should yield <500 km/s>

        cu = result.unit
        self.assertIsInstance(cu, UnitProduct)

        # --- quantity check ---
        self.assertAlmostEqual(result.quantity, 500)

        # --- dimension check ---
        self.assertEqual(cu.dimension, Dimension.velocity)

        # --- symbolic shorthand ---
        self.assertEqual(cu.shorthand, "km/s")

        # --- convert to base units (m/s) ---
        m_per_s = units.meter / units.second
        canonical = result.to(m_per_s)
        self.assertAlmostEqual(canonical.quantity, 500000, places=5)
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
        kV = Scale.kilo * Unit(name='volt', dimension=Dimension.voltage, aliases=('V',))
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
        mL = Scale.milli * Unit(name='liter', dimension=Dimension.volume, aliases=('L',))
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
            unit=Scale.kilo * Unit(name='joule', dimension=Dimension.energy, aliases=('J',)),
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


class TestRatioExponentScaling(unittest.TestCase):
    """Tests for Ratio.evaluate() using Exponent-based scaling.

    Ensures Ratio.evaluate() behaves consistently with Number.__truediv__
    when units cancel to dimensionless results.
    """

    def test_evaluate_dimensionless_with_different_scales(self):
        """Ratio of same unit with different scales should fold scales."""
        kg = Scale.kilo * units.gram
        # 500 g / 1 kg = 0.5 (dimensionless)
        ratio = Ratio(units.gram(500), kg(1))
        result = ratio.evaluate()
        self.assertAlmostEqual(result.quantity, 0.5, places=10)
        self.assertEqual(result.unit.dimension, Dimension.none)

    def test_evaluate_matches_number_truediv(self):
        """Ratio.evaluate() should match Number.__truediv__ for dimensionless."""
        kg = Scale.kilo * units.gram
        num = units.gram(500)
        den = kg(1)

        ratio_result = Ratio(num, den).evaluate()
        truediv_result = num / den

        self.assertAlmostEqual(ratio_result.quantity, truediv_result.quantity, places=10)
        self.assertEqual(ratio_result.unit.dimension, truediv_result.unit.dimension)

    def test_evaluate_cross_base_scaling(self):
        """Binary and decimal prefixes should combine correctly."""
        kibigram = Scale.kibi * units.gram  # 1024 g
        kg = Scale.kilo * units.gram         # 1000 g
        # 1 kibigram / 1 kg = 1024/1000 = 1.024
        ratio = Ratio(kibigram(1), kg(1))
        result = ratio.evaluate()
        self.assertAlmostEqual(result.quantity, 1.024, places=10)
        self.assertEqual(result.unit.dimension, Dimension.none)

    def test_evaluate_dimensionful_preserves_scales(self):
        """Non-cancelling units should preserve symbolic scales."""
        km = Scale.kilo * units.meter
        # 100 km / 2 h = 50 km/h (scales preserved, not folded)
        ratio = Ratio(km(100), units.hour(2))
        result = ratio.evaluate()
        self.assertAlmostEqual(result.quantity, 50.0, places=10)
        self.assertEqual(result.unit.dimension, Dimension.velocity)
        self.assertIn("km", result.unit.shorthand)

    def test_evaluate_complex_composition(self):
        """Composed ratios should maintain scale semantics."""
        mL = Scale.milli * units.liter
        # Density: 3.119 g/mL
        density = Ratio(units.gram(3.119), mL(1))
        # Volume: 2 mL
        volume = Ratio(mL(2), Number())
        # Mass = density * volume
        result = (density * volume).evaluate()
        self.assertAlmostEqual(result.quantity, 6.238, places=3)


class TestCallableUnits(unittest.TestCase):
    """Tests for the callable unit syntax: unit(quantity) -> Number."""

    def test_unit_callable_returns_number(self):
        result = units.meter(5)
        self.assertIsInstance(result, Number)
        self.assertEqual(result.quantity, 5)

    def test_unit_callable_shorthand(self):
        result = units.meter(5)
        self.assertIn("m", result.unit.shorthand)

    def test_unit_product_callable_returns_number(self):
        velocity = units.meter / units.second
        result = velocity(10)
        self.assertIsInstance(result, Number)
        self.assertEqual(result.quantity, 10)
        self.assertEqual(result.unit.dimension, Dimension.velocity)

    def test_scaled_unit_callable_returns_number(self):
        km = Scale.kilo * units.meter
        result = km(5)
        self.assertIsInstance(result, Number)
        self.assertEqual(result.quantity, 5)
        self.assertIn("km", result.unit.shorthand)

    def test_composite_scaled_unit_callable(self):
        mph = units.mile / units.hour
        result = mph(60)
        self.assertIsInstance(result, Number)
        self.assertEqual(result.quantity, 60)


class TestScaledUnitConversion(unittest.TestCase):
    """Tests for conversions involving scaled units.

    Regression tests for bug where scale was applied twice during conversion.
    """

    def test_km_to_mile_conversion(self):
        """5 km should be approximately 3.10686 miles."""
        km = Scale.kilo * units.meter
        result = km(5).to(units.mile)
        # 5 km = 5000 m = 5000 / 1609.34 miles ≈ 3.10686
        self.assertAlmostEqual(result.quantity, 3.10686, places=4)

    def test_km_to_meter_conversion(self):
        """1 km should be 1000 meters."""
        km = Scale.kilo * units.meter
        result = km(1).to(units.meter)
        self.assertAlmostEqual(result.quantity, 1000.0, places=6)

    def test_meter_to_mm_conversion(self):
        """1 meter should be 1000 millimeters."""
        mm = Scale.milli * units.meter
        result = units.meter(1).to(mm)
        self.assertAlmostEqual(result.quantity, 1000.0, places=6)

    def test_mm_to_inch_conversion(self):
        """25.4 mm should be approximately 1 inch."""
        mm = Scale.milli * units.meter
        result = mm(25.4).to(units.inch)
        self.assertAlmostEqual(result.quantity, 1.0, places=4)

    def test_scaled_velocity_conversion(self):
        """1 km/h should be approximately 0.27778 m/s."""
        km_per_h = (Scale.kilo * units.meter) / units.hour
        m_per_s = units.meter / units.second
        result = km_per_h(1).to(m_per_s)
        # 1 km/h = 1000m / 3600s = 0.27778 m/s
        self.assertAlmostEqual(result.quantity, 0.27778, places=4)

    def test_mph_to_m_per_s_conversion(self):
        """60 mph should be approximately 26.8224 m/s."""
        mph = units.mile / units.hour
        m_per_s = units.meter / units.second
        result = mph(60).to(m_per_s)
        # 60 mph = 60 * 1609.34 / 3600 m/s ≈ 26.8224
        self.assertAlmostEqual(result.quantity, 26.8224, places=2)


class TestNumberSimplify(unittest.TestCase):
    """Tests for Number.simplify() method."""

    def test_simplify_kilo_prefix(self):
        """5 km simplifies to 5000 m."""
        km = Scale.kilo * units.meter
        result = km(5).simplify()
        self.assertAlmostEqual(result.quantity, 5000.0, places=10)
        self.assertEqual(result.unit.shorthand, "m")

    def test_simplify_milli_prefix(self):
        """500 mg simplifies to 0.5 g."""
        mg = Scale.milli * units.gram
        result = mg(500).simplify()
        self.assertAlmostEqual(result.quantity, 0.5, places=10)
        self.assertEqual(result.unit.shorthand, "g")

    def test_simplify_binary_prefix(self):
        """2 kibibytes simplifies to 2048 bytes."""
        kibibyte = Scale.kibi * units.byte
        result = kibibyte(2).simplify()
        self.assertAlmostEqual(result.quantity, 2048.0, places=10)
        self.assertEqual(result.unit.shorthand, "B")

    def test_simplify_composite_unit(self):
        """1 km/h simplifies to base scales."""
        km_per_h = (Scale.kilo * units.meter) / units.hour
        result = km_per_h(1).simplify()
        # 1 km/h = 1000 m / 1 h (hour stays hour since it's base unit)
        self.assertAlmostEqual(result.quantity, 1000.0, places=10)
        self.assertEqual(result.unit.shorthand, "m/h")

    def test_simplify_plain_unit_unchanged(self):
        """Plain unit without scale returns equivalent Number."""
        result = units.meter(5).simplify()
        self.assertAlmostEqual(result.quantity, 5.0, places=10)
        self.assertEqual(result.unit.shorthand, "m")

    def test_simplify_preserves_dimension(self):
        """Simplified Number has same dimension."""
        km = Scale.kilo * units.meter
        original = km(5)
        simplified = original.simplify()
        self.assertEqual(original.unit.dimension, simplified.unit.dimension)

    def test_simplify_idempotent(self):
        """Simplifying twice gives same result."""
        km = Scale.kilo * units.meter
        result1 = km(5).simplify()
        result2 = result1.simplify()
        self.assertAlmostEqual(result1.quantity, result2.quantity, places=10)
        self.assertEqual(result1.unit.shorthand, result2.unit.shorthand)


class TestInformationDimension(unittest.TestCase):
    """Tests for Dimension.information and information units (bit, byte)."""

    def test_dimension_information_exists(self):
        """Dimension.information should be a valid dimension."""
        self.assertEqual(Dimension.information.name, 'information')
        self.assertNotEqual(Dimension.information, Dimension.none)

    def test_bit_unit_exists(self):
        """units.bit should have Dimension.information."""
        self.assertEqual(units.bit.dimension, Dimension.information)
        self.assertIn('b', units.bit.aliases)

    def test_byte_unit_exists(self):
        """units.byte should have Dimension.information."""
        self.assertEqual(units.byte.dimension, Dimension.information)
        self.assertIn('B', units.byte.aliases)

    def test_byte_to_bit_conversion(self):
        """1 byte should be 8 bits."""
        result = units.byte(1).to(units.bit)
        self.assertAlmostEqual(result.quantity, 8.0, places=10)

    def test_bit_to_byte_conversion(self):
        """8 bits should be 1 byte."""
        result = units.bit(8).to(units.byte)
        self.assertAlmostEqual(result.quantity, 1.0, places=10)

    def test_kibibyte_simplify(self):
        """1 kibibyte simplifies to 1024 bytes."""
        kibibyte = Scale.kibi * units.byte
        result = kibibyte(1).simplify()
        self.assertAlmostEqual(result.quantity, 1024.0, places=10)
        self.assertEqual(result.unit.shorthand, "B")

    def test_kilobyte_simplify(self):
        """1 kilobyte simplifies to 1000 bytes."""
        kilobyte = Scale.kilo * units.byte
        result = kilobyte(1).simplify()
        self.assertAlmostEqual(result.quantity, 1000.0, places=10)
        self.assertEqual(result.unit.shorthand, "B")

    def test_data_rate_dimension(self):
        """bytes/second should have information/time dimension."""
        data_rate = units.byte / units.second
        expected_dim = Dimension.information / Dimension.time
        self.assertEqual(data_rate.dimension, expected_dim)

    def test_information_orthogonal_to_physical(self):
        """Information dimension should be orthogonal to physical dimensions."""
        # byte * meter should have both information and length
        composite = units.byte * units.meter
        self.assertNotEqual(composite.dimension, Dimension.information)
        self.assertNotEqual(composite.dimension, Dimension.length)
