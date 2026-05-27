# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
test_active_context
===================

Tests for the v2.0 §3.4 :class:`ActiveContext` substrate.

``ActiveContext`` is a frozen dataclass that bundles a ``UnitSystem`` with
the active :class:`FormulaRegistry`, :class:`KindLattice`, and a ``strict``
flag.  It is the payload carried by the ``ucon._active`` ContextVar.  The
typed accessors ``active``, ``active_system``, ``active_formulas``,
``active_kinds``, and ``active_strict`` are the only sanctioned read paths;
the extended :func:`use` ``contextmanager`` writes the payload and inherits
unset fields from the enclosing context.
"""

from __future__ import annotations

import dataclasses
import unittest

import ucon
from ucon import (
    ActiveContext,
    FormulaRegistry,
    KindLattice,
    UnitSystem,
    active,
    active_formulas,
    active_kinds,
    active_strict,
    active_system,
    use,
)
from ucon._active import _active as _active_var


class TestActiveContextType(unittest.TestCase):
    """``ActiveContext`` shape and immutability."""

    def test_returns_active_context_instance(self):
        ctx = active()
        self.assertIsInstance(ctx, ActiveContext)

    def test_system_field_is_unitsystem(self):
        ctx = active()
        self.assertIsInstance(ctx.system, UnitSystem)

    def test_formulas_field_is_formula_registry(self):
        ctx = active()
        self.assertIsInstance(ctx.formulas, FormulaRegistry)

    def test_kinds_field_is_kind_lattice(self):
        ctx = active()
        self.assertIsInstance(ctx.kinds, KindLattice)

    def test_strict_defaults_to_true(self):
        ctx = active()
        self.assertTrue(ctx.strict)

    def test_active_context_is_frozen(self):
        ctx = active()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            ctx.strict = False  # type: ignore[misc]


class TestTypedAccessors(unittest.TestCase):
    """The typed accessors delegate to ``active()`` field access."""

    def test_active_system_returns_system_field(self):
        self.assertIs(active_system(), active().system)

    def test_active_formulas_returns_formulas_field(self):
        self.assertIs(active_formulas(), active().formulas)

    def test_active_kinds_returns_kinds_field(self):
        self.assertIs(active_kinds(), active().kinds)

    def test_active_strict_returns_strict_field(self):
        self.assertEqual(active_strict(), active().strict)

    def test_ucon_top_level_exposes_accessors(self):
        # The top-level package re-exports all accessors.
        self.assertIs(ucon.active_system(), ucon.active().system)
        self.assertIs(ucon.active_formulas(), ucon.active().formulas)
        self.assertIs(ucon.active_kinds(), ucon.active().kinds)
        self.assertEqual(ucon.active_strict(), ucon.active().strict)


class TestRaisesWhenNoContext(unittest.TestCase):
    """``active()`` raises ``RuntimeError`` when ``_active`` holds ``None``."""

    def test_raises_runtime_error(self):
        token = _active_var.set(None)
        try:
            with self.assertRaises(RuntimeError) as cm:
                active()
            self.assertIn("No active UnitSystem", str(cm.exception))
        finally:
            _active_var.reset(token)


class TestUseSetsContext(unittest.TestCase):
    """``use(system, ...)`` installs an ``ActiveContext`` inside the block."""

    def test_use_with_only_system_inherits_other_fields(self):
        outer = active()
        with use(outer.system):
            inner = active()
            self.assertIs(inner.system, outer.system)
            # ``use`` did not specify formulas/kinds/strict, so it should
            # inherit them from the enclosing context.
            self.assertIs(inner.formulas, outer.formulas)
            self.assertIs(inner.kinds, outer.kinds)
            self.assertEqual(inner.strict, outer.strict)

    def test_use_can_override_formulas(self):
        custom_formulas = FormulaRegistry()
        with use(active().system, formulas=custom_formulas):
            self.assertIs(active().formulas, custom_formulas)
            self.assertIs(active_formulas(), custom_formulas)

    def test_use_can_override_kinds(self):
        custom_kinds = KindLattice()
        with use(active().system, kinds=custom_kinds):
            self.assertIs(active().kinds, custom_kinds)
            self.assertIs(active_kinds(), custom_kinds)

    def test_use_can_override_strict(self):
        with use(active().system, strict=False):
            self.assertFalse(active().strict)
            self.assertFalse(active_strict())

    def test_use_can_override_all_fields(self):
        sys_outer = active().system
        f = FormulaRegistry()
        k = KindLattice()
        with use(sys_outer, formulas=f, kinds=k, strict=False):
            ctx = active()
            self.assertIs(ctx.system, sys_outer)
            self.assertIs(ctx.formulas, f)
            self.assertIs(ctx.kinds, k)
            self.assertFalse(ctx.strict)

    def test_use_restores_outer_context_on_exit(self):
        before = active()
        with use(before.system, strict=False):
            self.assertFalse(active().strict)
        self.assertEqual(active(), before)
        self.assertTrue(active_strict())


class TestNestedUseInheritance(unittest.TestCase):
    """Nested ``use`` blocks inherit unset fields from the enclosing block."""

    def test_inner_inherits_outer_formulas_when_not_specified(self):
        custom_formulas = FormulaRegistry()
        with use(active().system, formulas=custom_formulas):
            with use(active().system, strict=False):
                # Inner did not specify formulas; should still see outer's.
                self.assertIs(active().formulas, custom_formulas)
                self.assertFalse(active().strict)

    def test_inner_overrides_outer_kinds(self):
        outer_kinds = KindLattice()
        inner_kinds = KindLattice()
        with use(active().system, kinds=outer_kinds):
            self.assertIs(active_kinds(), outer_kinds)
            with use(active().system, kinds=inner_kinds):
                self.assertIs(active_kinds(), inner_kinds)
            # After inner exits, outer's kinds is restored.
            self.assertIs(active_kinds(), outer_kinds)

    def test_nested_unwind_restores_each_layer(self):
        before = active()
        outer_strict = False
        inner_strict = True
        with use(before.system, strict=outer_strict):
            self.assertEqual(active_strict(), outer_strict)
            with use(before.system, strict=inner_strict):
                self.assertEqual(active_strict(), inner_strict)
            self.assertEqual(active_strict(), outer_strict)
        # Full restoration.
        self.assertEqual(active(), before)


class TestUseExceptionSafety(unittest.TestCase):
    """``use`` restores the previous context even when an exception is raised."""

    def test_exception_inside_use_restores_outer(self):
        class _Boom(Exception):
            pass

        before = active()
        with self.assertRaises(_Boom):
            with use(before.system, strict=False):
                raise _Boom("failure inside use-block")
        # After the exception unwinds, the previous context is restored.
        self.assertEqual(active(), before)
        self.assertTrue(active_strict())


if __name__ == "__main__":
    unittest.main()
