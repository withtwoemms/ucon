# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
test_scale_exact
================

``Scale`` arithmetic computes the exact power (#390).

Before this, :meth:`Scale.__mul__`, :meth:`Scale.__truediv__` and
:meth:`Scale.__pow__` computed the exact :class:`Exponent`, looked for a
*named* member at that power, and discarded the exact result when none
matched — falling through to :meth:`Scale.nearest`, which answers with the
closest named prefix. 244 of 522 single-base operations returned a wrong
scale: ``kilo * deca`` as ``kilo`` (1000, not 10000), ``centi * centi`` as
``milli``, and ``femto * femto`` as ``femto`` — off by 10**15, because
``nearest`` clamps at the ends of the table.

Naming cannot close this. A finite set of powers is never closed under
multiplication; adding the full SI prefix set *raises* the unnamed count
from 208 to 528. So the conventional prefixes are a registry over
``Exponent`` rather than the set of representable scales.

What these tests pin:

1. **Exactness** — every single-base product, quotient and power is exact.
2. **Identity** — a result a prefix names is that prefix, by ``is``.
3. **Interning** — the same exact power is the same object, so ``is``
   stays meaningful for results no prefix names.
4. **Enum surface** — unnamed members are built the way ``enum.Flag``
   builds composites, so ``isinstance`` holds and iteration over ``Scale``
   still yields only the conventional prefixes.
5. **Cross-base approximation is kept** — a mixed-base product has no
   exact power in either base, so ``nearest()`` there is correct.
6. **Rendering does not drop the scale** — an unnamed scale renders its
   exponent rather than an empty prefix.
"""
import unittest

from ucon import Scale
from ucon.core._types import Exponent


class TestExactness(unittest.TestCase):
    """Single-base arithmetic computes the exact power."""

    def test_the_three_characterising_cases(self):
        """The examples the issue names, each previously wrong."""
        cases = [
            (Scale.kilo * Scale.deca, 1e4, "10^4"),
            (Scale.centi * Scale.centi, 1e-4, "10^-4"),
            (Scale.femto * Scale.femto, 1e-30, "10^-30"),
        ]
        for result, expected, rendered in cases:
            with self.subTest(rendered=rendered):
                self.assertAlmostEqual(
                    result.value.evaluated, expected, delta=abs(expected) * 1e-12
                )
                self.assertEqual(result.name, rendered)

    def test_every_single_base_product_and_quotient_is_exact(self):
        """All 522 single-base operations, exhaustively."""
        checked = 0
        for a in Scale:
            for b in Scale:
                if a.value.base != b.value.base:
                    continue
                for symbol, got, want in (
                    ("*", (a * b).value.evaluated,
                     a.value.evaluated * b.value.evaluated),
                    ("/", (a / b).value.evaluated,
                     a.value.evaluated / b.value.evaluated),
                ):
                    checked += 1
                    self.assertAlmostEqual(
                        got, want, delta=abs(want) * 1e-12,
                        msg=f"{a.name} {symbol} {b.name}",
                    )
        self.assertEqual(checked, 522)

    def test_power_is_exact(self):
        """``__pow__`` keeps the exact power rather than approximating."""
        self.assertEqual((Scale.centi ** 2).name, "10^-4")
        self.assertEqual((Scale.kilo ** 3).name, "giga")
        self.assertEqual((Scale.femto ** 2).name, "10^-30")


class TestIdentityAndInterning(unittest.TestCase):
    """A named result is the named member; an unnamed one is interned."""

    def test_named_results_keep_identity(self):
        self.assertIs(Scale.kilo * Scale.one, Scale.kilo)
        self.assertIs(Scale.one * Scale.kilo, Scale.kilo)
        self.assertIs(Scale.milli * Scale.kilo, Scale.one)
        self.assertIs(Scale.deci * Scale.deci, Scale.centi)
        self.assertIs(Scale.mega / Scale.kilo, Scale.kilo)

    def test_unnamed_results_are_interned(self):
        self.assertIs(Scale.centi * Scale.centi, Scale.centi * Scale.centi)
        self.assertIs(Scale.of(10, -4), Scale.centi * Scale.centi)

    def test_zero_power_is_the_one_scale_in_any_base(self):
        """``base ** 0`` is 1 in every base, so it is not a second unity."""
        self.assertIs(Scale.of(10, 0), Scale.one)
        self.assertIs(Scale.of(2, 0), Scale.one)
        self.assertIs(Scale.kibi / Scale.kibi, Scale.one)

    def test_of_returns_the_named_member_when_one_exists(self):
        self.assertIs(Scale.of(10, 3), Scale.kilo)
        self.assertIs(Scale.of(2, 10), Scale.kibi)


class TestEnumSurface(unittest.TestCase):
    """Unnamed members do not disturb what ``Scale`` is."""

    def test_unnamed_member_is_a_scale(self):
        self.assertIsInstance(Scale.centi * Scale.centi, Scale)

    def test_iteration_yields_only_conventional_prefixes(self):
        """``nearest()``, ``all()`` and the parser map iterate ``Scale``."""
        members = list(Scale)
        self.assertEqual(len(members), 21)
        self.assertNotIn(Scale.centi * Scale.centi, members)
        for member in members:
            self.assertIsNotNone(member._name_)

    def test_named_lookup_still_works(self):
        self.assertIs(Scale["kilo"], Scale.kilo)

    def test_repr_distinguishes_named_from_unnamed(self):
        self.assertIn("Scale.kilo", repr(Scale.kilo))
        self.assertEqual(repr(Scale.centi * Scale.centi), "<Scale 10^-4>")

    def test_comparison_and_hashing_work_for_unnamed(self):
        unnamed = Scale.centi * Scale.centi
        self.assertTrue(unnamed < Scale.centi)
        self.assertTrue(unnamed > Scale.micro)
        self.assertEqual(hash(unnamed), hash(Scale.of(10, -4)))
        self.assertNotEqual(unnamed, Scale.milli)


class TestCrossBaseStillApproximates(unittest.TestCase):
    """Mixed-base operands have no exact power, so ``nearest()`` is right."""

    def test_mixed_base_product_falls_through_to_nearest(self):
        result = Scale.kibi * Scale.kilo
        self.assertIsNotNone(result._name_)

    def test_mixed_base_quotient_falls_through_to_nearest(self):
        self.assertIs(Scale.kibi / Scale.kilo, Scale.one)


class TestRenderingDoesNotDropTheScale(unittest.TestCase):
    """An empty prefix would be a silent magnitude error."""

    def test_unnamed_scale_renders_its_exponent(self):
        unnamed = Scale.centi * Scale.centi
        self.assertEqual(unnamed.shorthand, "10^-4")
        self.assertEqual(unnamed.name, "10^-4")

    def test_exponent_parts_round_trip(self):
        unnamed = Scale.centi * Scale.centi
        self.assertEqual(unnamed.value.parts(), (10, -4))
        self.assertEqual(Exponent(*unnamed.value.parts()).evaluated, 1e-4)


if __name__ == "__main__":
    unittest.main()
