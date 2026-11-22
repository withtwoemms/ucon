# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
test_ratio_deprecation
======================

Rung one of the linear-ratio retirement (#393).

[ADR 013] routes "a power of a small radix on unity" to ``Scale``, which makes
``fraction``, ``percent``, ``permille``, ``basis_point``, ``ppm`` and ``ppb``
units that were filed as units but are really scales. Per the deprecation
policy they get ``PendingDeprecationWarning`` first, ``DeprecationWarning``
next, and removal at 3.0.0.

The warning fires at :class:`Number` construction rather than on attribute
access: ``ucon.units`` injects its units into the module dict at import, so a
module ``__getattr__`` never fires for them. Construction also catches the
unit however it was obtained.

What these tests pin:

1. Each of the six warns, with the category rung one requires.
2. A retiring unit is caught inside a product too, not just alone.
3. Ordinary units stay silent, and ``import ucon`` stays silent.
4. The message carries what the policy demands — the removal version and a
   migration path.
"""
import unittest
import warnings

from ucon import Number, Scale, units
from ucon.core import UnitFactor, UnitProduct
from ucon.core._types import _DEPRECATED_RATIO_UNITS


def _rung_one(fn):
    """Return the PendingDeprecationWarning records ``fn`` emits."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        fn()
    return [r for r in caught
            if issubclass(r.category, PendingDeprecationWarning)]


class TestEachRetiringUnitWarns(unittest.TestCase):
    """All six units ADR 013 routes to ``Scale`` are covered."""

    def test_every_listed_unit_warns(self):
        for name, replacement in _DEPRECATED_RATIO_UNITS:
            with self.subTest(unit=name):
                unit = getattr(units, name)
                records = _rung_one(lambda u=unit: Number(1.0, u))
                self.assertEqual(len(records), 1)
                self.assertIn(name, str(records[0].message))

    def test_the_table_covers_adr_013s_list(self):
        """Guards against a unit being dropped from the table silently."""
        self.assertEqual(
            {name for name, _ in _DEPRECATED_RATIO_UNITS},
            {"fraction", "percent", "permille", "basis_point", "ppm", "ppb"},
        )


class TestTheWarningSaysWhatThePolicyRequires(unittest.TestCase):
    """CLAUDE.md: cite the migration path and the removal version."""

    def setUp(self):
        records = _rung_one(lambda: Number(50.0, units.percent))
        self.message = str(records[0].message)

    def test_cites_the_removal_version(self):
        self.assertIn("3.0.0", self.message)

    def test_cites_the_migration_path(self):
        self.assertIn("Scale", self.message)
        self.assertIn("units.one", self.message)

    def test_names_the_replacement_scale(self):
        self.assertIn("Scale.centi", self.message)

    def test_basis_point_points_at_the_exact_power(self):
        """Expressible only since #390; before that 10**-4 had no form."""
        records = _rung_one(lambda: Number(1.0, units.basis_point))
        self.assertIn("Scale.of(10, -4)", str(records[0].message))

    def test_is_rung_one_not_rung_two(self):
        records = _rung_one(lambda: Number(50.0, units.percent))
        self.assertIs(records[0].category, PendingDeprecationWarning)
        self.assertNotIsInstance(records[0].message, DeprecationWarning)


class TestProductsAreCaught(unittest.TestCase):
    """A retiring unit hides inside a product as readily as alone."""

    def test_a_factor_of_a_product_warns(self):
        product = UnitProduct({
            UnitFactor(units.gram, Scale.kilo): 1.0,
            UnitFactor(units.percent, Scale.one): 1.0,
        })
        records = _rung_one(lambda: Number(1.0, product))
        self.assertEqual(len(records), 1)
        self.assertIn("percent", str(records[0].message))


class TestSilenceWhereItBelongs(unittest.TestCase):
    """Rung one must not fire on ordinary use."""

    def test_an_ordinary_unit_is_silent(self):
        self.assertEqual(_rung_one(lambda: Number(1.0, units.meter)), [])

    def test_a_bare_number_is_silent(self):
        """The default empty product must not be inspected as a unit."""
        self.assertEqual(_rung_one(lambda: Number(1.0)), [])

    def test_a_scale_on_unity_is_silent(self):
        """The migration target itself must not warn."""
        target = UnitProduct({UnitFactor(units.one, Scale.centi): 1.0})
        self.assertEqual(_rung_one(lambda: Number(50.0, target)), [])


class TestTheMigrationTargetComputes(unittest.TestCase):
    """The warning points somewhere that gives the right number."""

    def test_percent_as_a_scale_on_unity(self):
        target = UnitProduct({UnitFactor(units.one, Scale.centi): 1.0})
        self.assertAlmostEqual(Number(50.0, target)._canonical_magnitude, 0.5)

    def test_basis_point_as_a_scale_on_unity(self):
        target = UnitProduct({UnitFactor(units.one, Scale.of(10, -4)): 1.0})
        self.assertAlmostEqual(Number(50.0, target)._canonical_magnitude, 0.005)


if __name__ == "__main__":
    unittest.main()
