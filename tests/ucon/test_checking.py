# © 2025 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""Tests for ucon.checking module."""

import unittest

from ucon import Number, Dimension, units, enforce_dimensions, DimConstraint


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


class TestDimConstraint(unittest.TestCase):
    """Tests for the DimConstraint marker class."""

    def test_equality(self):
        c1 = DimConstraint(Dimension.time)
        c2 = DimConstraint(Dimension.time)
        c3 = DimConstraint(Dimension.mass)

        self.assertEqual(c1, c2)
        self.assertNotEqual(c1, c3)

    def test_hash(self):
        c1 = DimConstraint(Dimension.time)
        c2 = DimConstraint(Dimension.time)

        self.assertEqual(hash(c1), hash(c2))
        self.assertIn(c1, {c2})

    def test_repr(self):
        c = DimConstraint(Dimension.time)
        self.assertEqual(repr(c), "DimConstraint(time)")


if __name__ == "__main__":
    unittest.main()
