# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
Tests for the new Dimension dataclass in ucon.dimension.
"""

import unittest
from fractions import Fraction

from ucon.dimension import (
    Dimension,
    resolve,
    basis,
    SI,
    NONE,
    TIME,
    LENGTH,
    MASS,
    CURRENT,
    TEMPERATURE,
    LUMINOUS_INTENSITY,
    AMOUNT_OF_SUBSTANCE,
    INFORMATION,
    ANGLE,
    SOLID_ANGLE,
    RATIO,
    COUNT,
    VELOCITY,
    ACCELERATION,
    FORCE,
    ENERGY,
    POWER,
    AREA,
    VOLUME,
    DENSITY,
    PRESSURE,
    FREQUENCY,
    CHARGE,
    VOLTAGE,
)
from ucon.basis import Vector


class TestDimensionConstruction(unittest.TestCase):
    """Test Dimension construction methods."""

    def test_from_components_basic(self):
        """Test creating dimension from named components."""
        velocity = Dimension.from_components(L=1, T=-1, name="velocity")
        self.assertEqual(velocity, VELOCITY)

    def test_from_components_using_symbols(self):
        """Test creating dimension using symbol names."""
        # Using symbol names instead of full names
        dim = Dimension.from_components(L=1, name="length_test")
        self.assertEqual(dim.vector, LENGTH.vector)

    def test_from_components_derived(self):
        """Test creating complex derived dimension."""
        # Force = M*L/T^2
        force = Dimension.from_components(M=1, L=1, T=-2, name="force")
        self.assertEqual(force, FORCE)

    def test_pseudo_dimension(self):
        """Test creating pseudo-dimension."""
        angle = Dimension.pseudo("angle", name="angle")
        self.assertTrue(angle.is_pseudo)
        self.assertEqual(angle.tag, "angle")
        self.assertTrue(angle.is_dimensionless)

    def test_pseudo_dimensions_are_distinct(self):
        """Test that pseudo-dimensions with different tags are not equal."""
        self.assertNotEqual(ANGLE, RATIO)
        self.assertNotEqual(ANGLE, COUNT)
        self.assertNotEqual(RATIO, SOLID_ANGLE)

    def test_pseudo_dimensions_not_equal_to_none(self):
        """Test that pseudo-dimensions are not equal to NONE."""
        self.assertNotEqual(ANGLE, NONE)
        self.assertNotEqual(RATIO, NONE)
        self.assertNotEqual(COUNT, NONE)
        self.assertNotEqual(SOLID_ANGLE, NONE)


class TestDimensionAlgebra(unittest.TestCase):
    """Test dimension algebraic operations."""

    def test_multiplication_creates_derived_dimension(self):
        """Test that multiplication produces correct derived dimensions."""
        self.assertEqual(MASS * ACCELERATION, FORCE)
        self.assertEqual(LENGTH * LENGTH, AREA)
        self.assertEqual(LENGTH * LENGTH * LENGTH, VOLUME)

    def test_division_creates_derived_dimension(self):
        """Test that division produces correct derived dimensions."""
        self.assertEqual(LENGTH / TIME, VELOCITY)
        self.assertEqual(FORCE / AREA, PRESSURE)
        self.assertEqual(ENERGY / TIME, POWER)

    def test_power_creates_derived_dimension(self):
        """Test that exponentiation produces correct derived dimensions."""
        self.assertEqual(LENGTH ** 2, AREA)
        self.assertEqual(LENGTH ** 3, VOLUME)
        self.assertEqual(TIME ** -1, FREQUENCY)

    def test_power_zero_returns_none(self):
        """Test that power of 0 returns NONE."""
        self.assertEqual(LENGTH ** 0, NONE)
        self.assertEqual(MASS ** 0, NONE)

    def test_power_one_returns_same(self):
        """Test that power of 1 returns the same dimension."""
        self.assertIs(LENGTH ** 1, LENGTH)
        self.assertIs(MASS ** 1, MASS)

    def test_fractional_power(self):
        """Test fractional exponents create derived dimensions."""
        sqrt_length = LENGTH ** Fraction(1, 2)
        self.assertIsInstance(sqrt_length, Dimension)
        self.assertNotEqual(sqrt_length, LENGTH)

    def test_composite_expression(self):
        """Test complex composite expressions."""
        # Energy = Force * Length = (M*L/T^2) * L = M*L^2/T^2
        energy_via_force = FORCE * LENGTH
        self.assertEqual(energy_via_force, ENERGY)

        # Power = Energy / Time
        power_via_energy = ENERGY / TIME
        self.assertEqual(power_via_energy, POWER)

    def test_charge_equals_current_times_time(self):
        """Test that Charge = Current * Time."""
        self.assertEqual(CURRENT * TIME, CHARGE)

    def test_pseudo_dimension_acts_as_identity_in_multiplication(self):
        """Test that pseudo-dimensions act as identity when multiplied with regular dimensions."""
        # ANGLE * LENGTH = LENGTH (pseudo-dimension has zero vector)
        self.assertEqual(ANGLE * LENGTH, LENGTH)
        self.assertEqual(LENGTH * ANGLE, LENGTH)

    def test_pseudo_dimension_acts_as_identity_in_division(self):
        """Test that pseudo-dimensions act as identity when divided."""
        # LENGTH / ANGLE = LENGTH (pseudo-dimension has zero vector)
        self.assertEqual(LENGTH / ANGLE, LENGTH)

    def test_pseudo_dimension_invariant_under_exponentiation(self):
        """Test that pseudo-dimensions are invariant under exponentiation."""
        # ANGLE ** 2 = ANGLE (pseudo-dimensions preserve identity)
        self.assertEqual(ANGLE ** 2, ANGLE)
        self.assertEqual(COUNT ** -1, COUNT)

    def test_different_pseudo_dimensions_cannot_multiply(self):
        """Test that different pseudo-dimensions cannot be combined."""
        with self.assertRaises(TypeError):
            ANGLE * RATIO

    def test_different_pseudo_dimensions_cannot_divide(self):
        """Test that different pseudo-dimensions cannot be divided."""
        with self.assertRaises(TypeError):
            ANGLE / RATIO


class TestDimensionEquality(unittest.TestCase):
    """Test dimension equality and hashing."""

    def test_same_dimension_equals(self):
        """Test that same dimensions are equal."""
        self.assertEqual(LENGTH, LENGTH)
        self.assertEqual(VELOCITY, VELOCITY)

    def test_different_dimensions_not_equal(self):
        """Test that different dimensions are not equal."""
        self.assertNotEqual(LENGTH, MASS)
        self.assertNotEqual(VELOCITY, ACCELERATION)

    def test_hash_consistency(self):
        """Test that equal dimensions have equal hashes."""
        d1 = LENGTH
        d2 = LENGTH
        self.assertEqual(hash(d1), hash(d2))

    def test_derived_same_vector_equals(self):
        """Test that dimensions with same vector are equal."""
        vel1 = LENGTH / TIME
        vel2 = LENGTH / TIME
        self.assertEqual(vel1, vel2)
        self.assertEqual(hash(vel1), hash(vel2))

    def test_dynamic_dimension_equality(self):
        """Test dynamic dimensions with same vector are equal."""
        # Create a dimension not in the registry
        jerk = LENGTH * TIME ** -3
        jerk2 = LENGTH / TIME ** 3
        self.assertEqual(jerk, jerk2)


class TestDimensionBool(unittest.TestCase):
    """Test dimension boolean behavior."""

    def test_none_is_falsy(self):
        """Test that NONE is falsy."""
        self.assertFalse(NONE)

    def test_base_dimensions_are_truthy(self):
        """Test that base dimensions are truthy."""
        self.assertTrue(LENGTH)
        self.assertTrue(MASS)
        self.assertTrue(TIME)

    def test_derived_dimensions_are_truthy(self):
        """Test that derived dimensions are truthy."""
        self.assertTrue(VELOCITY)
        self.assertTrue(FORCE)

    def test_pseudo_dimensions_are_truthy(self):
        """Test that pseudo-dimensions are truthy."""
        self.assertTrue(ANGLE)
        self.assertTrue(RATIO)


class TestDimensionIntrospection(unittest.TestCase):
    """Test dimension introspection methods."""

    def test_is_base_for_base_dimensions(self):
        """Test is_base returns True for base dimensions."""
        self.assertTrue(LENGTH.is_base())
        self.assertTrue(MASS.is_base())
        self.assertTrue(TIME.is_base())
        self.assertTrue(CURRENT.is_base())
        self.assertTrue(TEMPERATURE.is_base())
        self.assertTrue(LUMINOUS_INTENSITY.is_base())
        self.assertTrue(AMOUNT_OF_SUBSTANCE.is_base())
        self.assertTrue(INFORMATION.is_base())

    def test_is_base_for_derived_dimensions(self):
        """Test is_base returns False for derived dimensions."""
        self.assertFalse(VELOCITY.is_base())
        self.assertFalse(FORCE.is_base())
        self.assertFalse(ENERGY.is_base())
        self.assertFalse(AREA.is_base())

    def test_is_pseudo(self):
        """Test is_pseudo property."""
        self.assertTrue(ANGLE.is_pseudo)
        self.assertTrue(RATIO.is_pseudo)
        self.assertTrue(COUNT.is_pseudo)
        self.assertTrue(SOLID_ANGLE.is_pseudo)
        self.assertFalse(LENGTH.is_pseudo)
        self.assertFalse(NONE.is_pseudo)

    def test_is_dimensionless(self):
        """Test is_dimensionless property."""
        self.assertTrue(NONE.is_dimensionless)
        self.assertTrue(ANGLE.is_dimensionless)  # Pseudo-dimensions have zero vector
        self.assertFalse(LENGTH.is_dimensionless)
        self.assertFalse(VELOCITY.is_dimensionless)

    def test_base_expansion_base_dimensions(self):
        """Test base_expansion for base dimensions."""
        exp = LENGTH.base_expansion()
        self.assertEqual(exp, {LENGTH: Fraction(1)})

        exp = MASS.base_expansion()
        self.assertEqual(exp, {MASS: Fraction(1)})

    def test_base_expansion_derived_dimensions(self):
        """Test base_expansion for derived dimensions."""
        exp = VELOCITY.base_expansion()
        self.assertEqual(exp, {TIME: Fraction(-1), LENGTH: Fraction(1)})

        exp = FORCE.base_expansion()
        self.assertEqual(
            exp, {TIME: Fraction(-2), LENGTH: Fraction(1), MASS: Fraction(1)}
        )

    def test_base_expansion_pseudo_dimensions(self):
        """Test base_expansion for pseudo-dimensions."""
        exp = ANGLE.base_expansion()
        self.assertEqual(exp, {})

    def test_basis_function(self):
        """Test the basis() function returns all 8 base dimensions."""
        b = basis()
        self.assertEqual(len(b), 8)
        self.assertIn(TIME, b)
        self.assertIn(LENGTH, b)
        self.assertIn(MASS, b)
        self.assertIn(CURRENT, b)
        self.assertIn(TEMPERATURE, b)
        self.assertIn(LUMINOUS_INTENSITY, b)
        self.assertIn(AMOUNT_OF_SUBSTANCE, b)
        self.assertIn(INFORMATION, b)


class TestResolve(unittest.TestCase):
    """Test the resolve function."""

    def test_resolve_known_vector(self):
        """Test resolving a known vector returns the registered dimension."""
        vec = Vector(
            SI, (Fraction(0), Fraction(1), Fraction(0), Fraction(0),
                 Fraction(0), Fraction(0), Fraction(0), Fraction(0))
        )
        dim = resolve(vec)
        self.assertEqual(dim, LENGTH)

    def test_resolve_velocity_vector(self):
        """Test resolving velocity vector."""
        vec = Vector(
            SI, (Fraction(-1), Fraction(1), Fraction(0), Fraction(0),
                 Fraction(0), Fraction(0), Fraction(0), Fraction(0))
        )
        dim = resolve(vec)
        self.assertEqual(dim, VELOCITY)

    def test_resolve_unknown_vector_creates_derived(self):
        """Test resolving unknown vector creates derived dimension."""
        # T/L (inverse velocity) - not in registry
        vec = Vector(
            SI, (Fraction(1), Fraction(-1), Fraction(0), Fraction(0),
                 Fraction(0), Fraction(0), Fraction(0), Fraction(0))
        )
        dim = resolve(vec)
        self.assertIn("derived", dim.name)

    def test_resolve_zero_vector_returns_none(self):
        """Test resolving zero vector returns NONE."""
        vec = SI.zero_vector()
        dim = resolve(vec)
        self.assertEqual(dim, NONE)


class TestDimensionRepr(unittest.TestCase):
    """Test dimension string representation."""

    def test_repr_named_dimension(self):
        """Test repr for named dimensions."""
        self.assertEqual(repr(LENGTH), "Dimension(length)")
        self.assertEqual(repr(VELOCITY), "Dimension(velocity)")

    def test_repr_none(self):
        """Test repr for NONE."""
        self.assertEqual(repr(NONE), "Dimension(none)")


class TestDimensionRegistry(unittest.TestCase):
    """Test dimension registry behavior."""

    def test_all_base_dimensions_registered(self):
        """Test all base dimensions are in the registry."""
        for dim in basis():
            resolved = resolve(dim.vector)
            self.assertEqual(resolved, dim)

    def test_derived_dimensions_registered(self):
        """Test common derived dimensions are registered."""
        derived = [VELOCITY, ACCELERATION, FORCE, ENERGY, POWER, AREA, VOLUME]
        for dim in derived:
            resolved = resolve(dim.vector)
            self.assertEqual(resolved, dim)


class TestDimensionProperties(unittest.TestCase):
    """Test dimension property accessors."""

    def test_basis_property(self):
        """Test the basis property returns the correct basis."""
        self.assertEqual(LENGTH.basis, SI)
        self.assertEqual(VELOCITY.basis, SI)

    def test_name_property(self):
        """Test the name property."""
        self.assertEqual(LENGTH.name, "length")
        self.assertEqual(VELOCITY.name, "velocity")

    def test_symbol_property(self):
        """Test the symbol property."""
        self.assertEqual(LENGTH.symbol, "L")
        self.assertEqual(TIME.symbol, "T")
        self.assertEqual(MASS.symbol, "M")


if __name__ == "__main__":
    unittest.main()
