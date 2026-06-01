# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
test_unitproduct_canonical
==========================

Canonical-form contract for :class:`UnitProduct`.

The empty product (``UnitProduct({})``) is the multiplicative identity for
the Units group. These tests pin the algebraic guarantees that downstream
code is now allowed to rely on:

1. **Identity** — multiplying by an empty product preserves factors.
2. **Self-cancellation** — ``u / u`` yields the empty product.
3. **Idempotence** — ``UnitProduct(u.factors, u.canonical_scale)`` is
   structurally equal to ``u``.
4. **Canonical-form invariants** (per-UnitFactor grain):
   a. no dimensionless (NONE-dim) factor survives in ``factors``;
   b. no zero-exponent factor survives in ``factors``;
   c. at most one entry per distinct ``UnitFactor`` — i.e. per
      ``(unit_name, dimension, aliases, scale)`` tuple. Cross-scale
      variants of the same base unit (e.g. ``mg`` and ``kg``) are
      distinct UnitFactors and both survive; their scale ratio is
      recoverable via ``fold_scale()``.
   d. ``canonical_scale == 1.0`` whenever ``factors`` is non-empty.
5. **Dimensionless absorption** — scale of dropped dim=NONE factors is
   folded into ``canonical_scale`` instead of being silently discarded.
6. **Cross-scale preservation** — ``mg/kg`` retains both factors
   (shorthand ``"mg/kg"``), ``fold_scale() == 1e-6``, and downstream
   composition works: ``(mg/kg) * kg == mg``.
7. **Constructor seed** — the ``canonical_scale`` parameter is composed
   into the final value (and defaults to ``1.0``).
"""

from __future__ import annotations

import unittest

from ucon import Scale, Unit, UnitFactor, UnitProduct
from ucon.dimension import LENGTH, MASS, NONE


class TestEmptyProductIsIdentity(unittest.TestCase):
    """The empty UnitProduct acts as the multiplicative identity."""

    def setUp(self):
        self.meter = Unit(name="meter", dimension=LENGTH, aliases=("m",))
        self.m = UnitFactor(self.meter, Scale.one)

    def test_empty_product_has_no_factors(self):
        identity = UnitProduct({})
        self.assertEqual(identity.factors, {})

    def test_empty_product_canonical_scale_is_one(self):
        identity = UnitProduct({})
        self.assertEqual(identity.canonical_scale, 1.0)

    def test_empty_product_dimension_is_none(self):
        identity = UnitProduct({})
        self.assertEqual(identity.dimension, NONE)

    def test_multiplying_by_empty_preserves_factors(self):
        u = UnitProduct({self.m: 1.0})
        identity = UnitProduct({})
        product = UnitProduct({u: 1.0, identity: 1.0})
        self.assertEqual(product.factors, u.factors)

    def test_two_empty_products_are_equal(self):
        self.assertEqual(UnitProduct({}), UnitProduct({}))


class TestSelfCancellation(unittest.TestCase):
    """A unit divided by itself collapses to the empty product."""

    def setUp(self):
        self.meter = Unit(name="meter", dimension=LENGTH, aliases=("m",))
        self.m = UnitFactor(self.meter, Scale.one)

    def test_meter_over_meter_is_empty(self):
        cancelled = UnitProduct({UnitProduct({self.m: 1.0}): 1.0,
                                 UnitProduct({self.m: -1.0}): 1.0})
        self.assertEqual(cancelled.factors, {})

    def test_self_cancellation_canonical_scale_is_one(self):
        cancelled = UnitProduct({UnitProduct({self.m: 1.0}): 1.0,
                                 UnitProduct({self.m: -1.0}): 1.0})
        self.assertEqual(cancelled.canonical_scale, 1.0)


class TestIdempotence(unittest.TestCase):
    """Rebuilding a UnitProduct from its own factors yields an equal product."""

    def setUp(self):
        self.meter = Unit(name="meter", dimension=LENGTH, aliases=("m",))
        self.gram = Unit(name="gram", dimension=MASS, aliases=("g",))
        self.dimensionless = Unit(name="ratio", dimension=NONE, aliases=())

    def test_simple_product_is_idempotent(self):
        m = UnitFactor(self.meter, Scale.one)
        original = UnitProduct({m: 2.0})
        rebuilt = UnitProduct(original.factors, original.canonical_scale)
        self.assertEqual(rebuilt.factors, original.factors)
        self.assertEqual(rebuilt.canonical_scale, original.canonical_scale)

    def test_absorbed_product_is_idempotent(self):
        # A dim=NONE factor with a non-unit scale absorbs into
        # canonical_scale; the rebuilt product must preserve both
        # (the empty factors) and the absorbed canonical_scale value.
        r = UnitFactor(self.dimensionless, Scale.kilo)
        original = UnitProduct({r: 1.0})
        rebuilt = UnitProduct(original.factors, original.canonical_scale)
        self.assertEqual(rebuilt.factors, original.factors)
        self.assertAlmostEqual(rebuilt.canonical_scale, original.canonical_scale)

class TestCanonicalFormInvariants(unittest.TestCase):
    """The canonical-form invariants must hold for every UnitProduct."""

    def setUp(self):
        self.meter = Unit(name="meter", dimension=LENGTH, aliases=("m",))
        self.dimensionless = Unit(name="ratio", dimension=NONE, aliases=())
        self.m = UnitFactor(self.meter, Scale.one)
        self.r = UnitFactor(self.dimensionless, Scale.one)

    def test_no_dimensionless_factor_survives(self):
        # Mix one LENGTH factor with a NONE-dim factor: only LENGTH remains.
        u = UnitProduct({self.m: 1.0, self.r: 1.0})
        for fu in u.factors:
            self.assertNotEqual(fu.dimension, NONE)

    def test_no_zero_exponent_factor_survives(self):
        # A factor with exponent ~0 must be filtered out.
        u = UnitProduct({self.m: 1.0, UnitFactor(self.meter, Scale.one): 0.0})
        for exp in u.factors.values():
            self.assertGreater(abs(exp), 1e-12)

    def test_canonical_scale_is_one_when_factors_nonempty(self):
        # A plain product carries no cancelled-scale residue.
        u = UnitProduct({self.m: 1.0})
        self.assertEqual(u.canonical_scale, 1.0)


class TestDimensionlessAbsorption(unittest.TestCase):
    """Dropped NONE-dim factors must compose their scale into canonical_scale."""

    def setUp(self):
        self.dimensionless = Unit(name="ratio", dimension=NONE, aliases=())

    def test_scaled_dimensionless_absorbs_into_canonical_scale(self):
        # A dimensionless factor with a non-unit scale is dropped from
        # ``factors`` but its scale^exp is folded into canonical_scale.
        r = UnitFactor(self.dimensionless, Scale.kilo)
        u = UnitProduct({r: 1.0})
        self.assertEqual(u.factors, {})
        self.assertAlmostEqual(u.canonical_scale, 1000.0)

    def test_absorption_respects_exponent(self):
        r = UnitFactor(self.dimensionless, Scale.kilo)
        u = UnitProduct({r: 2.0})
        self.assertEqual(u.factors, {})
        self.assertAlmostEqual(u.canonical_scale, 1_000_000.0)

    def test_unit_scale_dimensionless_absorbs_to_one(self):
        # A dim=NONE factor with Scale.one carries scale=1, so absorption
        # is a no-op and the empty product remains canonical_scale == 1.0.
        r = UnitFactor(self.dimensionless, Scale.one)
        u = UnitProduct({r: 1.0})
        self.assertEqual(u.factors, {})
        self.assertEqual(u.canonical_scale, 1.0)


class TestCancellation(unittest.TestCase):
    """
    Same-scale pairs collapse to the empty product. Cross-scale pairs
    survive as distinct UnitFactors (per-UnitFactor grain): the algebra
    preserves user-provided scales so that downstream composition works
    (``mg/kg * kg == mg``). The numeric ratio is recoverable via
    ``fold_scale()``.
    """

    def setUp(self):
        self.gram = Unit(name="gram", dimension=MASS, aliases=("g",))

    def test_kg_over_kg_cancels(self):
        kg = UnitFactor(self.gram, Scale.kilo)
        cancelled = UnitProduct({UnitProduct({kg: 1.0}): 1.0,
                                 UnitProduct({kg: -1.0}): 1.0})
        self.assertEqual(cancelled.factors, {})
        self.assertEqual(cancelled.canonical_scale, 1.0)

    def test_mg_per_kg_preserves_both_factors(self):
        # Cross-scale variants are distinct UnitFactors; both survive.
        mg = UnitFactor(self.gram, Scale.milli)
        kg = UnitFactor(self.gram, Scale.kilo)
        ratio = UnitProduct({UnitProduct({mg: 1.0}): 1.0,
                             UnitProduct({kg: -1.0}): 1.0})
        self.assertIn(mg, ratio.factors)
        self.assertIn(kg, ratio.factors)
        self.assertAlmostEqual(ratio.factors[mg], 1.0)
        self.assertAlmostEqual(ratio.factors[kg], -1.0)

    def test_mg_per_kg_fold_scale_recovers_ratio(self):
        # The numeric ratio 10^-3 / 10^3 = 10^-6 is recoverable.
        mg = UnitFactor(self.gram, Scale.milli)
        kg = UnitFactor(self.gram, Scale.kilo)
        ratio = UnitProduct({UnitProduct({mg: 1.0}): 1.0,
                             UnitProduct({kg: -1.0}): 1.0})
        self.assertAlmostEqual(ratio.fold_scale(), 1e-6)

    def test_mg_per_kg_shorthand(self):
        mg = UnitFactor(self.gram, Scale.milli)
        kg = UnitFactor(self.gram, Scale.kilo)
        ratio = UnitProduct({UnitProduct({mg: 1.0}): 1.0,
                             UnitProduct({kg: -1.0}): 1.0})
        self.assertEqual(ratio.shorthand, "mg/kg")

    def test_mg_per_kg_composes_with_kg(self):
        # The dosage composition path: (mg/kg) * kg == mg.
        mg = UnitFactor(self.gram, Scale.milli)
        kg = UnitFactor(self.gram, Scale.kilo)
        ratio = UnitProduct({UnitProduct({mg: 1.0}): 1.0,
                             UnitProduct({kg: -1.0}): 1.0})
        composed = ratio * UnitProduct({kg: 1.0})
        self.assertEqual(composed.factors, {mg: 1.0})

    def test_cross_scale_product_is_idempotent(self):
        mg = UnitFactor(self.gram, Scale.milli)
        kg = UnitFactor(self.gram, Scale.kilo)
        original = UnitProduct({UnitProduct({mg: 1.0}): 1.0,
                                UnitProduct({kg: -1.0}): 1.0})
        rebuilt = UnitProduct(original.factors, original.canonical_scale)
        self.assertEqual(rebuilt.factors, original.factors)
        self.assertAlmostEqual(rebuilt.canonical_scale, original.canonical_scale)


class TestCanonicalScaleSeed(unittest.TestCase):
    """The constructor's ``canonical_scale`` parameter is a seed value."""

    def setUp(self):
        self.meter = Unit(name="meter", dimension=LENGTH, aliases=("m",))
        self.m = UnitFactor(self.meter, Scale.one)

    def test_seed_default_is_one(self):
        u = UnitProduct({self.m: 1.0})
        self.assertEqual(u.canonical_scale, 1.0)

    def test_seed_propagates_on_empty_product(self):
        # With no factors and no cancellation, the seed survives intact.
        u = UnitProduct({}, canonical_scale=3.5)
        self.assertEqual(u.factors, {})
        self.assertAlmostEqual(u.canonical_scale, 3.5)

    def test_seed_composes_with_dimensionless_absorption(self):
        # Seed multiplies with the absorbed-dimensionless scale.
        dimensionless = Unit(name="ratio", dimension=NONE, aliases=())
        r = UnitFactor(dimensionless, Scale.kilo)
        u = UnitProduct({r: 1.0}, canonical_scale=2.0)
        self.assertEqual(u.factors, {})
        self.assertAlmostEqual(u.canonical_scale, 2000.0)

    def test_seed_propagates_on_cross_scale_product(self):
        # Cross-scale variants survive as distinct factors; the seed
        # composes into canonical_scale alongside them.
        gram = Unit(name="gram", dimension=MASS, aliases=("g",))
        mg = UnitFactor(gram, Scale.milli)
        kg = UnitFactor(gram, Scale.kilo)
        u = UnitProduct({UnitProduct({mg: 1.0}): 1.0,
                         UnitProduct({kg: -1.0}): 1.0},
                        canonical_scale=2.0)
        self.assertIn(mg, u.factors)
        self.assertIn(kg, u.factors)
        self.assertAlmostEqual(u.canonical_scale, 2.0)


if __name__ == "__main__":
    unittest.main()
