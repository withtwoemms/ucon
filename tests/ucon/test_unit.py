

from unittest import TestCase

from ucon.dimension import Dimension
from ucon.unit import Unit


class TestUnit(TestCase):

    unit_name = 'second'
    unit_type = 'time'
    unit_aliases = ('seconds', 'secs', 's', 'S')
    unit = Unit(*unit_aliases, name=unit_name, dimension=Dimension.time)

    def test___repr__(self):
        self.assertEqual(f'<{self.unit_type} | {self.unit_name}>', str(self.unit))


class TestUnitEdgeCases(TestCase):

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
