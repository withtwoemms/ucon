# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
test_adopt
==========

Tests for :meth:`ucon.system.UnitSystem.adopt` (v2.0 §3.3).

``adopt`` is the trivial cross-system value-movement primitive: rebind
the :class:`Unit` references in a :class:`Number` to point at the
objects owned by ``self``, raising :class:`UnknownUnitError` if any
component name is not defined here. It performs no conversion math.
"""

import unittest

import ucon
from ucon import Number, Unit, UnitFactor, UnitProduct, UnknownUnitError
from ucon.system import UnitSystem


def _active() -> UnitSystem:
    return ucon.active()


class TestAdoptSuccess(unittest.TestCase):

    def test_adopts_plain_unit_number(self):
        s = _active()
        meter = s.units["meter"]
        n = Number(5.0, meter)
        out = s.adopt(n)
        self.assertIs(out.unit, meter)
        self.assertEqual(out.quantity, 5.0)

    def test_preserves_uncertainty(self):
        s = _active()
        meter = s.units["meter"]
        n = Number(5.0, meter, uncertainty=0.1)
        out = s.adopt(n)
        self.assertEqual(out.uncertainty, 0.1)

    def test_adopts_unit_product(self):
        s = _active()
        meter = s.units["meter"]
        second = s.units["second"]
        product = UnitProduct({meter: 1.0, second: -1.0})
        n = Number(2.5, product)
        out = s.adopt(n)
        self.assertIsInstance(out.unit, UnitProduct)
        self.assertEqual(out.quantity, 2.5)
        # Every UnitFactor in the rebound product refers to a Unit owned
        # by ``s``.
        for factor in out.unit.factors:
            self.assertIs(s.units[factor.unit.name], factor.unit)

    def test_rebinds_to_self_units_objects(self):
        """When two systems share the same name but have *equal* Unit
        objects, ``adopt`` rebinds the Number's ``unit`` so that
        ``out.unit is system.units[name]``.
        """
        s = _active()
        sub = s.restrict(units=["meter"])
        # Use the system's own meter object, then adopt into the
        # restricted subsystem. The Unit objects should be the same
        # (restrict reuses them), but identity should hold by name.
        meter = s.units["meter"]
        n = Number(1.0, meter)
        out = sub.adopt(n)
        self.assertIs(out.unit, sub.units["meter"])


class TestAdoptFailure(unittest.TestCase):

    def test_unknown_unit_in_plain_unit_raises(self):
        s = _active()
        sub = s.restrict(units=["meter"])
        foot = s.units["foot"]
        n = Number(3.0, foot)
        with self.assertRaises(UnknownUnitError) as cm:
            sub.adopt(n)
        self.assertEqual(cm.exception.name, "foot")

    def test_unknown_unit_in_unit_product_raises(self):
        s = _active()
        sub = s.restrict(units=["meter"])
        meter = s.units["meter"]
        second = s.units["second"]
        product = UnitProduct({meter: 1.0, second: -1.0})
        n = Number(2.5, product)
        with self.assertRaises(UnknownUnitError) as cm:
            sub.adopt(n)
        self.assertEqual(cm.exception.name, "second")


class TestAdoptNoConversion(unittest.TestCase):
    """``adopt`` does not perform conversion. The numeric value is
    untouched even when the source ``Unit`` happens to have a different
    definition; ``adopt`` is name-based rebinding only.
    """

    def test_quantity_unchanged_for_plain_unit(self):
        s = _active()
        n = Number(42.0, s.units["meter"])
        out = s.adopt(n)
        self.assertEqual(out.quantity, n.quantity)

    def test_quantity_unchanged_for_unit_product(self):
        s = _active()
        product = UnitProduct({s.units["meter"]: 1.0, s.units["second"]: -1.0})
        n = Number(7.25, product)
        out = s.adopt(n)
        self.assertEqual(out.quantity, n.quantity)


if __name__ == "__main__":
    unittest.main()
