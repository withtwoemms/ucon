# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
test_bridge
===========

Tests for :class:`ucon.system.Bridge` (v2.0 §3.3).

``Bridge`` is the sanctioned cross-system value-movement primitive when
unit names diverge or a basis transform is required. ``rename`` is
synonym-only; non-synonym pairs are rejected by ``__post_init__`` with
:class:`InvalidRename`. Apply order is rename → ``basis_transform`` →
identity-bind; the two layers commute under the synonym constraint.
"""

import unittest
from dataclasses import replace

import ucon
from ucon import (
    Bridge,
    InvalidRename,
    Number,
    Unit,
    UnknownUnitError,
)
from ucon.system import UnitSystem


def _active() -> UnitSystem:
    return ucon.active_system()


def _system_with_metre_synonym() -> UnitSystem:
    """Return a system that has the same units as ``active()`` plus an
    additional ``metre`` unit that is synonym-equivalent to ``meter``.
    """
    s = _active()
    meter = s.units["meter"]
    metre = Unit(name="metre", dimension=meter.dimension, aliases=())
    # base_form is compare=False on Unit; we must install it explicitly
    # to satisfy the synonym predicate in Bridge._validate_synonym.
    metre._set_base_form(meter.base_form)
    return s.with_unit(metre)


# ---------------------------------------------------------------------------
# Construction & identity
# ---------------------------------------------------------------------------


class TestBridgeIdentity(unittest.TestCase):

    def test_identity_bridge_constructs(self):
        s = _active()
        b = Bridge(src=s, dst=s)
        self.assertIs(b.src, s)
        self.assertIs(b.dst, s)
        self.assertEqual(dict(b.rename), {})
        self.assertIsNone(b.basis_transform)

    def test_identity_bridge_apply_is_noop_on_quantity(self):
        s = _active()
        b = Bridge(src=s, dst=s)
        n = Number(5.0, s.units["meter"])
        out = b.apply(n)
        self.assertEqual(out.quantity, 5.0)
        self.assertIs(out.unit, s.units["meter"])

    def test_identity_bridge_applies_to_unit_product(self):
        from ucon import UnitProduct
        s = _active()
        b = Bridge(src=s, dst=s)
        product = UnitProduct({s.units["meter"]: 1.0, s.units["second"]: -1.0})
        n = Number(3.0, product)
        out = b.apply(n)
        self.assertIsInstance(out.unit, UnitProduct)
        self.assertEqual(out.quantity, 3.0)


# ---------------------------------------------------------------------------
# Rename (synonym)
# ---------------------------------------------------------------------------


class TestBridgeRenameSynonym(unittest.TestCase):

    def test_synonym_rename_constructs(self):
        src = _active()
        dst = _system_with_metre_synonym()
        b = Bridge(src=src, dst=dst, rename={"meter": "metre"})
        self.assertEqual(dict(b.rename), {"meter": "metre"})

    def test_synonym_rename_apply_renames_unit(self):
        src = _active()
        dst = _system_with_metre_synonym()
        b = Bridge(src=src, dst=dst, rename={"meter": "metre"})
        n = Number(5.0, src.units["meter"])
        out = b.apply(n)
        self.assertEqual(out.unit.name, "metre")
        self.assertIs(out.unit, dst.units["metre"])
        self.assertEqual(out.quantity, 5.0)


# ---------------------------------------------------------------------------
# InvalidRename — construction validation
# ---------------------------------------------------------------------------


class TestBridgeInvalidRename(unittest.TestCase):

    def test_missing_src_name_raises(self):
        s = _active()
        with self.assertRaises(InvalidRename) as cm:
            Bridge(src=s, dst=s, rename={"nonexistent_src": "meter"})
        self.assertEqual(cm.exception.src_name, "nonexistent_src")
        self.assertEqual(cm.exception.dst_name, "meter")

    def test_missing_dst_name_raises(self):
        s = _active()
        with self.assertRaises(InvalidRename) as cm:
            Bridge(src=s, dst=s, rename={"meter": "nonexistent_dst"})
        self.assertEqual(cm.exception.src_name, "meter")
        self.assertEqual(cm.exception.dst_name, "nonexistent_dst")

    def test_dimension_mismatch_raises(self):
        s = _active()
        # meter ≠ second: different dimensions.
        with self.assertRaises(InvalidRename) as cm:
            Bridge(src=s, dst=s, rename={"meter": "second"})
        self.assertEqual(cm.exception.src_name, "meter")
        self.assertEqual(cm.exception.dst_name, "second")
        self.assertIn("dimension", cm.exception.reason)

    def test_base_form_mismatch_raises(self):
        s = _active()
        # meter and foot share the dimension (length) but have different
        # base_forms (foot = 0.3048 m). This is a definitional difference,
        # not a synonym, and must be rejected.
        with self.assertRaises(InvalidRename) as cm:
            Bridge(src=s, dst=s, rename={"meter": "foot"})
        self.assertIn("base form", cm.exception.reason.lower())


# ---------------------------------------------------------------------------
# Inverse round-trip
# ---------------------------------------------------------------------------


class TestBridgeInverse(unittest.TestCase):

    def test_identity_bridge_inverse_is_identity_bridge(self):
        s = _active()
        b = Bridge(src=s, dst=s)
        inv = b.inverse()
        self.assertIs(inv.src, s)
        self.assertIs(inv.dst, s)
        self.assertEqual(dict(inv.rename), {})
        self.assertIsNone(inv.basis_transform)

    def test_synonym_rename_inverse_reverses_mapping(self):
        src = _active()
        dst = _system_with_metre_synonym()
        b = Bridge(src=src, dst=dst, rename={"meter": "metre"})
        inv = b.inverse()
        self.assertIs(inv.src, dst)
        self.assertIs(inv.dst, src)
        self.assertEqual(dict(inv.rename), {"metre": "meter"})

    def test_apply_then_inverse_apply_round_trips(self):
        src = _active()
        dst = _system_with_metre_synonym()
        b = Bridge(src=src, dst=dst, rename={"meter": "metre"})
        n = Number(5.0, src.units["meter"])
        forward = b.apply(n)
        roundtrip = b.inverse().apply(forward)
        self.assertEqual(roundtrip.quantity, n.quantity)
        self.assertIs(roundtrip.unit, src.units["meter"])


# ---------------------------------------------------------------------------
# Composition (__matmul__)
# ---------------------------------------------------------------------------


class TestBridgeComposition(unittest.TestCase):

    def test_identity_composition(self):
        s = _active()
        a = Bridge(src=s, dst=s)
        b = Bridge(src=s, dst=s)
        composed = a @ b
        self.assertIs(composed.src, s)
        self.assertIs(composed.dst, s)
        self.assertEqual(dict(composed.rename), {})

    def test_composition_requires_other_dst_is_self_src(self):
        s = _active()
        other = _system_with_metre_synonym()
        a = Bridge(src=s, dst=s)
        b = Bridge(src=other, dst=other)
        # other.dst is `other`, but a.src is `s` — not identical.
        with self.assertRaises(ValueError):
            a @ b

    def test_composition_chains_renames(self):
        src = _active()
        mid = _system_with_metre_synonym()
        b1 = Bridge(src=src, dst=mid, rename={"meter": "metre"})
        b2 = Bridge(src=mid, dst=mid)
        composed = b2 @ b1
        self.assertIs(composed.src, src)
        self.assertIs(composed.dst, mid)
        self.assertEqual(dict(composed.rename), {"meter": "metre"})

    def test_composition_re_runs_validation(self):
        """Pairs valid individually can be invalid jointly. With the
        current scope (no basis_transform composition trickery), the
        easiest regression vector is name-existence: a composed rename
        whose target does not exist in ``self.dst.units`` must raise.
        """
        # Build two bridges where, in isolation, the rename pair is
        # valid; then compose so that the chained target name no longer
        # exists in the final ``dst``. Since restriction loses ``metre``
        # if we re-restrict, we can engineer that path.
        src = _active()
        mid = _system_with_metre_synonym()
        b1 = Bridge(src=src, dst=mid, rename={"meter": "metre"})
        # restrict mid back down to a system that does not have ``metre``
        dst = mid.restrict(units=["meter"])
        # b2: identity on dst — no renames to validate.
        b2 = Bridge(src=mid, dst=dst)
        # Composition forwards "meter" -> "metre" through b1, but "metre"
        # is not in dst.units; __post_init__ must reject.
        with self.assertRaises(InvalidRename):
            b2 @ b1


# ---------------------------------------------------------------------------
# Apply order
# ---------------------------------------------------------------------------


class TestBridgeApplyOrder(unittest.TestCase):
    """Apply order is rename → basis_transform → identity-bind. Without
    a basis_transform, this collapses to rename + identity-bind, which
    we already cover above. The order assertion here is structural: a
    Number whose unit name is renamed lands at the destination's
    ``Unit`` object, never at the source's.
    """

    def test_apply_returns_dst_owned_unit_object(self):
        src = _active()
        dst = _system_with_metre_synonym()
        b = Bridge(src=src, dst=dst, rename={"meter": "metre"})
        n = Number(2.0, src.units["meter"])
        out = b.apply(n)
        # The returned Number's unit references ``dst``, not ``src``.
        self.assertIs(out.unit, dst.units["metre"])
        self.assertIsNot(out.unit, src.units["meter"])


if __name__ == "__main__":
    unittest.main()
