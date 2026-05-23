# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
Tests for the new Dimension dataclass in ucon.dimension.
"""

import unittest
from fractions import Fraction

from ucon.dimension import Dimension, resolve, basis, SI
from ucon.basis import Vector


class TestDimensionConstruction(unittest.TestCase):
    """Test Dimension construction methods."""

    def test_from_components_basic(self):
        """Test creating dimension from named components."""
        velocity = Dimension.from_components(L=1, T=-1, name="velocity")
        self.assertEqual(velocity, Dimension.velocity)

    def test_from_components_using_symbols(self):
        """Test creating dimension using symbol names."""
        # Using symbol names instead of full names
        dim = Dimension.from_components(L=1, name="length_test")
        self.assertEqual(dim.vector, Dimension.length.vector)

    def test_from_components_derived(self):
        """Test creating complex derived dimension."""
        # Force = M*L/T^2
        force = Dimension.from_components(M=1, L=1, T=-2, name="force")
        self.assertEqual(force, Dimension.force)

    def test_pseudo_dimension(self):
        """Test creating pseudo-dimension."""
        angle = Dimension.pseudo("angle", name="angle")
        self.assertTrue(angle.is_pseudo)
        self.assertEqual(angle.tag, "angle")
        self.assertTrue(angle.is_dimensionless)

    def test_pseudo_dimensions_are_distinct(self):
        """Test that pseudo-dimensions with different tags are not equal."""
        self.assertNotEqual(Dimension.angle, Dimension.ratio)
        self.assertNotEqual(Dimension.angle, Dimension.count)
        self.assertNotEqual(Dimension.ratio, Dimension.solid_angle)

    def test_pseudo_dimensions_not_equal_to_none(self):
        """Test that pseudo-dimensions are not equal to Dimension.none."""
        self.assertNotEqual(Dimension.angle, Dimension.none)
        self.assertNotEqual(Dimension.ratio, Dimension.none)
        self.assertNotEqual(Dimension.count, Dimension.none)
        self.assertNotEqual(Dimension.solid_angle, Dimension.none)


class TestDimensionAlgebra(unittest.TestCase):
    """Test dimension algebraic operations."""

    def test_multiplication_creates_derived_dimension(self):
        """Test that multiplication produces correct derived dimensions."""
        self.assertEqual(Dimension.mass * Dimension.acceleration, Dimension.force)
        self.assertEqual(Dimension.length * Dimension.length, Dimension.area)
        self.assertEqual(Dimension.length * Dimension.length * Dimension.length, Dimension.volume)

    def test_division_creates_derived_dimension(self):
        """Test that division produces correct derived dimensions."""
        self.assertEqual(Dimension.length / Dimension.time, Dimension.velocity)
        self.assertEqual(Dimension.force / Dimension.area, Dimension.pressure)
        self.assertEqual(Dimension.energy / Dimension.time, Dimension.power)

    def test_power_creates_derived_dimension(self):
        """Test that exponentiation produces correct derived dimensions."""
        self.assertEqual(Dimension.length ** 2, Dimension.area)
        self.assertEqual(Dimension.length ** 3, Dimension.volume)
        self.assertEqual(Dimension.time ** -1, Dimension.frequency)

    def test_power_zero_returns_none(self):
        """Test that power of 0 returns Dimension.none."""
        self.assertEqual(Dimension.length ** 0, Dimension.none)
        self.assertEqual(Dimension.mass ** 0, Dimension.none)

    def test_power_one_returns_same(self):
        """Test that power of 1 returns the same dimension."""
        self.assertIs(Dimension.length ** 1, Dimension.length)
        self.assertIs(Dimension.mass ** 1, Dimension.mass)

    def test_fractional_power(self):
        """Test fractional exponents create derived dimensions."""
        sqrt_length = Dimension.length ** Fraction(1, 2)
        self.assertIsInstance(sqrt_length, Dimension)
        self.assertNotEqual(sqrt_length, Dimension.length)

    def test_composite_expression(self):
        """Test complex composite expressions."""
        # Energy = Force * Length = (M*L/T^2) * L = M*L^2/T^2
        energy_via_force = Dimension.force * Dimension.length
        self.assertEqual(energy_via_force, Dimension.energy)

        # Power = Energy / Time
        power_via_energy = Dimension.energy / Dimension.time
        self.assertEqual(power_via_energy, Dimension.power)

    def test_charge_equals_current_times_time(self):
        """Test that Charge = Current * Time."""
        self.assertEqual(Dimension.current * Dimension.time, Dimension.charge)

    def test_pseudo_dimension_acts_as_identity_in_multiplication(self):
        """Test that pseudo-dimensions act as identity when multiplied with regular dimensions."""
        # Dimension.angle * Dimension.length = Dimension.length (pseudo-dimension has zero vector)
        self.assertEqual(Dimension.angle * Dimension.length, Dimension.length)
        self.assertEqual(Dimension.length * Dimension.angle, Dimension.length)

    def test_pseudo_dimension_acts_as_identity_in_division(self):
        """Test that pseudo-dimensions act as identity when divided."""
        # Dimension.length / Dimension.angle = Dimension.length (pseudo-dimension has zero vector)
        self.assertEqual(Dimension.length / Dimension.angle, Dimension.length)

    def test_pseudo_dimension_invariant_under_exponentiation(self):
        """Test that pseudo-dimensions are invariant under exponentiation."""
        # Dimension.angle ** 2 = Dimension.angle (pseudo-dimensions preserve identity)
        self.assertEqual(Dimension.angle ** 2, Dimension.angle)
        self.assertEqual(Dimension.count ** -1, Dimension.count)

    def test_different_pseudo_dimensions_cannot_multiply(self):
        """Test that different pseudo-dimensions cannot be combined."""
        with self.assertRaises(TypeError):
            Dimension.angle * Dimension.ratio

    def test_different_pseudo_dimensions_cannot_divide(self):
        """Test that different pseudo-dimensions cannot be divided."""
        with self.assertRaises(TypeError):
            Dimension.angle / Dimension.ratio

    def test_same_pseudo_multiplied_yields_self(self):
        """``ANGLE * ANGLE == ANGLE``.

        Pins the ``self.is_pseudo and other.is_pseudo and self == other``
        branch in ``Dimension.__mul__`` (where the same pseudo combines
        to itself rather than 0+0=0 promoting to NONE).
        """
        self.assertEqual(Dimension.angle * Dimension.angle, Dimension.angle)
        self.assertEqual(Dimension.ratio * Dimension.ratio, Dimension.ratio)
        self.assertEqual(Dimension.count * Dimension.count, Dimension.count)

    def test_same_pseudo_divided_yields_none(self):
        """``ANGLE / ANGLE == NONE``.

        Pins the same-pseudo division branch: the algebra collapses to
        the dimensionless identity, distinguishing it from the
        ``ANGLE * ANGLE = ANGLE`` invariant.
        """
        self.assertEqual(Dimension.angle / Dimension.angle, Dimension.none)
        self.assertEqual(Dimension.ratio / Dimension.ratio, Dimension.none)
        self.assertEqual(Dimension.count / Dimension.count, Dimension.none)

    def test_pseudo_divided_by_regular_acts_as_none(self):
        """``ANGLE / LENGTH == 1/LENGTH``.

        Covers the ``pseudo / regular`` branch in ``Dimension.__truediv__``
        which routes through ``ops.divide_via``. Pseudo-dimensions carry
        the zero vector, so the result is the inverse of the regular
        operand — i.e. ``wavenumber`` for ``1/length``.
        """
        self.assertEqual(Dimension.angle / Dimension.length, Dimension.wavenumber)
        self.assertEqual(Dimension.ratio / Dimension.time, Dimension.frequency)


class TestDimensionAlgebraOpsRouting(unittest.TestCase):
    """``Dimension.__mul__`` / ``__truediv__`` route through
    :mod:`ucon.basis.ops` instead of operating on ``Vector`` directly.

    The same-basis fast path is exercised throughout
    :class:`TestDimensionAlgebra`; these tests pin the cross-basis path
    where ``ops.multiply_via`` / ``divide_via`` must consult the active
    :class:`~ucon.basis.BasisGraph` to project operands into a shared
    basis before composing.
    """

    def test_cross_basis_multiplication_routes_via_ops(self):
        """SI length * CGS length yields an area-shaped dimension via
        graph-mediated projection."""
        from ucon.basis.builtin import CGS

        si_length = Dimension.length
        cgs_length = Dimension.from_components(CGS, length=1)
        result = si_length * cgs_length
        # Result must be 2-D in length; basis is whichever side the
        # graph projected into (SI is the canonical hub, but either is
        # acceptable so long as the structure is right).
        # ``length`` exponent in the result must be 2.
        length_axis = next(
            i for i, c in enumerate(result.vector.basis) if c.name == "length"
        )
        self.assertEqual(result.vector.components[length_axis], 2)

    def test_cross_basis_division_routes_via_ops(self):
        """SI length / CGS time yields a velocity-shaped dimension via
        graph-mediated projection."""
        from ucon.basis.builtin import CGS

        si_length = Dimension.length
        cgs_time = Dimension.from_components(CGS, time=1)
        result = si_length / cgs_time
        # length=+1, time=-1 in the projected basis.
        length_axis = next(
            i for i, c in enumerate(result.vector.basis) if c.name == "length"
        )
        time_axis = next(
            i for i, c in enumerate(result.vector.basis) if c.name == "time"
        )
        self.assertEqual(result.vector.components[length_axis], 1)
        self.assertEqual(result.vector.components[time_axis], -1)

    def test_cross_basis_with_no_transform_path_raises(self):
        """If the active graph has no path between the operand bases,
        the underlying ``BasisMismatch`` from ``ops`` surfaces as
        :class:`ValueError` to the caller."""
        from ucon.basis import Basis, BasisComponent, BasisGraph, using_basis_graph

        isolated = Basis("isolated", [BasisComponent("phlogiston", "Φ")])
        with using_basis_graph(BasisGraph()):  # empty graph — no SI ↔ isolated
            phlogiston = Dimension.from_components(isolated, phlogiston=1)
            with self.assertRaises(ValueError):
                Dimension.length * phlogiston


class TestDimensionAlgebraCacheKeying(unittest.TestCase):
    """Regression tests for Dimension algebra caches.

    The mul/div/pow caches in ucon.dimension were originally keyed by
    ``(id(self), id(other))``. Because ``id()`` is only unique among
    simultaneously-living objects, garbage-collected transient ``Dimension``
    instances could have their ids reused by later allocations, causing
    stale cache hits to return the wrong dimension. This surfaced on
    Python 3.13 in ``parse_dimension`` test sequences where parsing
    ``"L^2"`` followed by ``"M*L/T^2"`` returned ``linear_density``
    instead of ``force`` (because ``T**2`` hit the cached ``L**2 = AREA``
    entry under a reused id, turning ``M*L/T^2`` into ``M*L/L^2``).

    The caches are now keyed by the dimensions themselves, which use
    structural hash/eq on ``(vector, tag)``. These tests pin the
    invariants the new keying must preserve.
    """

    def test_distinct_instances_with_equal_content_produce_equal_results(self):
        """Two distinct Dimension instances with identical content must
        produce identical results across all algebraic operations.
        """
        a = Dimension.from_components(SI, length=1)
        b = Dimension.from_components(SI, length=1)
        self.assertIsNot(a, b)
        self.assertEqual(a, b)
        self.assertEqual(a, Dimension.length)

        # Power: must not depend on which instance you use
        self.assertEqual(a ** 2, Dimension.area)
        self.assertEqual(b ** 2, Dimension.area)
        self.assertEqual(a ** 2, b ** 2)

        # Multiplication
        self.assertEqual(a * a, Dimension.area)
        self.assertEqual(b * b, Dimension.area)
        self.assertEqual(a * b, Dimension.area)

        # Division
        self.assertEqual(a / b, Dimension.none)
        t = Dimension.from_components(SI, time=1)
        self.assertEqual(a / t, Dimension.velocity)

    def test_parse_dimension_sequence_after_gc(self):
        """Parsing ``L^2`` then ``M*L/T^2`` must return AREA then FORCE,
        regardless of GC reaping the transient dimensions in between.

        This is the exact failure path that broke on Python 3.13 with the
        old id-keyed caches: the freed id of the transient ``L`` from the
        area parse could be reassigned to the transient ``T`` of the force
        parse, causing ``T**2`` to hit the stale ``L**2 = AREA`` cache
        entry and turn ``M*L/T^2`` into ``M*L/L^2 = linear_density``.
        """
        import gc

        from ucon import parse_dimension

        self.assertEqual(parse_dimension("L^2"), Dimension.area)
        gc.collect()  # encourage id reuse for the next parse

        self.assertEqual(parse_dimension("M*L/T^2"), Dimension.force)
        self.assertEqual(parse_dimension("M\u00b7L/T^2"), Dimension.force)
        self.assertEqual(parse_dimension("M\u22c5L/T^2"), Dimension.force)


class TestDimensionAlgebraCacheRouting(unittest.TestCase):
    """v1.8: ``Dimension`` algebra routes through ``UnitSystem._algebra_cache``.

    Outside any ``use(...)`` block the module-level ``_DEFAULT_ALGEBRA_CACHE``
    is consulted (stable across calls). Inside a ``use(system)`` block the
    active system's per-instance ``AlgebraCache`` is consulted instead.
    """

    def test_default_state_populates_active_system_cache(self):
        """v1.11: With eager init, algebra always routes through the active system cache."""
        from ucon.system import active
        cache = active()._algebra_cache
        cache.clear()
        _ = Dimension.length * Dimension.time
        self.assertGreater(len(cache.mul), 0)

    def test_use_block_routes_to_system_cache(self):
        from ucon.system import UnitSystem, use
        system = UnitSystem.from_globals()
        system._algebra_cache.clear()
        with use(system):
            _ = Dimension.length * Dimension.time
            _ = Dimension.length / Dimension.time
            _ = Dimension.length ** 3
        self.assertGreater(len(system._algebra_cache.mul), 0)
        self.assertGreater(len(system._algebra_cache.div), 0)
        self.assertGreater(len(system._algebra_cache.pow), 0)

    def test_legacy_dim_mul_cache_alias_emits_pending_deprecation(self):
        import warnings

        import ucon.dimension as dim_mod
        from ucon.system import _get_active_cache

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            alias = dim_mod._DIM_MUL_CACHE
        self.assertTrue(
            any(issubclass(w.category, PendingDeprecationWarning) for w in caught)
        )
        self.assertIs(alias, _get_active_cache().mul)

    def test_legacy_dim_div_cache_alias_points_at_active_cache(self):
        import warnings

        import ucon.dimension as dim_mod
        from ucon.system import _get_active_cache

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            alias = dim_mod._DIM_DIV_CACHE
        self.assertIs(alias, _get_active_cache().div)

    def test_legacy_dim_pow_cache_alias_points_at_active_cache(self):
        import warnings

        import ucon.dimension as dim_mod
        from ucon.system import _get_active_cache

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            alias = dim_mod._DIM_POW_CACHE
        self.assertIs(alias, _get_active_cache().pow)

    def test_unknown_module_attribute_still_raises(self):
        import ucon.dimension as dim_mod
        with self.assertRaises(AttributeError):
            dim_mod._DIM_NOT_A_CACHE


class TestDimensionEquality(unittest.TestCase):
    """Test dimension equality and hashing."""

    def test_same_dimension_equals(self):
        """Test that same dimensions are equal."""
        self.assertEqual(Dimension.length, Dimension.length)
        self.assertEqual(Dimension.velocity, Dimension.velocity)

    def test_different_dimensions_not_equal(self):
        """Test that different dimensions are not equal."""
        self.assertNotEqual(Dimension.length, Dimension.mass)
        self.assertNotEqual(Dimension.velocity, Dimension.acceleration)

    def test_hash_consistency(self):
        """Test that equal dimensions have equal hashes."""
        d1 = Dimension.length
        d2 = Dimension.length
        self.assertEqual(hash(d1), hash(d2))

    def test_derived_same_vector_equals(self):
        """Test that dimensions with same vector are equal."""
        vel1 = Dimension.length / Dimension.time
        vel2 = Dimension.length / Dimension.time
        self.assertEqual(vel1, vel2)
        self.assertEqual(hash(vel1), hash(vel2))

    def test_dynamic_dimension_equality(self):
        """Test dynamic dimensions with same vector are equal."""
        # Create a dimension not in the registry
        jerk = Dimension.length * Dimension.time ** -3
        jerk2 = Dimension.length / Dimension.time ** 3
        self.assertEqual(jerk, jerk2)


class TestDimensionBool(unittest.TestCase):
    """Test dimension boolean behavior."""

    def test_none_is_falsy(self):
        """Test that Dimension.none is falsy."""
        self.assertFalse(Dimension.none)

    def test_base_dimensions_are_truthy(self):
        """Test that base dimensions are truthy."""
        self.assertTrue(Dimension.length)
        self.assertTrue(Dimension.mass)
        self.assertTrue(Dimension.time)

    def test_derived_dimensions_are_truthy(self):
        """Test that derived dimensions are truthy."""
        self.assertTrue(Dimension.velocity)
        self.assertTrue(Dimension.force)

    def test_pseudo_dimensions_are_truthy(self):
        """Test that pseudo-dimensions are truthy."""
        self.assertTrue(Dimension.angle)
        self.assertTrue(Dimension.ratio)


class TestDimensionIntrospection(unittest.TestCase):
    """Test dimension introspection methods."""

    def test_is_base_for_base_dimensions(self):
        """Test is_base returns True for base dimensions."""
        self.assertTrue(Dimension.length.is_base())
        self.assertTrue(Dimension.mass.is_base())
        self.assertTrue(Dimension.time.is_base())
        self.assertTrue(Dimension.current.is_base())
        self.assertTrue(Dimension.temperature.is_base())
        self.assertTrue(Dimension.luminous_intensity.is_base())
        self.assertTrue(Dimension.amount_of_substance.is_base())
        self.assertTrue(Dimension.information.is_base())

    def test_is_base_for_derived_dimensions(self):
        """Test is_base returns False for derived dimensions."""
        self.assertFalse(Dimension.velocity.is_base())
        self.assertFalse(Dimension.force.is_base())
        self.assertFalse(Dimension.energy.is_base())
        self.assertFalse(Dimension.area.is_base())

    def test_is_pseudo(self):
        """Test is_pseudo property."""
        self.assertTrue(Dimension.angle.is_pseudo)
        self.assertTrue(Dimension.ratio.is_pseudo)
        self.assertTrue(Dimension.count.is_pseudo)
        self.assertTrue(Dimension.solid_angle.is_pseudo)
        self.assertFalse(Dimension.length.is_pseudo)
        self.assertFalse(Dimension.none.is_pseudo)

    def test_is_dimensionless(self):
        """Test is_dimensionless property."""
        self.assertTrue(Dimension.none.is_dimensionless)
        self.assertTrue(Dimension.angle.is_dimensionless)  # Pseudo-dimensions have zero vector
        self.assertFalse(Dimension.length.is_dimensionless)
        self.assertFalse(Dimension.velocity.is_dimensionless)

    def test_base_expansion_base_dimensions(self):
        """Test base_expansion for base dimensions."""
        exp = Dimension.length.base_expansion()
        self.assertEqual(exp, {Dimension.length: Fraction(1)})

        exp = Dimension.mass.base_expansion()
        self.assertEqual(exp, {Dimension.mass: Fraction(1)})

    def test_base_expansion_derived_dimensions(self):
        """Test base_expansion for derived dimensions."""
        exp = Dimension.velocity.base_expansion()
        self.assertEqual(exp, {Dimension.time: Fraction(-1), Dimension.length: Fraction(1)})

        exp = Dimension.force.base_expansion()
        self.assertEqual(
            exp, {Dimension.time: Fraction(-2), Dimension.length: Fraction(1), Dimension.mass: Fraction(1)}
        )

    def test_base_expansion_pseudo_dimensions(self):
        """Test base_expansion for pseudo-dimensions."""
        exp = Dimension.angle.base_expansion()
        self.assertEqual(exp, {})

    def test_basis_function(self):
        """Test the basis() function returns all 8 base dimensions."""
        b = basis()
        self.assertEqual(len(b), 8)
        self.assertIn(Dimension.time, b)
        self.assertIn(Dimension.length, b)
        self.assertIn(Dimension.mass, b)
        self.assertIn(Dimension.current, b)
        self.assertIn(Dimension.temperature, b)
        self.assertIn(Dimension.luminous_intensity, b)
        self.assertIn(Dimension.amount_of_substance, b)
        self.assertIn(Dimension.information, b)


class TestResolve(unittest.TestCase):
    """Test the resolve function."""

    def test_resolve_known_vector(self):
        """Test resolving a known vector returns the registered dimension."""
        vec = Vector(
            SI, (Fraction(0), Fraction(1), Fraction(0), Fraction(0),
                 Fraction(0), Fraction(0), Fraction(0), Fraction(0))
        )
        dim = resolve(vec)
        self.assertEqual(dim, Dimension.length)

    def test_resolve_velocity_vector(self):
        """Test resolving velocity vector."""
        vec = Vector(
            SI, (Fraction(-1), Fraction(1), Fraction(0), Fraction(0),
                 Fraction(0), Fraction(0), Fraction(0), Fraction(0))
        )
        dim = resolve(vec)
        self.assertEqual(dim, Dimension.velocity)

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
        """Test resolving zero vector returns Dimension.none."""
        vec = Vector.zero(SI)
        dim = resolve(vec)
        self.assertEqual(dim, Dimension.none)


class TestDimensionRepr(unittest.TestCase):
    """Test dimension string representation."""

    def test_repr_named_dimension(self):
        """Test repr for named dimensions."""
        self.assertEqual(repr(Dimension.length), "Dimension(length)")
        self.assertEqual(repr(Dimension.velocity), "Dimension(velocity)")

    def test_repr_none(self):
        """Test repr for Dimension.none."""
        self.assertEqual(repr(Dimension.none), "Dimension(none)")

    def test_repr_unnamed_dimension_falls_back_to_vector(self):
        """Dimensions constructed without a name repr as their vector."""
        from ucon.basis.builtin import CGS

        # A CGS-basis dimension is not in the SI _REGISTRY and is created
        # without a ``name``, exercising the ``__repr__`` fallback branch.
        cgs_length = Dimension.from_components(CGS, length=1)
        self.assertFalse(cgs_length.name)
        rendered = repr(cgs_length)
        self.assertTrue(rendered.startswith("Dimension(Vector("))
        self.assertIn("CGS", rendered)


class TestDimensionMetaDir(unittest.TestCase):
    """The ``_DimensionMeta.__dir__`` surface backs IDE discoverability."""

    def test_dir_includes_registered_dimensions(self):
        """``dir(Dimension)`` exposes attribute-style dimension names."""
        names = dir(Dimension)
        for expected in ("length", "mass", "time", "velocity", "force"):
            self.assertIn(expected, names)

    def test_dir_includes_type_object_dunders(self):
        """``dir(Dimension)`` still includes the underlying ``type`` members."""
        names = dir(Dimension)
        # The metaclass ``__dir__`` returns ``super().__dir__() + …``, so the
        # standard dataclass / object protocol surface remains visible.
        self.assertIn("__class__", names)
        self.assertIn("__init__", names)
        self.assertIn("__eq__", names)


class TestDimensionRegistry(unittest.TestCase):
    """Test dimension registry behavior."""

    def test_all_base_dimensions_registered(self):
        """Test all base dimensions are in the registry."""
        for dim in basis():
            resolved = resolve(dim.vector)
            self.assertEqual(resolved, dim)

    def test_derived_dimensions_registered(self):
        """Test common derived dimensions are registered."""
        derived = [Dimension.velocity, Dimension.acceleration, Dimension.force, Dimension.energy, Dimension.power, Dimension.area, Dimension.volume]
        for dim in derived:
            resolved = resolve(dim.vector)
            self.assertEqual(resolved, dim)


class TestDimensionProperties(unittest.TestCase):
    """Test dimension property accessors."""

    def test_basis_property(self):
        """Test the basis property returns the correct basis."""
        self.assertEqual(Dimension.length.basis, SI)
        self.assertEqual(Dimension.velocity.basis, SI)

    def test_name_property(self):
        """Test the name property."""
        self.assertEqual(Dimension.length.name, "length")
        self.assertEqual(Dimension.velocity.name, "velocity")

    def test_symbol_property(self):
        """Test the symbol property."""
        self.assertEqual(Dimension.length.symbol, "L")
        self.assertEqual(Dimension.time.symbol, "T")
        self.assertEqual(Dimension.mass.symbol, "M")


if __name__ == "__main__":
    unittest.main()
