# © 2025 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

import math
import unittest

from ucon import Number
from ucon import Exponent
from ucon import Ratio
from ucon import Scale
from ucon import Dimension
from ucon import Unit
from ucon import units
from ucon.algebra import Vector
from ucon.core import UnitFactor, UnitProduct, ScaleDescriptor


class TestDimension(unittest.TestCase):

    def test_basic_dimensions_are_unique(self):
        seen = set()
        for dim in Dimension:
            self.assertNotIn(dim.value, seen, f'Duplicate vector found for {dim.name}')
            seen.add(dim.value)

    def test_multiplication_adds_exponents(self):
        self.assertEqual(
            Dimension.mass * Dimension.acceleration,
            Dimension.force,
        )
        self.assertEqual(
            Dimension.length * Dimension.length,
            Dimension.area,
        )
        self.assertEqual(
            Dimension.length * Dimension.length * Dimension.length,
            Dimension.volume,
        )

    def test_division_subtracts_exponents(self):
        self.assertEqual(
            Dimension.length / Dimension.time,
            Dimension.velocity,
        )
        self.assertEqual(
            Dimension.force / Dimension.area,
            Dimension.pressure,
        )

    # def test_none_dimension_behaves_neutrally(self):
    #     base = Dimension.mass
    #     self.assertEqual(base * Dimension.none, base)
    #     self.assertEqual(base / Dimension.none, base)
    #     self.assertEqual(Dimension.none * base, base)
    #     with self.assertRaises(ValueError) as exc:
    #         Dimension.none / base
    #     assert type(exc.exception) == ValueError
    #     assert str(exc.exception).endswith('is not a valid Dimension')

    def test_hash_and_equality_consistency(self):
        d1 = Dimension.mass
        d2 = Dimension.mass
        d3 = Dimension.length
        self.assertEqual(d1, d2)
        self.assertNotEqual(d1, d3)
        self.assertEqual(hash(d1), hash(d2))
        self.assertNotEqual(hash(d1), hash(d3))

    def test_composite_quantities_examples(self):
        # Energy = Force * Length
        self.assertEqual(
            Dimension.force * Dimension.length,
            Dimension.energy,
        )
        # Power = Energy / Time
        self.assertEqual(
            Dimension.energy / Dimension.time,
            Dimension.power,
        )
        # Pressure = Force / Area
        self.assertEqual(
            Dimension.force / Dimension.area,
            Dimension.pressure,
        )
        # Charge = Current * Time
        self.assertEqual(
            Dimension.current * Dimension.time,
            Dimension.charge,
        )

    def test_vector_equality_reflects_dimension_equality(self):
        self.assertEqual(Dimension.mass.value, Dimension.mass.value)
        self.assertNotEqual(Dimension.mass.value, Dimension.time.value)
        self.assertEqual(Dimension.mass, Dimension.mass)
        self.assertNotEqual(Dimension.mass, Dimension.time)

    def test_pow_identity_and_zero(self):
        self.assertIs(Dimension.length ** 1, Dimension.length)
        self.assertIs(Dimension.mass ** 0, Dimension.none)

    def test_pow_known_results(self):
        self.assertEqual(Dimension.length ** 2, Dimension.area)
        self.assertEqual(Dimension.time ** -1, Dimension.frequency)

    def test_pow_returns_derived_dimension_for_unknown(self):
        jerk = Dimension.length * (Dimension.time ** -3)  # length / time^3
        self.assertTrue(jerk.name.startswith("derived("))
        self.assertNotIn(jerk.name, Dimension.__members__)

    def test_resolve_known_vector_returns_enum_member(self):
        dim = Dimension._resolve(Vector(0, 1, 0, 0, 0, 0, 0))
        self.assertIs(dim, Dimension.length)

    def test_resolve_unknown_vector_returns_dynamic_dimension(self):
        vec = Vector(T=1, L=-1, M=0, I=0, Θ=0, J=0, N=0)  # “speed per time”, not an enum member
        dyn = Dimension._resolve(vec)
        self.assertNotIn(dyn.name, Dimension.__members__)
        self.assertEqual(dyn.value, vec)
        self.assertEqual(dyn.name, f"derived({vec})")

    def test_resolve_returns_same_dynamic_for_same_vector(self):
        vec = Vector(T=2, L=-2, M=0, I=0, Θ=0, J=0, N=0)
        first = Dimension._resolve(vec)
        second = Dimension._resolve(vec)
        self.assertEqual(first.value, second.value)
        self.assertEqual(first.name, second.name)

    def test_dynamic_dimensions_compare_by_vector(self):
        v1 = Vector(T=2, L=-2, M=0, I=0, Θ=0, J=0, N=0)
        v2 = Vector(T=2, L=-2, M=0, I=0, Θ=0, J=0, N=0)
        d1 = Dimension._resolve(v1)
        d2 = Dimension._resolve(v2)
        self.assertEqual(d1.value, d2.value)
        self.assertEqual(d1 == d2, True)
        self.assertEqual(hash(d1), hash(d2))

    def test_pow_zero_returns_none(self):
        # Dimension ** 0 should always return Dimension.none
        self.assertIs(Dimension.length ** 0, Dimension.none)

    def test_pow_fractional(self):
        # Fractional powers = derived dimensions not equal to any registered one
        d = Dimension.length ** 0.5
        self.assertIsInstance(d, Dimension)
        self.assertNotIn(d, list(Dimension))

    def test_invalid_operand_multiply(self):
        with self.assertRaises(TypeError):
            Dimension.length * 10

    def test_invalid_operand_divide(self):
        with self.assertRaises(TypeError):
            Dimension.time / "bad"


class TestDimensionResolve(unittest.TestCase):

    def test_registered_multiplication(self):
        # velocity = length / time
        v = Dimension.length / Dimension.time
        self.assertIs(v, Dimension.velocity)
        self.assertEqual(v.value, Vector(-1, 1, 0, 0, 0, 0, 0))

    def test_registered_power(self):
        # area = length ** 2
        a = Dimension.length ** 2
        self.assertIs(a, Dimension.area)
        self.assertEqual(a.value, Vector(0, 2, 0, 0, 0, 0, 0))

    def test_unregistered_multiplication_creates_derived(self):
        # L * M should yield derived(Vector(L=1, M=1))
        d = Dimension.length * Dimension.mass
        self.assertIsInstance(d, Dimension)
        self.assertNotIn(d, list(Dimension))
        self.assertIn("derived", d.name)
        self.assertEqual(d.value, Vector(0, 1, 1, 0, 0, 0, 0))

    def test_unregistered_division_creates_derived(self):
        # M / T should yield derived(Vector(M=1, T=-1))
        d = Dimension.mass / Dimension.time
        self.assertIsInstance(d, Dimension)
        self.assertNotIn(d, list(Dimension))
        self.assertIn("derived", d.name)
        self.assertEqual(d.value, Vector(-1, 0, 1, 0, 0, 0, 0))

    def test_unregistered_power_creates_derived(self):
        # (L * M)^2 → derived(Vector(L=2, M=2))
        d1 = Dimension.length * Dimension.mass
        d2 = d1 ** 2
        self.assertIsInstance(d2, Dimension)
        self.assertIn("derived", d2.name)
        self.assertEqual(d2.value, Vector(0, 2, 2, 0, 0, 0, 0))

    def test_registered_vs_derived_equality(self):
        # Ensure derived dimensions only equal themselves
        derived = Dimension.length * Dimension.mass
        again = Dimension._resolve(Vector(0, 1, 1, 0, 0, 0, 0))
        self.assertEqual(derived, again)
        self.assertNotEqual(derived, Dimension.length)
        self.assertNotEqual(derived, Dimension.mass)


class TestDimensionEdgeCases(unittest.TestCase):

    def test_invalid_multiplication_type(self):
        with self.assertRaises(TypeError):
            Dimension.length * 5
        with self.assertRaises(TypeError):
            "mass" * Dimension.time

    def test_invalid_division_type(self):
        with self.assertRaises(TypeError):
            Dimension.time / "length"
        with self.assertRaises(TypeError):
            5 / Dimension.mass

    def test_equality_with_non_dimension(self):
        with self.assertRaises(TypeError):
            Dimension.mass ==  "mass"

    def test_enum_uniqueness_and_hash(self):
        # Hashes should be unique per distinct dimension
        hashes = {hash(d) for d in Dimension}
        self.assertEqual(len(hashes), len(Dimension))
        # All Dimension.value entries must be distinct Vectors
        values = [d.value for d in Dimension]
        self.assertEqual(len(values), len(set(values)))

    def test_combined_chained_operations(self):
        # (mass * acceleration) / area = pressure
        result = (Dimension.mass * Dimension.acceleration) / Dimension.area
        self.assertEqual(result, Dimension.pressure)

    def test_dimension_round_trip_equality(self):
        # Multiplying and dividing by the same dimension returns self
        d = Dimension.energy
        self.assertEqual((d * Dimension.none) / Dimension.none, d)
        self.assertEqual(d / Dimension.none, d)
        self.assertEqual(Dimension.none * d, d)

    def test_enum_is_hashable_and_iterable(self):
        seen = {d for d in Dimension}
        self.assertIn(Dimension.mass, seen)
        self.assertEqual(len(seen), len(Dimension))


class TestScaleDescriptor(unittest.TestCase):

    def test_scale_descriptor_power_and_repr(self):
        exp = Exponent(10, 3)
        desc = ScaleDescriptor(exp, "k", "kilo")

        # power property should reflect Exponent.power
        assert desc.power == 3
        assert desc.base == 10
        assert math.isclose(desc.evaluated, 1e3)

        # repr should include alias and power
        r = repr(desc)
        assert "kilo" in r or "k" in r
        assert "10^3" in r


class TestScale(unittest.TestCase):

    def test___truediv__(self):
        self.assertEqual(Scale.deca, Scale.one / Scale.deci)
        self.assertEqual(Scale.deci, Scale.one / Scale.deca)
        self.assertEqual(Scale.kibi, Scale.mebi / Scale.kibi)
        self.assertEqual(Scale.milli, Scale.one / Scale.deca / Scale.deca / Scale.deca)
        self.assertEqual(Scale.deca, Scale.kilo / Scale.hecto)
        self.assertEqual(Scale.kibi, Scale.kibi / Scale.one)
        self.assertEqual(Scale.one, Scale.one / Scale.one)
        self.assertEqual(Scale.one, Scale.kibi / Scale.kibi)
        self.assertEqual(Scale.one, Scale.kibi / Scale.kilo)

    def test___mul__(self):
        self.assertEqual(Scale.kilo, Scale.kilo * Scale.one)
        self.assertEqual(Scale.kilo, Scale.one * Scale.kilo)
        self.assertEqual(Scale.one, Scale.kilo * Scale.milli)
        self.assertEqual(Scale.deca, Scale.hecto * Scale.deci)
        self.assertEqual(Scale.mega, Scale.kilo * Scale.kibi)
        self.assertEqual(Scale.giga, Scale.mega * Scale.kilo)
        self.assertEqual(Scale.one, Scale.one * Scale.one)

    def test___lt__(self):
        self.assertLess(Scale.one, Scale.kilo)

    def test___gt__(self):
        self.assertGreater(Scale.kilo, Scale.one)

    def test_all(self):
        for scale in Scale:
            self.assertTrue(isinstance(scale.value.exponent, Exponent))
        self.assertIsInstance(Scale.all(), dict)


class TestScaleMultiplicationAdditional(unittest.TestCase):

    def test_decimal_combinations(self):
        self.assertEqual(Scale.kilo * Scale.centi, Scale.deca)
        self.assertEqual(Scale.kilo * Scale.milli, Scale.one)
        self.assertEqual(Scale.hecto * Scale.deci, Scale.deca)

    def test_binary_combinations(self):
        # kibi (2^10) * mebi (2^20) = 2^30 (should round to nearest known)
        result = Scale.kibi * Scale.mebi
        self.assertEqual(result.value.base, 2)
        self.assertTrue(isinstance(result, Scale))

    def test_mixed_base_combination(self):
        self.assertEqual(Scale.mega, Scale.kilo * Scale.kibi)

    def test_result_has_no_exact_match_fallbacks_to_nearest(self):
        # Suppose the exponent product is not in Scale.all()
        # e.g. kilo (10^3) * deci (10^-1) = 10^2 = hecto
        result = Scale.kilo * Scale.deci
        self.assertEqual(result, Scale.hecto)

    def test_order_independence(self):
        # Associativity of multiplication
        self.assertEqual(Scale.kilo * Scale.centi, Scale.centi * Scale.kilo)

    def test_non_scale_operand_returns_not_implemented(self):
        with self.assertRaises(TypeError):
            Scale.kilo * 2

    def test_large_exponent_clamping(self):
        # simulate a very large multiplication, should still resolve
        result = Scale.mega * Scale.mega  # 10^12, not defined -> nearest Scale
        self.assertIsInstance(result, Scale)
        self.assertEqual(result.value.base, 10)

    @unittest.skip("TODO: revamp: Unit.scale is deprecated.")
    def test_scale_multiplication_with_unit(self):
        meter = UnitFactor('m', name='meter', dimension=Dimension.length)
        kilometer = Scale.kilo * meter
        self.assertIsInstance(kilometer, UnitFactor)
        self.assertEqual(kilometer.scale, Scale.kilo)
        self.assertEqual(kilometer.dimension, Dimension.length)
        self.assertIn('meter', kilometer.name)

    def test_scale_multiplication_with_unit_returns_not_implemented_for_invalid_type(self):
        with self.assertRaises(TypeError):
            Scale.kilo * 1

    def test_scale_mul_with_unknown_exponent_hits_nearest(self):
        # Construct two strange scales (base10^7 * base10^5 = base10^12 = tera)
        s = Scale.nearest(10**7) * Scale.nearest(10**5)
        self.assertIs(s, Scale.tera)

    def test_scale_mul_non_unit_non_scale(self):
        self.assertEqual(Scale.kilo.__mul__("nope"), NotImplemented)


class TestScaleDivisionAdditional(unittest.TestCase):

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

    def test_scale_div_hits_nearest(self):
        # giga / kilo = 10^(9-3) = 10^6 = mega
        self.assertIs(Scale.giga / Scale.kilo, Scale.mega)

    def test_scale_div_non_scale(self):
        self.assertEqual(Scale.kilo.__truediv__("bad"), NotImplemented)


class TestScaleNearestAdditional(unittest.TestCase):

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


class TestScaleInternals(unittest.TestCase):

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


class TestUnit(unittest.TestCase):

    unit_name = 'second'
    unit_type = 'time'
    unit_aliases = ('seconds', 'secs', 's', 'S')
    unit = Unit(name=unit_name, dimension=Dimension.time, aliases=unit_aliases)

    def test___repr__(self):
        self.assertEqual(f'<Unit {self.unit_aliases[0]}>', str(self.unit))

    def test_unit_repr_has_dimension_when_no_shorthand(self):
        u = Unit(name="", dimension=Dimension.force)
        r = repr(u)
        self.assertIn("force", r)
        self.assertTrue(r.startswith("<Unit"))

    def test_unit_equality_alias_normalization(self):
        # ('',) should normalize to () under _norm
        u1 = Unit(name="x", dimension=Dimension.length, aliases=("",))
        u2 = Unit(name="x", dimension=Dimension.length)
        self.assertEqual(u1, u2)

    def test_unit_invalid_eq_type(self):
        self.assertFalse(Unit(name="meter", dimension=Dimension.length, aliases=("m",)) == "meter")


class TestUnitProduct(unittest.TestCase):

    mf = UnitFactor(unit=units.meter, scale=Scale.one)
    sf = UnitFactor(unit=units.second, scale=Scale.one)
    nf = UnitFactor(unit=units.none, scale=Scale.one)
    velocity = UnitProduct({mf: 1, sf: -1})
    acceleration = UnitProduct({mf: 1, sf: -2})

    def test_composite_unit_collapses_to_unit(self):
        cu = UnitProduct({self.mf: 1})
        # should anneal to Unit
        self.assertIsInstance(cu, UnitProduct)
        self.assertEqual(cu.shorthand, self.mf.shorthand)

    def test_merge_of_identical_units(self):
        # Inner composite that already has m^1
        inner = UnitProduct({self.mf: 1, self.sf: -1})
        # Outer composite sees both `m:1` and `inner:1`
        up = UnitProduct({self.mf: 1, inner: 1})
        # merge_unit should accumulate the exponents → m^(1 + 1) = m^2
        self.assertIn(self.mf, up.factors)
        self.assertEqual(up.factors[self.mf], 2)

    def test_merge_of_nested_composite_units(self):
        # expect m*s^-2
        self.assertEqual(self.acceleration.factors[self.mf], 1)
        self.assertEqual(self.acceleration.factors[self.sf], -2)

    def test_drop_dimensionless_component(self):
        up = UnitProduct({self.mf: 2, self.nf: 1})
        self.assertIn(self.mf, up.factors)
        self.assertNotIn(self.nf, up.factors)

    def test_unitproduct_can_behave_like_single_unit(self):
        """
        A UnitProduct with only one factor should seem like that factor.
        """
        up = UnitProduct({self.mf: 1})
        self.assertEqual(up.shorthand, self.mf.shorthand)
        self.assertEqual(up.dimension, self.mf.dimension)

    def test_composite_mul_with_scale(self):
        up = UnitProduct({self.mf: 1, self.sf: -1})
        result = Scale.kilo * up
        # equivalent to scale multiplication on RMUL path
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.shorthand, "km/s")

    def test_composite_div_dimensionless(self):
        up = UnitProduct({self.mf: 2})
        out = up / UnitProduct({})
        self.assertEqual(out.factors[self.mf], 2)

    def test_truediv_composite_by_composite(self):
        jerk = self.acceleration / self.velocity
        # jerk = m^1 s^-2  /  m^1 s^-1 = s^-1
        self.assertEqual(list(jerk.factors.values()), [-1])


class TestUnitEdgeCases(unittest.TestCase):

    # --- Initialization & representation -----------------------------------

    def test_default_unit_is_dimensionless(self):
        u = Unit()
        self.assertEqual(u.dimension, Dimension.none)
        self.assertEqual(u.name, '')
        self.assertEqual(u.aliases, ())
        self.assertEqual(u.shorthand, '')
        self.assertEqual(repr(u), '<Unit>')

    def test_unit_with_aliases_and_name(self):
        u = Unit(name='meter', dimension=Dimension.length, aliases=('m', 'M'))
        self.assertEqual(u.shorthand, 'm')
        self.assertIn('m', u.aliases)
        self.assertIn('M', u.aliases)
        self.assertIn('length', u.dimension.name)
        self.assertIn('meter', u.name)
        self.assertIn('<Unit m>', repr(u))

    def test_hash_and_equality_consistency(self):
        u1 = Unit(name='meter', dimension=Dimension.length, aliases=('m',))
        u2 = Unit(name='meter', dimension=Dimension.length, aliases=('m',))
        u3 = Unit(name='second', dimension=Dimension.time, aliases=('s',))
        self.assertEqual(u1, u2)
        self.assertEqual(hash(u1), hash(u2))
        self.assertNotEqual(u1, u3)
        self.assertNotEqual(hash(u1), hash(u3))

    def test_units_with_same_name_but_different_dimension_not_equal(self):
        u1 = Unit(name='amp', dimension=Dimension.current)
        u2 = Unit(name='amp', dimension=Dimension.time)
        self.assertNotEqual(u1, u2)

    # --- arithmetic behavior ----------------------------------------------

    def test_multiplication_produces_composite_unit(self):
        m = Unit(name='meter', dimension=Dimension.length, aliases=('m',))
        s = Unit(name='second', dimension=Dimension.time, aliases=('s',))
        v = m / s
        self.assertIsInstance(v, UnitProduct)
        self.assertEqual(v.dimension, Dimension.velocity)
        self.assertIn('/', repr(v))

    def test_division_with_dimensionless_denominator_returns_self(self):
        m = Unit(name='meter', dimension=Dimension.length, aliases=('m',))
        none = Unit(name='none', dimension=Dimension.none)
        result = m / none
        self.assertEqual(result, m)

    def test_division_of_identical_units_returns_dimensionless(self):
        m1 = Unit(name='meter', dimension=Dimension.length, aliases=('m',))
        m2 = Unit(name='meter', dimension=Dimension.length, aliases=('m',))
        result = m1 / m2
        self.assertEqual(result.dimension, Dimension.none)
        self.assertEqual(result.name, '')

    def test_multiplying_with_dimensionless_returns_self(self):
        m = Unit(name='meter', dimension=Dimension.length, aliases=('m',))
        none = Unit(name='none', dimension=Dimension.none)
        result = m * none
        self.assertEqual(result.dimension, Dimension.length)
        self.assertEqual('m', result.shorthand)

    def test_invalid_dimension_combinations_raise_value_error(self):
        m = Unit(name='meter', dimension=Dimension.length, aliases=('m',))
        c = Unit(name='coulomb', dimension=Dimension.charge, aliases=('C',))
        # The result of combination gives CompositeUnit
        self.assertIsInstance(m / c, UnitProduct)
        self.assertIsInstance(m * c, UnitProduct)

    # --- equality, hashing, immutability ----------------------------------

    def test_equality_with_non_unit(self):
        self.assertFalse(Unit(name='meter', dimension=Dimension.length, aliases=('m',)) == 'meter')

    def test_hash_stability_in_collections(self):
        m1 = Unit(name='meter', dimension=Dimension.length, aliases=('m',))
        s = set([m1])
        self.assertIn(Unit(name='meter', dimension=Dimension.length, aliases=('m',)), s)

    def test_operations_do_not_mutate_operands(self):
        m = Unit(name='meter', dimension=Dimension.length, aliases=('m',))
        s = Unit(name='second', dimension=Dimension.time, aliases=('s',))
        _ = m / s
        self.assertEqual(m.dimension, Dimension.length)
        self.assertEqual(s.dimension, Dimension.time)

    # --- operator edge cases ----------------------------------------------

    def test_repr_contains_dimension_name_even_without_name(self):
        u = Unit(dimension=Dimension.force)
        self.assertIn('force', repr(u))


class TestScaleEdgeCases(unittest.TestCase):

    def test_nearest_prefers_decimal_by_default(self):
        self.assertEqual(Scale.nearest(1024), Scale.kilo)
        self.assertEqual(Scale.nearest(50_000), Scale.kilo)
        self.assertEqual(Scale.nearest(1/1024), Scale.milli)

    def test_nearest_includes_binary_when_opted_in(self):
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

    def test_descriptor_property(self):
        self.assertIsInstance(Scale.kilo.descriptor, ScaleDescriptor)
        self.assertEqual(Scale.kilo.descriptor, Scale.kilo.value)

    def test_alias_property(self):
        self.assertEqual(Scale.kilo.alias, "kilo")
        self.assertEqual(Scale.one.alias, "")

    def test_scale_descriptor_parts(self):
        self.assertEqual(Scale.kilo.value.parts(), (10, 3))
        self.assertEqual(Scale.kibi.value.parts(), (2, 10))

    def test_scale_hash_used_in_sets(self):
        s = {Scale.kilo, Scale.milli}
        self.assertIn(Scale.kilo, s)
        self.assertNotIn(Scale.one, s)

    def test_scale_mul_nonmatching_falls_to_nearest(self):
        # kilo * kibi → no exact match, falls through to Scale.nearest
        result = Scale.kilo * Scale.kibi
        self.assertIsInstance(result, Scale)

    def test_scale_pow(self):
        result = Scale.kilo ** 2
        self.assertEqual(result, Scale.mega)

    def test_scale_pow_binary(self):
        result = Scale.kibi ** 2
        self.assertEqual(result, Scale.mebi)

    def test_scale_pow_nonmatching_falls_to_nearest(self):
        result = Scale.kilo ** 0.5
        self.assertIsInstance(result, Scale)


class TestUnitAlgebra(unittest.TestCase):

    def test_unit_mul_unitproduct(self):
        m = units.meter
        velocity = UnitProduct({m: 1, units.second: -1})
        result = m * velocity
        self.assertIsInstance(result, UnitProduct)
        # m * (m/s) = m²/s
        self.assertEqual(result.dimension, Dimension.area / Dimension.time)

    def test_unit_mul_non_unit_returns_not_implemented(self):
        result = units.meter.__mul__("not a unit")
        self.assertIs(result, NotImplemented)

    def test_unit_truediv_non_unit_returns_not_implemented(self):
        result = units.meter.__truediv__("not a unit")
        self.assertIs(result, NotImplemented)

    def test_unit_pow(self):
        m = units.meter
        result = m ** 2
        self.assertIsInstance(result, UnitProduct)
        self.assertEqual(result.dimension, Dimension.area)

    def test_unit_pow_3(self):
        m = units.meter
        result = m ** 3
        self.assertEqual(result.dimension, Dimension.volume)


class TestUnitFactorCoverage(unittest.TestCase):

    def test_shorthand_name_fallback(self):
        # UnitFactor where unit has no aliases but has a name
        u = Unit(name='gram', dimension=Dimension.mass)
        fu = UnitFactor(unit=u, scale=Scale.milli)
        self.assertEqual(fu.shorthand, 'mgram')

    def test_repr(self):
        fu = UnitFactor(unit=units.meter, scale=Scale.kilo)
        self.assertIn('UnitFactor', repr(fu))
        self.assertIn('kilo', repr(fu))

    def test_eq_non_unit_returns_not_implemented(self):
        fu = UnitFactor(unit=units.meter, scale=Scale.one)
        self.assertIs(fu.__eq__("string"), NotImplemented)


class TestUnitProductAlgebra(unittest.TestCase):

    def test_mul_unitproduct_by_unitproduct(self):
        velocity = UnitProduct({units.meter: 1, units.second: -1})
        time_sq = UnitProduct({units.second: 2})
        result = velocity * time_sq
        self.assertIsInstance(result, UnitProduct)
        # (m/s) * s² = m·s
        self.assertEqual(result.dimension, Dimension.length * Dimension.time)

    def test_mul_unitproduct_by_scale_returns_not_implemented(self):
        velocity = UnitProduct({units.meter: 1, units.second: -1})
        result = velocity.__mul__(Scale.kilo)
        self.assertIs(result, NotImplemented)

    def test_mul_unitproduct_by_non_unit_returns_not_implemented(self):
        velocity = UnitProduct({units.meter: 1, units.second: -1})
        result = velocity.__mul__("string")
        self.assertIs(result, NotImplemented)

    def test_truediv_unitproduct_by_unitproduct(self):
        acceleration = UnitProduct({units.meter: 1, units.second: -2})
        velocity = UnitProduct({units.meter: 1, units.second: -1})
        result = acceleration / velocity
        self.assertIsInstance(result, UnitProduct)
        # (m/s²) / (m/s) = 1/s
        self.assertEqual(result.dimension, Dimension.frequency)

    def test_rmul_unit_times_unitproduct(self):
        velocity = UnitProduct({units.meter: 1, units.second: -1})
        result = units.meter * velocity
        self.assertIsInstance(result, UnitProduct)

    def test_rmul_scale_on_empty_unitproduct(self):
        empty = UnitProduct({})
        result = Scale.kilo * empty
        self.assertIs(result, empty)

    def test_rmul_scale_applies_to_sink_unit(self):
        velocity = UnitProduct({units.meter: 1, units.second: -1})
        result = Scale.kilo * velocity
        self.assertIsInstance(result, UnitProduct)
        self.assertIn('km', result.shorthand)

    def test_rmul_scale_combines_with_existing_scale(self):
        km_per_s = Scale.kilo * UnitProduct({units.meter: 1, units.second: -1})
        # Apply another scale on top → should combine scales
        result = Scale.milli * km_per_s
        self.assertIsInstance(result, UnitProduct)

    def test_rmul_non_unit_returns_not_implemented(self):
        velocity = UnitProduct({units.meter: 1, units.second: -1})
        result = velocity.__rmul__("string")
        self.assertIs(result, NotImplemented)

    def test_append_dimensionless_skipped(self):
        # UnitProduct with only dimensionless factor → empty shorthand
        up = UnitProduct({})
        self.assertEqual(up.shorthand, "")

    def test_shorthand_with_negative_non_unit_exponent(self):
        # e.g. m/s² should show superscript on denominator
        accel = UnitProduct({units.meter: 1, units.second: -2})
        sh = accel.shorthand
        self.assertIn('m', sh)
        self.assertIn('s', sh)

    def test_shorthand_numerator_exponent(self):
        area = UnitProduct({units.meter: 2})
        self.assertIn('m', area.shorthand)
        # Should contain superscript 2
        self.assertIn('²', area.shorthand)
