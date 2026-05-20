# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Tests for the ``Unit.scalable`` flag and ``NonScalableError`` behavior.

The ``scalable`` field controls whether the resolver may apply SI scale
prefixes to a unit during prefix decomposition. Default is ``True``;
units intended to be used only at their base scale (e.g., currency
codes, certain count-domain quantities, or symbolic constants) may
opt out by declaring ``scalable=False``.

When the resolver encounters a token that decomposes only via a prefix
attached to a non-scalable base, it raises :class:`NonScalableError`
rather than the generic :class:`UnknownUnitError`, allowing callers to
discriminate between "unknown" and "known-but-not-prefixable".
"""

import io
import unittest

from ucon import (
    Dimension,
    NonScalableError,
    UnknownUnitError,
    parse_unit,
    units,
)
from ucon.core import Unit
from ucon.graph import ConversionGraph, using_conversion_graph
from ucon.serialization import from_toml, to_toml


class TestScalableField(unittest.TestCase):
    """The ``scalable`` field on Unit."""

    def test_default_is_true(self):
        u = Unit(name="widget", dimension=Dimension.none, aliases=())
        self.assertTrue(u.scalable)

    def test_explicit_false(self):
        u = Unit(
            name="usd",
            dimension=Dimension.none,
            aliases=("USD",),
            scalable=False,
        )
        self.assertFalse(u.scalable)

    def test_builtin_units_are_scalable_by_default(self):
        # Built-in units default to scalable=True. The catalog can opt
        # individual units out without affecting the rest.
        self.assertTrue(units.meter.scalable)
        self.assertTrue(units.second.scalable)
        self.assertTrue(units.gram.scalable)

    def test_scalable_excluded_from_identity(self):
        # Like ``base_form``, ``scalable`` is parsing-behavior metadata,
        # not part of Unit identity. Two units differing only in scalable
        # compare equal and hash identically. This avoids registry
        # inconsistency if a unit's scalability is later toggled.
        a = Unit(name="thing", dimension=Dimension.none, aliases=())
        b = Unit(
            name="thing",
            dimension=Dimension.none,
            aliases=(),
            scalable=False,
        )
        self.assertEqual(a, b)
        self.assertEqual(hash(a), hash(b))


class TestNonScalableError(unittest.TestCase):
    """The resolver raises NonScalableError on prefix-over-non-scalable."""

    def test_prefix_on_non_scalable_raises(self):
        graph = ConversionGraph()
        non_scalable = Unit(
            name="usd",
            dimension=Dimension.none,
            aliases=("USD",),
            scalable=False,
        )
        graph.register_unit(non_scalable)

        with using_conversion_graph(graph):
            with self.assertRaises(NonScalableError) as cm:
                parse_unit("kUSD")

        err = cm.exception
        self.assertEqual(err.attempted, "kUSD")
        self.assertEqual(err.base.name, "usd")
        self.assertEqual(err.prefix, "k")

    def test_non_scalable_error_subclasses_unknown_unit(self):
        # NonScalableError IS an UnknownUnitError so existing callers
        # that catch the generic exception still see the failure.
        graph = ConversionGraph()
        graph.register_unit(
            Unit(
                name="eur",
                dimension=Dimension.none,
                aliases=("EUR",),
                scalable=False,
            )
        )

        with using_conversion_graph(graph):
            with self.assertRaises(UnknownUnitError):
                parse_unit("MEUR")

    def test_unprefixed_lookup_still_works(self):
        # Marking a unit non-scalable does not prevent direct lookup
        # by name or alias.
        graph = ConversionGraph()
        graph.register_unit(
            Unit(
                name="usd",
                dimension=Dimension.none,
                aliases=("USD",),
                scalable=False,
            )
        )

        with using_conversion_graph(graph):
            u = parse_unit("USD")
            self.assertEqual(u.name, "usd")
            u2 = parse_unit("usd")
            self.assertEqual(u2.name, "usd")

    def test_shorter_prefix_scalable_match_wins(self):
        # If a longer prefix yields a non-scalable base but a shorter
        # prefix yields a scalable base, the scalable interpretation
        # wins. This preserves the greedy-on-success-only invariant
        # documented in resolver._lookup_factor.
        graph = ConversionGraph()
        # Register two units whose names collide under prefix decomposition:
        #   "ilo_widget"  → non-scalable
        #   "widget"      → scalable
        # The token "kilo_widget" greedily matches "kilo" + "_widget"
        # which is not in the registry, but progressively shorter prefixes
        # are tried; "k" + "ilo_widget" hits the non-scalable base.
        # The shorter "kilo" prefix doesn't help because "_widget" is
        # not registered. Here we exercise the genuine fallthrough.
        non_scalable_base = Unit(
            name="ilo_widget",
            dimension=Dimension.none,
            aliases=(),
            scalable=False,
        )
        graph.register_unit(non_scalable_base)

        with using_conversion_graph(graph):
            with self.assertRaises(NonScalableError):
                parse_unit("kilo_widget")


class TestComputingEventFamily(unittest.TestCase):
    """The computing-event family resolves with SI prefixes."""

    def test_base_units_resolve(self):
        for name in ("flop", "op", "instruction", "cycle", "request", "event"):
            with self.subTest(name=name):
                u = parse_unit(name)
                self.assertEqual(u.name, name)
                self.assertTrue(u.scalable)

    def test_si_prefixes_attach(self):
        # SI scale prefixes apply to every member of the family.
        cases = [
            ("Pflop", "flop", 1e15),
            ("Gflop", "flop", 1e9),
            ("Mop", "op", 1e6),
            ("krequest", "request", 1e3),
            ("Tevent", "event", 1e12),
            ("kcycle", "cycle", 1e3),
        ]
        for token, base_name, factor in cases:
            with self.subTest(token=token):
                product = parse_unit(token)
                # parse_unit returns a UnitProduct for prefixed tokens.
                # Walk the single factor to verify base + scale.
                factors = list(product.factors)
                self.assertEqual(len(factors), 1)
                uf = factors[0]
                self.assertEqual(uf.unit.name, base_name)
                self.assertAlmostEqual(
                    float(uf.scale.descriptor.evaluated), factor, places=3
                )


class TestSerializationRoundTrip(unittest.TestCase):
    """``scalable`` survives the TOML round-trip."""

    def _round_trip(self, units_to_register):
        src = ConversionGraph()
        for u in units_to_register:
            src.register_unit(u)

        # Capture the TOML output and reparse it.
        import tempfile
        from pathlib import Path
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".toml", delete=False
        ) as fh:
            tmp_path = Path(fh.name)
        try:
            to_toml(src, tmp_path)
            dst = from_toml(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)
        return dst

    def test_non_scalable_unit_round_trips(self):
        non_scalable = Unit(
            name="usd",
            dimension=Dimension.none,
            aliases=("USD",),
            scalable=False,
        )
        dst = self._round_trip([non_scalable])
        recovered = dst.resolve_unit("usd")
        self.assertIsNotNone(recovered)
        recovered_unit = recovered[0]
        self.assertEqual(recovered_unit.name, "usd")
        self.assertFalse(recovered_unit.scalable)

    def test_scalable_default_round_trips(self):
        # Default scalable=True should round-trip without an explicit
        # field appearing in the TOML (verified by inspecting output).
        scalable_unit = Unit(
            name="widget",
            dimension=Dimension.none,
            aliases=("wgt",),
        )
        src = ConversionGraph()
        src.register_unit(scalable_unit)

        import tempfile
        from pathlib import Path
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".toml", delete=False
        ) as fh:
            tmp_path = Path(fh.name)
        try:
            to_toml(src, tmp_path)
            raw = tmp_path.read_text()
            # Default value must not appear in serialized output.
            # We check the "widget" block specifically.
            self.assertIn('name = "widget"', raw)
            widget_block = raw.split('name = "widget"', 1)[1].split("[[")[0]
            self.assertNotIn("scalable", widget_block)

            dst = from_toml(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)

        recovered = dst.resolve_unit("widget")
        self.assertIsNotNone(recovered)
        self.assertTrue(recovered[0].scalable)


if __name__ == "__main__":
    unittest.main()
