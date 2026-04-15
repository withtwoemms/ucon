# © 2025 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""Tests for ucon.checking module."""

import unittest

from ucon import Dimension, Number, units, enforce_dimensions, DimensionConstraint


class TestEnforceDimensions(unittest.TestCase):
    """Tests for the @enforce_dimensions decorator."""

    def test_valid_dimensions_pass(self):
        @enforce_dimensions
        def speed(distance: Number[Dimension.length], time: Number[Dimension.time]) -> Number:
            return distance / time

        result = speed(units.meter(100), units.second(10))
        self.assertEqual(result.quantity, 10.0)

    def test_wrong_dimension_raises_value_error(self):
        @enforce_dimensions
        def speed(distance: Number[Dimension.length], time: Number[Dimension.time]) -> Number:
            return distance / time

        with self.assertRaises(ValueError) as ctx:
            speed(units.second(100), units.second(10))

        self.assertIn("distance", str(ctx.exception))
        self.assertIn("expected dimension 'length'", str(ctx.exception))
        self.assertIn("got 'time'", str(ctx.exception))

    def test_non_number_raises_type_error(self):
        @enforce_dimensions
        def speed(distance: Number[Dimension.length], time: Number[Dimension.time]) -> Number:
            return distance / time

        with self.assertRaises(TypeError) as ctx:
            speed(100, units.second(10))

        self.assertIn("distance", str(ctx.exception))
        self.assertIn("expected Number", str(ctx.exception))
        self.assertIn("got int", str(ctx.exception))

    def test_unconstrained_param_accepts_any_dimension(self):
        @enforce_dimensions
        def mixed(x: Number[Dimension.time], y: Number) -> Number:
            return x

        # y is unconstrained — any dimension OK
        result = mixed(units.second(1), units.meter(5))
        self.assertEqual(result.quantity, 1)

        result = mixed(units.second(1), units.kilogram(5))
        self.assertEqual(result.quantity, 1)

    def test_optional_none_skipped(self):
        @enforce_dimensions
        def optional(x: Number[Dimension.time], y: Number[Dimension.mass] = None):
            return x

        # y defaults to None, should not raise
        result = optional(units.second(1))
        self.assertEqual(result.quantity, 1)

    def test_no_constraints_returns_unwrapped(self):
        @enforce_dimensions
        def no_constraints(x: Number) -> Number:
            return x

        # Function should be returned unwrapped (fast path)
        # We can verify by checking it's the original function
        result = no_constraints(units.meter(5))
        self.assertEqual(result.quantity, 5)

    def test_composite_dimension(self):
        @enforce_dimensions
        def momentum(mass: Number[Dimension.mass], velocity: Number[Dimension.velocity]):
            return mass * velocity

        # m/s is velocity dimension
        v = units.meter(10) / units.second(1)
        result = momentum(units.kilogram(2), v)
        self.assertEqual(result.quantity, 20)

    def test_wrong_composite_dimension_raises(self):
        @enforce_dimensions
        def momentum(mass: Number[Dimension.mass], velocity: Number[Dimension.velocity]):
            return mass * velocity

        # Passing length instead of velocity
        with self.assertRaises(ValueError) as ctx:
            momentum(units.kilogram(2), units.meter(10))

        self.assertIn("velocity", str(ctx.exception))
        self.assertIn("expected dimension 'velocity'", str(ctx.exception))
        self.assertIn("got 'length'", str(ctx.exception))

    def test_positional_and_keyword_args(self):
        @enforce_dimensions
        def speed(distance: Number[Dimension.length], time: Number[Dimension.time]) -> Number:
            return distance / time

        # Positional
        result1 = speed(units.meter(100), units.second(10))
        self.assertEqual(result1.quantity, 10.0)

        # Keyword
        result2 = speed(distance=units.meter(100), time=units.second(10))
        self.assertEqual(result2.quantity, 10.0)

        # Mixed
        result3 = speed(units.meter(100), time=units.second(10))
        self.assertEqual(result3.quantity, 10.0)

    def test_preserves_function_metadata(self):
        @enforce_dimensions
        def documented(x: Number[Dimension.length]) -> Number:
            """This is the docstring."""
            return x

        self.assertEqual(documented.__name__, "documented")
        self.assertEqual(documented.__doc__, "This is the docstring.")

    def test_derived_dimension_in_error_message(self):
        # Create a derived dimension that doesn't match a named one
        @enforce_dimensions
        def needs_velocity(v: Number[Dimension.velocity]):
            return v

        # Pass volume/time which is a different derived dimension
        volume_flow = units.meter(1) * units.meter(1) * units.meter(1) / units.second(1)

        with self.assertRaises(ValueError) as ctx:
            needs_velocity(volume_flow)

        # Error should use readable derived dimension name
        error_msg = str(ctx.exception)
        self.assertIn("v", error_msg)
        self.assertIn("velocity", error_msg)
        # Should show readable format, not Vector(...)
        self.assertNotIn("Vector", error_msg)


class TestGetDimension(unittest.TestCase):
    """Tests for the _get_dimension helper."""

    def test_extracts_dimension_from_unit_product(self):
        from ucon.checking import _get_dimension
        n = units.meter(5)
        dim = _get_dimension(n)
        self.assertEqual(dim, Dimension.length)

    def test_raises_type_error_for_non_unit(self):
        from ucon.checking import _get_dimension
        # Construct a Number whose .unit is neither Unit nor UnitProduct
        n = Number.__new__(Number)
        object.__setattr__(n, '_quantity', 1.0)
        object.__setattr__(n, '_uncertainty', None)
        object.__setattr__(n, '_unit', "not_a_unit")
        with self.assertRaises(TypeError) as ctx:
            _get_dimension(n)
        self.assertIn("Cannot extract dimension", str(ctx.exception))


class TestDimensionsCompatible(unittest.TestCase):
    """Tests for the _dimensions_compatible function."""

    def test_same_dimension_is_compatible(self):
        from ucon.checking import _dimensions_compatible
        self.assertTrue(_dimensions_compatible(Dimension.length, Dimension.length))

    def test_different_dimension_same_basis_incompatible(self):
        from ucon.checking import _dimensions_compatible
        self.assertFalse(_dimensions_compatible(Dimension.length, Dimension.time))

    def test_cross_basis_compatible(self):
        """CGS dynamic_viscosity is compatible with SI dynamic_viscosity."""
        from ucon.checking import _dimensions_compatible
        cgs_dim = units.poise.dimension
        si_dim = Dimension.dynamic_viscosity
        self.assertNotEqual(cgs_dim.vector.basis, si_dim.vector.basis)
        self.assertTrue(_dimensions_compatible(cgs_dim, si_dim))

    def test_cross_basis_incompatible(self):
        """CGS dynamic_viscosity is NOT compatible with SI energy."""
        from ucon.checking import _dimensions_compatible
        cgs_dim = units.poise.dimension
        si_dim = Dimension.energy
        self.assertFalse(_dimensions_compatible(cgs_dim, si_dim))

    def test_no_transform_path_returns_false(self):
        """Dimensions with no BasisGraph path are incompatible."""
        from ucon.checking import _dimensions_compatible
        from ucon.dimension import Dimension as DimClass
        from ucon.basis import Basis, Vector

        # Create a dimension on a fictitious basis with no transforms registered
        fake_basis = Basis("FakeBasis", ["x", "y"])
        fake_vector = Vector(fake_basis, (1, 0))
        fake_dim = DimClass(fake_vector, name="fake_length")

        self.assertFalse(_dimensions_compatible(fake_dim, Dimension.length))


class TestEnforceDimensionsCrossBasis(unittest.TestCase):
    """Tests for @enforce_dimensions with cross-basis units."""

    def test_cgs_poise_accepted_for_si_dynamic_viscosity(self):
        @enforce_dimensions
        def viscosity_fn(mu: Number[Dimension.dynamic_viscosity]) -> Number:
            return mu

        # poise is CGS, constraint is SI dynamic_viscosity
        result = viscosity_fn(units.poise(1.0))
        self.assertEqual(result.quantity, 1.0)

    def test_cgs_unit_rejected_for_wrong_si_dimension(self):
        @enforce_dimensions
        def energy_fn(e: Number[Dimension.energy]) -> Number:
            return e

        with self.assertRaises(ValueError):
            energy_fn(units.poise(1.0))


class TestDimensionConstraint(unittest.TestCase):
    """Tests for the DimensionConstraint marker class."""

    def test_equality(self):
        c1 = DimensionConstraint(Dimension.time)
        c2 = DimensionConstraint(Dimension.time)
        c3 = DimensionConstraint(Dimension.mass)

        self.assertEqual(c1, c2)
        self.assertNotEqual(c1, c3)

    def test_hash(self):
        c1 = DimensionConstraint(Dimension.time)
        c2 = DimensionConstraint(Dimension.time)

        self.assertEqual(hash(c1), hash(c2))
        self.assertIn(c1, {c2})

    def test_repr(self):
        c = DimensionConstraint(Dimension.time)
        self.assertEqual(repr(c), "DimensionConstraint(time)")


if __name__ == "__main__":
    unittest.main()
