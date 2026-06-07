# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
test_strict_resolution
======================

Tests for the ``strict=True`` source-unit resolution guard on
:meth:`ucon.Number.to` and :meth:`ucon.NumberArray.to`.

Under ``strict=True`` (the v2.0 default), ``Number.to(target)`` resolves
the source unit by **object identity** against the active conversion
graph. A :class:`Number` whose ``unit`` is not in the resolution graph by
identity raises :class:`UnitDefinitionMismatch` instead of being silently
re-resolved by name. Remediation: ``system.adopt(n)`` for systems sharing
unit names, or ``Bridge(src, dst, ...).apply(n)`` when names or bases
diverge. ``use(system, strict=False)`` preserves v1.x name-based ergonomics
for a scope.

This file mirrors at the ``Number`` layer what
``tests/ucon/basis/test_vector_strict_basis.py`` does at the ``Vector``
layer: pin the strict-mode invariant directly at the algebra boundary so
it remains independently observable.
"""

from __future__ import annotations

import dataclasses
import unittest

import numpy as np

import ucon
from ucon import (
    Number,
    Unit,
    UnitDefinitionMismatch,
    UnitProduct,
    active_strict,
    use,
)
from ucon.core._types import NumberArray


def _foreign_unit_for(name: str) -> Unit:
    """Return a structurally-equal but identity-distinct clone of a unit.

    ``dataclasses.replace`` on a frozen dataclass returns a fresh instance
    with the same field values, so ``new == existing`` is ``True`` while
    ``new is existing`` is ``False`` — the exact precondition for the
    strict-mode guard to fire.
    """
    existing = ucon.active_system().units[name]
    return dataclasses.replace(existing)


class TestStrictDefaultBehavior(unittest.TestCase):
    """The v2.0 default is ``strict=True``; identity-good Numbers convert."""

    def test_strict_true_is_v20_default(self):
        self.assertTrue(active_strict())

    def test_shared_unit_objects_pass_strict_check(self):
        s = ucon.active_system()
        meter = s.units["meter"]
        foot = s.units["foot"]
        n = Number(1.0, meter)
        # No exception: meter is the same object as the node in the graph.
        out = n.to(foot)
        self.assertAlmostEqual(out.quantity, 3.28084, places=4)

    def test_to_target_string_unaffected_by_strict(self):
        """String targets are resolved via the active system, so the
        target itself is always identity-good. The guard only checks the
        *source* unit.
        """
        s = ucon.active_system()
        n = Number(1.0, s.units["meter"])
        out = n.to("foot")
        self.assertAlmostEqual(out.quantity, 3.28084, places=4)


class TestForeignUnitRaises(unittest.TestCase):
    """Under ``strict=True``, foreign source units surface as exceptions."""

    def test_foreign_unit_raises_unit_definition_mismatch(self):
        s = ucon.active_system()
        foreign_meter = _foreign_unit_for("meter")
        # Sanity: structurally equal but identity-distinct.
        self.assertEqual(foreign_meter, s.units["meter"])
        self.assertIsNot(foreign_meter, s.units["meter"])

        n = Number(1.0, foreign_meter)
        with self.assertRaises(UnitDefinitionMismatch) as cm:
            n.to(s.units["foot"])
        self.assertIs(cm.exception.unit, foreign_meter)
        self.assertIs(cm.exception.graph, s.conversion_graph)

    def test_remediation_message_names_adopt_and_bridge(self):
        foreign_meter = _foreign_unit_for("meter")
        n = Number(1.0, foreign_meter)
        with self.assertRaises(UnitDefinitionMismatch) as cm:
            n.to("foot")
        msg = str(cm.exception)
        self.assertIn("adopt", msg)
        self.assertIn("Bridge", msg)

    def test_unit_product_with_foreign_factor_raises(self):
        """``contains_unit_by_identity`` descends into UnitProduct factors.

        A composite source whose factors include an identity-foreign Unit
        must raise.
        """
        s = ucon.active_system()
        foreign_meter = _foreign_unit_for("meter")
        second = s.units["second"]
        # meter / second product whose meter is identity-foreign.
        product = UnitProduct({foreign_meter: 1.0, second: -1.0})
        n = Number(1.0, product)
        with self.assertRaises(UnitDefinitionMismatch):
            n.to("foot/second")


class TestStrictFalseOptOut(unittest.TestCase):
    """``use(system, strict=False)`` preserves v1.x name-based ergonomics."""

    def test_use_strict_false_falls_back_to_name_based(self):
        s = ucon.active_system()
        foreign_meter = _foreign_unit_for("meter")
        n = Number(1.0, foreign_meter)
        with use(s, strict=False):
            # No exception under strict=False; resolution falls through
            # to the graph's name-based path.
            out = n.to(s.units["foot"])
        self.assertAlmostEqual(out.quantity, 3.28084, places=4)

    def test_nested_use_inherits_strict_false(self):
        """A nested ``use(system)`` without ``strict=`` inherits the outer
        scope's ``strict=False``.
        """
        s = ucon.active_system()
        foreign_meter = _foreign_unit_for("meter")
        n = Number(1.0, foreign_meter)
        with use(s, strict=False):
            with use(s):
                # Should still be in strict=False territory.
                self.assertFalse(active_strict())
                out = n.to("foot")
        self.assertAlmostEqual(out.quantity, 3.28084, places=4)


class TestNumberArrayMirror(unittest.TestCase):
    """``NumberArray.to`` mirrors the strict guard on ``Number.to``."""

    def test_number_array_to_under_strict_raises_for_foreign_unit(self):
        s = ucon.active_system()
        foreign_meter = _foreign_unit_for("meter")
        arr = NumberArray(quantities=np.array([1.0, 2.0, 3.0]), unit=foreign_meter)
        with self.assertRaises(UnitDefinitionMismatch) as cm:
            arr.to(s.units["foot"])
        # NumberArray.to wraps the source into a UnitProduct before
        # delegating to the graph, so the exception carries that wrapper.
        # The identity-foreign meter lives inside it as a UnitFactor.unit.
        offender = cm.exception.unit
        if isinstance(offender, UnitProduct):
            factor_units = [f.unit for f in offender.factors]
            self.assertIn(foreign_meter, factor_units)
            # Verify by identity, not just equality, that the foreign Unit
            # was preserved through the wrap.
            self.assertTrue(any(f.unit is foreign_meter for f in offender.factors))
        else:
            self.assertIs(offender, foreign_meter)


class TestExceptionShape(unittest.TestCase):
    """:class:`UnitDefinitionMismatch` attribute and inheritance contract."""

    def test_unit_definition_mismatch_is_exception_subclass(self):
        self.assertTrue(issubclass(UnitDefinitionMismatch, Exception))

    def test_carries_unit_and_graph_attrs(self):
        s = ucon.active_system()
        foreign_meter = _foreign_unit_for("meter")
        n = Number(1.0, foreign_meter)
        try:
            n.to("foot")
        except UnitDefinitionMismatch as exc:
            self.assertIs(exc.unit, foreign_meter)
            self.assertIs(exc.graph, s.conversion_graph)
        else:
            self.fail("UnitDefinitionMismatch was not raised")


if __name__ == "__main__":
    unittest.main()
