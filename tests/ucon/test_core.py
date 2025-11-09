import unittest

from ucon import Number
from ucon import Exponent
from ucon import Ratio
from ucon import Scale
from ucon import Dimension
from ucon import Unit
from ucon import units
from ucon.algebra import Vector


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

    def test_none_dimension_behaves_neutrally(self):
        base = Dimension.mass
        self.assertEqual(base * Dimension.none, base)
        self.assertEqual(base / Dimension.none, base)
        self.assertEqual(Dimension.none * base, base)
        with self.assertRaises(ValueError) as exc:
            Dimension.none / base
        assert type(exc.exception) == ValueError
        assert str(exc.exception).endswith('is not a valid Dimension')

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

    @unittest.skip("TODO (ucon#68): should pass when dynamic dimensions are supported")
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

    def test_scale_multiplication_with_unit(self):
        meter = Unit('m', name='meter', dimension=Dimension.length)
        kilometer = Scale.kilo * meter
        self.assertIsInstance(kilometer, Unit)
        self.assertEqual(kilometer.scale, Scale.kilo)
        self.assertEqual(kilometer.dimension, Dimension.length)
        self.assertIn('meter', kilometer.name)

    def test_scale_multiplication_with_unit_returns_not_implemented_for_invalid_type(self):
        with self.assertRaises(TypeError):
            Scale.kilo * 1


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
    unit = Unit(*unit_aliases, name=unit_name, dimension=Dimension.time)

    def test___repr__(self):
        self.assertEqual(f'<{self.unit_type} | {self.unit_name}>', str(self.unit))


class TestUnitEdgeCases(unittest.TestCase):

    # --- Initialization & representation -----------------------------------

    def test_default_unit_is_dimensionless(self):
        u = Unit()
        self.assertEqual(u.dimension, Dimension.none)
        self.assertEqual(u.name, '')
        self.assertEqual(u.aliases, ())
        self.assertEqual(u.shorthand, '')
        self.assertEqual(repr(u), '<none>')

    def test_unit_with_aliases_and_name(self):
        u = Unit('m', 'M', name='meter', dimension=Dimension.length)
        self.assertEqual(u.shorthand, 'm')
        self.assertIn('m', u.aliases)
        self.assertIn('M', u.aliases)
        self.assertIn('length', repr(u))
        self.assertIn('meter', repr(u))

    def test_hash_and_equality_consistency(self):
        u1 = Unit('m', name='meter', dimension=Dimension.length)
        u2 = Unit('m', name='meter', dimension=Dimension.length)
        u3 = Unit('s', name='second', dimension=Dimension.time)
        self.assertEqual(u1, u2)
        self.assertEqual(hash(u1), hash(u2))
        self.assertNotEqual(u1, u3)
        self.assertNotEqual(hash(u1), hash(u3))

    def test_units_with_same_name_but_different_dimension_not_equal(self):
        u1 = Unit(name='amp', dimension=Dimension.current)
        u2 = Unit(name='amp', dimension=Dimension.time)
        self.assertNotEqual(u1, u2)

    # --- generate_name edge cases -----------------------------------------

    def test_generate_name_both_have_shorthand(self):
        u1 = Unit('m', name='meter', dimension=Dimension.length)
        u2 = Unit('s', name='second', dimension=Dimension.time)
        result = u1.generate_name(u2, '*')
        self.assertEqual(result, '(m*s)')

    def test_generate_name_missing_left_shorthand(self):
        u1 = Unit(name='unitless', dimension=Dimension.none)
        u2 = Unit('s', name='second', dimension=Dimension.time)
        self.assertEqual(u1.generate_name(u2, '/'), 'second')

    def test_generate_name_missing_right_shorthand(self):
        u1 = Unit('m', name='meter', dimension=Dimension.length)
        u2 = Unit(name='none', dimension=Dimension.none)
        self.assertEqual(u1.generate_name(u2, '*'), 'meter')

    def test_generate_name_no_aliases_on_either_side(self):
        u1 = Unit(name='foo', dimension=Dimension.length)
        u2 = Unit(name='bar', dimension=Dimension.time)
        self.assertEqual(u1.generate_name(u2, '*'), '(foo*bar)')

    # --- arithmetic behavior ----------------------------------------------

    def test_multiplication_produces_composite_unit(self):
        m = Unit('m', name='meter', dimension=Dimension.length)
        s = Unit('s', name='second', dimension=Dimension.time)
        v = m / s
        self.assertIsInstance(v, Unit)
        self.assertEqual(v.dimension, Dimension.velocity)
        self.assertIn('/', v.name)

    def test_division_with_dimensionless_denominator_returns_self(self):
        m = Unit('m', name='meter', dimension=Dimension.length)
        none = Unit(name='none', dimension=Dimension.none)
        result = m / none
        self.assertEqual(result, m)

    def test_division_of_identical_units_returns_dimensionless(self):
        m1 = Unit('m', name='meter', dimension=Dimension.length)
        m2 = Unit('m', name='meter', dimension=Dimension.length)
        result = m1 / m2
        self.assertEqual(result.dimension, Dimension.none)
        self.assertEqual(result.name, '')

    def test_multiplying_with_dimensionless_returns_self(self):
        m = Unit('m', name='meter', dimension=Dimension.length)
        none = Unit(name='none', dimension=Dimension.none)
        result = m * none
        self.assertEqual(result.dimension, Dimension.length)
        self.assertIn('m', result.name)

    def test_invalid_dimension_combinations_raise_value_error(self):
        m = Unit('m', name='meter', dimension=Dimension.length)
        c = Unit('C', name='coulomb', dimension=Dimension.charge)
        # The result of dividing these is undefined (no such Dimension)
        with self.assertRaises(ValueError):
            _ = m / c
        with self.assertRaises(ValueError):
            _ = c * m

    # --- equality, hashing, immutability ----------------------------------

    def test_equality_with_non_unit(self):
        with self.assertRaises(TypeError):
            Unit('m', name='meter', dimension=Dimension.length) == 'meter'

    def test_hash_stability_in_collections(self):
        m1 = Unit('m', name='meter', dimension=Dimension.length)
        s = set([m1])
        self.assertIn(Unit('m', name='meter', dimension=Dimension.length), s)

    def test_operations_do_not_mutate_operands(self):
        m = Unit('m', name='meter', dimension=Dimension.length)
        s = Unit('s', name='second', dimension=Dimension.time)
        _ = m / s
        self.assertEqual(m.dimension, Dimension.length)
        self.assertEqual(s.dimension, Dimension.time)

    # --- operator edge cases ----------------------------------------------

    def test_generate_name_handles_empty_names_and_aliases(self):
        a = Unit()
        b = Unit()
        self.assertEqual(a.generate_name(b, '*'), '')

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
