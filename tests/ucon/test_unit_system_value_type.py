# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Tests for the ``ucon.system.UnitSystem`` value type and its
``use`` / ``active`` context-var plumbing.
"""

import sys
import unittest

if sys.version_info >= (3, 9):
    from typing import Annotated
else:
    # Python 3.7 and 3.8: typing.Annotated is unavailable. Use the
    # typing_extensions backport so get_origin() in ucon.checking still
    # recognises the annotation.
    from typing_extensions import Annotated

from ucon.system import (
    AlgebraCache,
    BaseUnits,
    UnitSystem,
    active,
    use,
)


class TestAlgebraCache(unittest.TestCase):
    def test_default_construction_empty(self):
        cache = AlgebraCache()
        self.assertEqual(cache.mul, {})
        self.assertEqual(cache.div, {})
        self.assertEqual(cache.pow, {})

    def test_clear_empties_all_subcaches(self):
        cache = AlgebraCache()
        cache.mul["a"] = 1
        cache.div["b"] = 2
        cache.pow["c"] = 3
        cache.clear()
        self.assertEqual(cache.mul, {})
        self.assertEqual(cache.div, {})
        self.assertEqual(cache.pow, {})

    def test_independent_instances(self):
        c1 = AlgebraCache()
        c2 = AlgebraCache()
        c1.mul["x"] = 99
        self.assertNotIn("x", c2.mul)


class TestUnitSystemFromGlobals(unittest.TestCase):
    def test_from_globals_returns_unitsystem(self):
        system = UnitSystem.from_globals()
        self.assertIsInstance(system, UnitSystem)

    def test_from_globals_populates_required_fields(self):
        system = UnitSystem.from_globals()
        # Type-level checks; the actual concrete types live in modules
        # that import each other in nontrivial ways.
        self.assertIsNotNone(system.basis)
        self.assertIsInstance(system.units, dict)
        self.assertIsInstance(system.dimensions, dict)
        self.assertIsInstance(system.base_units, BaseUnits)
        self.assertIsNotNone(system.conversions)
        self.assertIsNotNone(system.basis_graph)
        self.assertIsInstance(system.contexts, dict)
        self.assertIsInstance(system.constants, dict)
        self.assertIsInstance(system._algebra_cache, AlgebraCache)

    def test_base_units_field_is_baseunits(self):
        system = UnitSystem.from_globals()
        self.assertIsInstance(system.base_units, BaseUnits)
        self.assertEqual(system.base_units.name, "SI")

    def test_from_globals_contains_meter_in_units(self):
        system = UnitSystem.from_globals()
        self.assertIn("meter", system.units)


class TestUnitSystemValueSemantics(unittest.TestCase):
    def test_two_snapshots_are_equal(self):
        s1 = UnitSystem.from_globals()
        s2 = UnitSystem.from_globals()
        # Same global registries -> equal
        self.assertEqual(s1, s2)

    def test_equal_systems_share_hash(self):
        s1 = UnitSystem.from_globals()
        s2 = UnitSystem.from_globals()
        self.assertEqual(hash(s1), hash(s2))

    def test_hashable(self):
        # Must be usable in a set
        s = UnitSystem.from_globals()
        bucket = {s}
        self.assertIn(s, bucket)

    def test_frozen_assignment_raises(self):
        s = UnitSystem.from_globals()
        with self.assertRaises(Exception):
            s.basis = None

    def test_unequal_to_non_unitsystem(self):
        s = UnitSystem.from_globals()
        self.assertNotEqual(s, "not a system")
        self.assertNotEqual(s, 42)


class TestActiveAndUse(unittest.TestCase):
    def test_active_returns_unitsystem(self):
        system = active()
        self.assertIsInstance(system, UnitSystem)

    def test_active_snapshots_when_no_use_block(self):
        # Two calls outside a `use` block should each produce equal snapshots.
        s1 = active()
        s2 = active()
        self.assertEqual(s1, s2)

    def test_use_sets_active_inside_block(self):
        custom = UnitSystem.from_globals()
        with use(custom):
            self.assertIs(active(), custom)

    def test_use_restores_active_on_exit(self):
        # Outside the block, active() must not return the custom system
        # (it returns a fresh snapshot).
        custom = UnitSystem.from_globals()
        with use(custom):
            pass
        # After exit, no custom system is bound: active() yields a snapshot,
        # not `custom` by identity.
        self.assertIsNot(active(), custom)

    def test_use_nested_blocks_unwind_correctly(self):
        outer = UnitSystem.from_globals()
        inner = UnitSystem.from_globals()
        with use(outer):
            self.assertIs(active(), outer)
            with use(inner):
                self.assertIs(active(), inner)
            self.assertIs(active(), outer)
        self.assertIsNot(active(), outer)


class TestPublicSurface(unittest.TestCase):
    def test_baseunits_importable_from_ucon_system(self):
        from ucon.system import BaseUnits as BU  # noqa: F401
        self.assertIs(BU, BaseUnits)

    def test_unitsystem_importable_from_ucon_system(self):
        from ucon.system import UnitSystem as US  # noqa: F401
        self.assertIs(US, UnitSystem)

    def test_use_and_active_importable_from_ucon_system(self):
        from ucon.system import active as a, use as u  # noqa: F401
        self.assertTrue(callable(a))
        self.assertTrue(callable(u))


class TestFromGlobalsOverride(unittest.TestCase):
    """Cover the ``base_units`` keyword override path in ``from_globals``."""

    def test_default_base_units_is_si(self):
        from ucon import units as _units_module
        system = UnitSystem.from_globals()
        self.assertIs(system.base_units, _units_module.si)

    def test_override_base_units_is_used_verbatim(self):
        from ucon import Dimension, units as _units_module
        custom = BaseUnits(
            name="length-only", bases={Dimension.length: _units_module.meter}
        )
        system = UnitSystem.from_globals(base_units=custom)
        self.assertIs(system.base_units, custom)
        self.assertEqual(system.base_units.name, "length-only")

    def test_override_does_not_affect_other_fields(self):
        from ucon import Dimension, units as _units_module
        custom = BaseUnits(
            name="length-only", bases={Dimension.length: _units_module.meter}
        )
        baseline = UnitSystem.from_globals()
        overridden = UnitSystem.from_globals(base_units=custom)
        self.assertIs(overridden.units, baseline.units)
        self.assertIs(overridden.dimensions, baseline.dimensions)
        self.assertIs(overridden.conversions, baseline.conversions)
        self.assertIs(overridden.basis_graph, baseline.basis_graph)


class TestUnitSystemDifferentialEquality(unittest.TestCase):
    """Each field's contribution to UnitSystem ``__eq__`` semantics."""

    def _twin(self, base, **overrides):
        kwargs = {
            "basis": base.basis,
            "units": base.units,
            "dimensions": base.dimensions,
            "base_units": base.base_units,
            "conversions": base.conversions,
            "basis_graph": base.basis_graph,
            "contexts": base.contexts,
            "constants": base.constants,
        }
        kwargs.update(overrides)
        return UnitSystem(**kwargs)

    def test_eq_returns_notimplemented_for_non_unitsystem(self):
        s = UnitSystem.from_globals()
        # Direct __eq__ call to confirm the sentinel return; `!=` would
        # collapse it to True via Python's fallback machinery.
        self.assertIs(s.__eq__("not a system"), NotImplemented)
        self.assertIs(s.__eq__(42), NotImplemented)
        self.assertIs(s.__eq__(None), NotImplemented)

    def test_different_base_units_not_equal(self):
        from ucon import Dimension, units as _units_module
        s = UnitSystem.from_globals()
        twin = self._twin(
            s,
            base_units=BaseUnits(
                name="other", bases={Dimension.length: _units_module.meter}
            ),
        )
        self.assertNotEqual(s, twin)

    def test_different_basis_not_equal(self):
        from ucon.basis.types import Basis
        s = UnitSystem.from_globals()
        twin = self._twin(s, basis=Basis("Synthetic", ["x", "y"]))
        self.assertNotEqual(s, twin)

    def test_units_field_uses_identity_not_value(self):
        s = UnitSystem.from_globals()
        # Same content, different dict instance -> not equal.
        twin = self._twin(s, units=dict(s.units))
        self.assertNotEqual(s, twin)

    def test_dimensions_field_uses_identity_not_value(self):
        s = UnitSystem.from_globals()
        twin = self._twin(s, dimensions=dict(s.dimensions))
        self.assertNotEqual(s, twin)

    def test_contexts_field_uses_identity_not_value(self):
        s = UnitSystem.from_globals()
        twin = self._twin(s, contexts=dict(s.contexts))
        self.assertNotEqual(s, twin)

    def test_constants_field_uses_identity_not_value(self):
        s = UnitSystem.from_globals()
        twin = self._twin(s, constants=dict(s.constants))
        self.assertNotEqual(s, twin)

    def test_conversions_field_uses_identity_not_value(self):
        s = UnitSystem.from_globals()
        twin = self._twin(s, conversions=object())
        self.assertNotEqual(s, twin)

    def test_basis_graph_field_uses_identity_not_value(self):
        s = UnitSystem.from_globals()
        twin = self._twin(s, basis_graph=object())
        self.assertNotEqual(s, twin)


class TestUnitSystemAlgebraCacheSemantics(unittest.TestCase):
    """``_algebra_cache`` is a per-instance ledger, excluded from value identity."""

    def test_distinct_snapshots_have_distinct_caches(self):
        s1 = UnitSystem.from_globals()
        s2 = UnitSystem.from_globals()
        self.assertIsNot(s1._algebra_cache, s2._algebra_cache)

    def test_cache_contents_excluded_from_equality(self):
        s1 = UnitSystem.from_globals()
        s2 = UnitSystem.from_globals()
        s1._algebra_cache.mul[("a", "b")] = "anything"
        s1._algebra_cache.div[("c", "d")] = "anything"
        s1._algebra_cache.pow[("e", 2)] = "anything"
        # Cache divergence does not break equality or hash.
        self.assertEqual(s1, s2)
        self.assertEqual(hash(s1), hash(s2))

    def test_cache_excluded_from_repr(self):
        s = UnitSystem.from_globals()
        self.assertNotIn("_algebra_cache", repr(s))

    def test_cache_starts_empty(self):
        s = UnitSystem.from_globals()
        self.assertEqual(s._algebra_cache.mul, {})
        self.assertEqual(s._algebra_cache.div, {})
        self.assertEqual(s._algebra_cache.pow, {})


class TestUseExceptionSafety(unittest.TestCase):
    """``use`` must restore the previous active system on every exit path."""

    def test_use_restores_on_exception(self):
        class _Boom(RuntimeError):
            pass

        custom = UnitSystem.from_globals()
        with self.assertRaises(_Boom):
            with use(custom):
                self.assertIs(active(), custom)
                raise _Boom("failure inside use-block")
        # active() falls back to a snapshot, not the leaked custom system.
        self.assertIsNot(active(), custom)

    def test_nested_use_restores_outer_on_inner_exception(self):
        class _Boom(RuntimeError):
            pass

        outer = UnitSystem.from_globals()
        inner = UnitSystem.from_globals()
        with use(outer):
            with self.assertRaises(_Boom):
                with use(inner):
                    raise _Boom("inner failure")
            # Outer must be the active system once inner unwinds.
            self.assertIs(active(), outer)


class TestBaseUnitsHashOrderStability(unittest.TestCase):
    """``BaseUnits.__hash__`` must be invariant under bases insertion order."""

    def test_hash_independent_of_insertion_order(self):
        from ucon import Dimension, units as _units_module
        s1 = BaseUnits(name="X", bases={
            Dimension.length: _units_module.meter,
            Dimension.mass: _units_module.kilogram,
            Dimension.time: _units_module.second,
        })
        s2 = BaseUnits(name="X", bases={
            Dimension.time: _units_module.second,
            Dimension.length: _units_module.meter,
            Dimension.mass: _units_module.kilogram,
        })
        self.assertEqual(s1, s2)
        self.assertEqual(hash(s1), hash(s2))
        self.assertEqual(len({s1, s2}), 1)


class TestUnitSystemEntryPointKwargs(unittest.TestCase):
    """``system=`` kwarg wired through user-facing entry points.

    The kwarg accepts a :class:`UnitSystem` and routes lookups/conversions
    through it. When omitted, the legacy module-global behavior is
    preserved.
    """

    def test_number_to_accepts_system_kwarg(self):
        from ucon.units import meter
        system = UnitSystem.from_globals()
        result = meter(100).to("km", system=system)
        self.assertAlmostEqual(result.quantity, 0.1)

    def test_number_to_system_wins_over_graph(self):
        # When both system= and graph= are given, system.conversions
        # takes precedence. We verify this by passing a "wrong" graph
        # via graph= and observing the conversion still succeeds via
        # system.conversions.
        from ucon.graph import ConversionGraph
        from ucon.units import meter
        bogus_graph = ConversionGraph()  # empty, would fail conversion
        system = UnitSystem.from_globals()
        result = meter(100).to("km", graph=bogus_graph, system=system)
        self.assertAlmostEqual(result.quantity, 0.1)

    def test_parse_unit_accepts_system_kwarg(self):
        from ucon.resolver import parse_unit
        from ucon.core import Unit
        system = UnitSystem.from_globals()
        unit = parse_unit("meter", system=system)
        self.assertIsInstance(unit, Unit)

    def test_parse_unit_system_override_short_circuits(self):
        # If system.units has a direct entry for the name, parse_unit
        # returns that without consulting the global registry.
        from ucon.resolver import parse_unit
        from ucon.units import meter as real_meter
        # Build a minimal custom system: only "widget" is in units.
        # Because parse_unit consults system.units first, "widget"
        # resolves; bare "meter" still falls through to the global
        # registry.
        class _FakeSystem:
            units = {"widget": real_meter}
        result = parse_unit("widget", system=_FakeSystem())
        self.assertIs(result, real_meter)

    def test_parse_unit_falls_back_when_system_misses(self):
        # When system.units does not have the name, parse_unit falls
        # back to the global registry so prefix decomposition still
        # works.
        from ucon.resolver import parse_unit
        class _EmptySystem:
            units = {}
        result = parse_unit("km", system=_EmptySystem())
        # "km" is not in system.units; falls through to scale-prefix
        # decomposition.
        self.assertIsNotNone(result)

    def test_parse_quantity_threads_system(self):
        from ucon.parsing.units import parse
        system = UnitSystem.from_globals()
        n = parse("60 mph", system=system)
        self.assertEqual(n.quantity, 60.0)

    def test_parse_dimension_accepts_system_kwarg(self):
        from ucon.parsing.dimensions import parse_dimension
        from ucon.dimension import Dimension as Dim
        system = UnitSystem.from_globals()
        result = parse_dimension("length", system=system)
        self.assertEqual(result, Dim.length)

    def test_parse_dimension_system_overrides_basis(self):
        # When basis= is omitted, system.basis is used as the default.
        from ucon.parsing.dimensions import parse_dimension
        from ucon.basis.builtin import SI
        system = UnitSystem.from_globals()
        # SI basis is the default; verify "M" parses against system.basis.
        self.assertEqual(system.basis, SI)
        result = parse_dimension("M", system=system)
        self.assertIsNotNone(result)

    def test_enforce_dimensions_factory_form(self):
        # @enforce_dimensions(system=sys) returns a decorator that
        # validates and coerces against the supplied system.
        from ucon import Dimension as Dim
        from ucon.checking import enforce_dimensions
        from ucon.core import DimensionConstraint, Number
        from ucon.units import meter, second

        system = UnitSystem.from_globals()

        @enforce_dimensions(system=system)
        def speed(
            d: Annotated[Number, DimensionConstraint(Dim.length)],
            t: Annotated[Number, DimensionConstraint(Dim.time)],
        ):
            return d / t

        result = speed(meter(100), second(10))
        self.assertIsNotNone(result)

    def test_enforce_dimensions_factory_rejects_wrong_dim(self):
        from ucon import Dimension as Dim
        from ucon.checking import enforce_dimensions
        from ucon.core import DimensionConstraint, Number
        from ucon.units import meter, second

        system = UnitSystem.from_globals()

        @enforce_dimensions(system=system)
        def speed(
            d: Annotated[Number, DimensionConstraint(Dim.length)],
            t: Annotated[Number, DimensionConstraint(Dim.time)],
        ):
            return d / t

        with self.assertRaises(ValueError):
            speed(second(100), meter(10))

    def test_enforce_dimensions_bare_form_still_works(self):
        # Backward-compatibility: @enforce_dimensions (no parens) is
        # the legacy form. It must continue to function.
        from ucon import Dimension as Dim
        from ucon.checking import enforce_dimensions
        from ucon.core import DimensionConstraint, Number
        from ucon.units import meter, second

        @enforce_dimensions
        def speed(
            d: Annotated[Number, DimensionConstraint(Dim.length)],
            t: Annotated[Number, DimensionConstraint(Dim.time)],
        ):
            return d / t

        result = speed(meter(100), second(10))
        self.assertIsNotNone(result)


class TestCompoundParserSystemRouting(unittest.TestCase):
    """The composite parser consults ``system.units`` at the factor level.

    Composite expressions whose tokens are only defined in a curated
    :class:`UnitSystem` (not the module globals) must resolve when that
    system is threaded through ``parse_unit`` — e.g. ``"USD/year"``
    parsing against a finance/currency :class:`UnitSystem`.
    """

    def test_composite_resolves_via_system_units(self):
        # A composite expression "widget/widget2" resolves entirely from
        # system.units, even though neither name is in the global registry.
        from ucon.core import Unit, UnitProduct
        from ucon.resolver import parse_unit
        from ucon.units import meter, second

        class _CurrencyLikeSystem:
            # Stand-ins: pretend `meter`-shaped unit acts as "widget"
            # and `second`-shaped unit acts as "widget2". The point is
            # only the *lookup path* — composite parsing must hit
            # ``system.units`` at the factor level.
            units = {"widget": meter, "widget2": second}

        result = parse_unit("widget/widget2", system=_CurrencyLikeSystem())
        self.assertIsInstance(result, UnitProduct)
        # Verify the factors come from system.units, not the global registry.
        factor_units = {uf.unit for uf in result.factors.keys()}
        self.assertIn(meter, factor_units)
        self.assertIn(second, factor_units)

    def test_composite_mixes_system_and_global_factors(self):
        # When system.units provides one factor and the other is in the
        # global registry, both should resolve.
        from ucon.core import UnitProduct
        from ucon.resolver import parse_unit
        from ucon.units import meter

        class _PartialSystem:
            units = {"widget": meter}

        # "widget" comes from system.units, "second" from global registry.
        result = parse_unit("widget/second", system=_PartialSystem())
        self.assertIsInstance(result, UnitProduct)

    def test_composite_falls_back_when_system_empty(self):
        # If system.units is empty, composite parsing falls through to
        # the global registry exactly as it does without ``system=``.
        from ucon.core import UnitProduct
        from ucon.resolver import parse_unit

        class _EmptySystem:
            units = {}

        result = parse_unit("m/s", system=_EmptySystem())
        self.assertIsInstance(result, UnitProduct)

    def test_composite_without_system_still_works(self):
        # Backward-compatibility: parse_unit("m/s") with no system= must
        # still resolve via the global registry.
        from ucon.core import UnitProduct
        from ucon.resolver import parse_unit

        result = parse_unit("m/s")
        self.assertIsInstance(result, UnitProduct)

    def test_system_factor_wins_over_global(self):
        # When a token exists in both ``system.units`` and the global
        # registry, ``system.units`` takes precedence at the factor level.
        from ucon.resolver import parse_unit
        from ucon.units import kelvin, meter

        class _ShadowingSystem:
            # Map "m" to ``kelvin`` — a deliberately wrong global meaning
            # — to prove the system path is consulted first. Pair with a
            # distinct denominator so the two factors don't cancel.
            units = {"m": kelvin}

        result = parse_unit("m/s", system=_ShadowingSystem())
        factor_units = {uf.unit for uf in result.factors.keys()}
        # The "m" token must resolve to ``kelvin`` via system.units.
        self.assertIn(kelvin, factor_units)
        # And it must NOT resolve to ``meter`` (the global meaning).
        self.assertNotIn(meter, factor_units)

    def test_composite_with_exponent_threads_system(self):
        # Exponents inside composites: ensure system.units lookups still
        # work for tokens that carry exponents.
        from ucon.core import UnitProduct
        from ucon.resolver import parse_unit
        from ucon.units import meter, second

        class _Sys:
            units = {"widget": meter, "widget2": second}

        result = parse_unit("widget/widget2^2", system=_Sys())
        self.assertIsInstance(result, UnitProduct)


class TestCrossBasisArithmetic(unittest.TestCase):
    """``with use(system): ...`` propagates ``system.basis_graph`` down
    through ``Number`` arithmetic via ``get_basis_graph()``, and
    :func:`ucon.basis.ops.unify` performs 3-way unification through a
    common combined basis.

    Closes the ``USD*s`` case — multiplying a Number whose unit lives in
    a domain basis (currency) by a Number whose unit lives in SI must
    succeed when the active :class:`UnitSystem`'s basis_graph contains
    embeddings of both bases into a combined basis.
    """

    @staticmethod
    def _build_combined_currency_si_system():
        """Build a UnitSystem whose basis_graph embeds currency and SI
        into a combined ``SI+currency`` basis."""
        import dataclasses

        import numpy as np

        from ucon.basis.builtin import SI
        from ucon.basis.graph import BasisGraph
        from ucon.basis.transforms import BasisTransform
        from ucon.basis.types import Basis, BasisComponent
        from ucon.system import UnitSystem

        si_components = tuple(SI)
        combined = Basis(
            name="SI+currency",
            components=si_components + (BasisComponent(name="currency", symbol="C"),),
        )
        currency = Basis(
            name="currency",
            components=(BasisComponent(name="currency", symbol="C"),),
        )
        n_si = len(si_components)
        # currency(1) -> combined(n+1): currency component maps to last slot.
        currency_to_combined = np.zeros((1, n_si + 1))
        currency_to_combined[0, -1] = 1.0
        # SI(n) -> combined(n+1): identity in first n columns.
        si_to_combined = np.zeros((n_si, n_si + 1))
        for i in range(n_si):
            si_to_combined[i, i] = 1.0

        bg = BasisGraph()
        bg.add_transform(
            BasisTransform(source=currency, target=combined, matrix=currency_to_combined)
        )
        bg.add_transform(
            BasisTransform(source=SI, target=combined, matrix=si_to_combined)
        )

        sys = dataclasses.replace(UnitSystem.from_globals(), basis_graph=bg)
        return sys, currency, combined

    def test_unify_via_common_combined_basis(self):
        # 3-way unification: vectors in disjoint bases meet in a common
        # combined basis when no direct path exists.
        from ucon.basis.ops import unify
        from ucon.dimension import Dimension

        sys, currency, combined = self._build_combined_currency_si_system()
        usd_dim = Dimension.from_components(currency, currency=1)

        from ucon.dimension import Dimension as Dim
        currency_vec = usd_dim.vector
        time_vec = Dim.time.vector

        a_prime, b_prime = unify(currency_vec, time_vec, system=sys)
        self.assertEqual(a_prime.basis, combined)
        self.assertEqual(b_prime.basis, combined)

    def test_cross_basis_number_multiply_inside_use(self):
        # The headline acceptance gate: USD * second succeeds inside
        # ``with use(sys):`` when sys.basis_graph embeds both bases.
        from ucon.core import Number, Unit
        from ucon.dimension import Dimension
        from ucon.system import use
        from ucon.units import second

        sys, currency, combined = self._build_combined_currency_si_system()
        usd_dim = Dimension.from_components(currency, currency=1)
        usd = Unit(name="USD", dimension=usd_dim, aliases=("$",))

        n1 = Number(100, usd)
        n2 = Number(1, second)

        with use(sys):
            result = n1 * n2
        self.assertEqual(result.quantity, 100)
        self.assertEqual(result.unit.dimension.vector.basis, combined)

    def test_cross_basis_number_multiply_outside_use_still_raises(self):
        # Backward-compatibility: with no active system and no transforms
        # in the default graph, cross-basis multiply still raises.
        from ucon.basis.types import Basis, BasisComponent, BasisMismatch
        from ucon.core import Number, Unit
        from ucon.dimension import Dimension
        from ucon.units import second

        currency = Basis(
            name="currency",
            components=(BasisComponent(name="currency", symbol="C"),),
        )
        usd_dim = Dimension.from_components(currency, currency=1)
        usd = Unit(name="USD", dimension=usd_dim, aliases=("$",))

        n1 = Number(100, usd)
        n2 = Number(1, second)

        with self.assertRaises(BasisMismatch):
            n1 * n2

    def test_get_basis_graph_honors_active_system(self):
        # The plumbing hook: get_basis_graph() returns system.basis_graph
        # when a system is active.
        from ucon.basis.graph import get_basis_graph
        from ucon.system import use

        sys, _, _ = self._build_combined_currency_si_system()
        with use(sys):
            self.assertIs(get_basis_graph(), sys.basis_graph)

    def test_using_basis_graph_still_wins_over_active_system(self):
        # Precedence: an explicit ``using_basis_graph`` context still wins
        # over the active UnitSystem.
        from ucon.basis.graph import BasisGraph, get_basis_graph, using_basis_graph
        from ucon.system import use

        sys, _, _ = self._build_combined_currency_si_system()
        explicit = BasisGraph()
        with use(sys):
            with using_basis_graph(explicit):
                self.assertIs(get_basis_graph(), explicit)
            # Outside the explicit override, falls back to system.basis_graph
            self.assertIs(get_basis_graph(), sys.basis_graph)


if __name__ == "__main__":
    unittest.main()
