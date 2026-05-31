# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
test_exceptions
===============

Unit tests for the exception classes defined in :mod:`ucon.core.exceptions`.

Coverage targets:

- :class:`DimensionNotCovered` — minimal raise/catch and Exception inheritance.
- :class:`UnknownUnitError` — ``name`` attribute and exact message format.
- :class:`NonScalableError` — ``attempted``/``base``/``prefix``/``name``
  attributes, message format distinct from the parent, and inheritance
  from :class:`UnknownUnitError`.
- :class:`UnitDefinitionMismatch` — named-unit path **and** the
  ``getattr(unit, "name", None) or repr(unit)`` fallback at the message
  site (line 94 in ``exceptions.py``).
- :class:`KindDimensionMismatch` — named-unit path **and** the analogous
  fallback at line 120.

These tests directly instantiate each exception (no graph traversal or
parser invocation required) so the assertions exercise the message
formatting and attribute installation logic in isolation.
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from ucon import (
    Dimension,
    DimensionNotCovered,
    KindDimensionMismatch,
    NonScalableError,
    Unit,
    UnitDefinitionMismatch,
    UnknownUnitError,
)
from ucon.dimension import LENGTH, MASS
from ucon.graph import ConversionGraph
from ucon.kinds import Kind


class TestDimensionNotCovered(unittest.TestCase):
    """:class:`DimensionNotCovered` is a bare Exception subclass."""

    def test_is_exception_subclass(self):
        self.assertTrue(issubclass(DimensionNotCovered, Exception))

    def test_raise_and_catch(self):
        with self.assertRaises(DimensionNotCovered):
            raise DimensionNotCovered("length not covered")

    def test_message_preserved(self):
        try:
            raise DimensionNotCovered("length not covered")
        except DimensionNotCovered as exc:
            self.assertEqual(str(exc), "length not covered")


class TestUnknownUnitError(unittest.TestCase):
    """:class:`UnknownUnitError` carries the offending name."""

    def test_is_exception_subclass(self):
        self.assertTrue(issubclass(UnknownUnitError, Exception))

    def test_name_attribute_set(self):
        err = UnknownUnitError("foo")
        self.assertEqual(err.name, "foo")

    def test_message_format(self):
        err = UnknownUnitError("foo")
        self.assertEqual(str(err), "Unknown unit: 'foo'")

    def test_message_quotes_name(self):
        # The !r conversion in the format string means even integer-like
        # tokens are shown with repr quoting.
        err = UnknownUnitError("123abc")
        self.assertEqual(str(err), "Unknown unit: '123abc'")


class TestNonScalableError(unittest.TestCase):
    """:class:`NonScalableError` carries prefix-decomposition context."""

    def setUp(self):
        self.base = Unit(name="usd", dimension=Dimension.none, aliases=("USD",),
                         scalable=False)

    def test_inherits_from_unknown_unit_error(self):
        # Inheritance is the explicit contract documented on the class.
        err = NonScalableError("kUSD", self.base, "k")
        self.assertIsInstance(err, UnknownUnitError)

    def test_attributes_installed(self):
        err = NonScalableError("kUSD", self.base, "k")
        self.assertEqual(err.attempted, "kUSD")
        self.assertIs(err.base, self.base)
        self.assertEqual(err.prefix, "k")

    def test_name_attribute_mirrors_attempted(self):
        # NonScalableError bypasses UnknownUnitError.__init__ but still
        # installs ``name = attempted`` so callers that read ``.name``
        # on a caught UnknownUnitError see the full token.
        err = NonScalableError("MUSD", self.base, "M")
        self.assertEqual(err.name, "MUSD")

    def test_message_format_distinct_from_parent(self):
        err = NonScalableError("kUSD", self.base, "k")
        msg = str(err)
        # The richer message must not be the generic "Unknown unit: ..."
        # produced by the parent constructor.
        self.assertNotEqual(msg, "Unknown unit: 'kUSD'")
        # Spot-check the salient fragments of the documented format.
        self.assertIn("'kUSD'", msg)
        self.assertIn("'usd'", msg)
        self.assertIn("'k'", msg)
        self.assertIn("non-scalable", msg)


class TestUnitDefinitionMismatch(unittest.TestCase):
    """:class:`UnitDefinitionMismatch` reports identity-failed source units."""

    def setUp(self):
        self.graph = ConversionGraph()

    def test_attributes_installed(self):
        unit = Unit(name="widget", dimension=Dimension.none, aliases=())
        err = UnitDefinitionMismatch(unit, graph=self.graph)
        self.assertIs(err.unit, unit)
        self.assertIs(err.graph, self.graph)

    def test_named_unit_appears_in_message(self):
        unit = Unit(name="widget", dimension=Dimension.none, aliases=())
        err = UnitDefinitionMismatch(unit, graph=self.graph)
        msg = str(err)
        self.assertIn("'widget'", msg)
        self.assertIn("adopt", msg)
        self.assertIn("Bridge", msg)

    def test_repr_fallback_when_name_missing(self):
        # The message-site fallback is
        #   ``name = getattr(unit, "name", None) or repr(unit)``
        # An object without a ``name`` attribute exercises the
        # ``getattr(..., None)`` branch; an object whose ``name`` is the
        # empty string (or another falsy value) exercises the ``or``
        # branch. Both must surface as the object's repr.
        nameless = SimpleNamespace()
        err = UnitDefinitionMismatch(nameless, graph=self.graph)
        self.assertIn(repr(nameless), str(err))

    def test_falsy_name_falls_back_to_repr(self):
        # A Unit constructed with the default empty name is structurally
        # legal and exercises the ``or repr(unit)`` half of the fallback.
        empty_named = Unit(name="", dimension=Dimension.none, aliases=())
        err = UnitDefinitionMismatch(empty_named, graph=self.graph)
        self.assertIn(repr(empty_named), str(err))


class TestKindDimensionMismatch(unittest.TestCase):
    """:class:`KindDimensionMismatch` reports kind/unit dimension drift."""

    def setUp(self):
        # A Kind anchored in MASS, intentionally distinct from the LENGTH
        # dimension used on the test units below.
        self.kind = Kind(name="test_mass_kind", dimension=MASS)

    def test_attributes_installed(self):
        unit = Unit(name="meter_clone", dimension=LENGTH, aliases=())
        err = KindDimensionMismatch(kind=self.kind, unit=unit)
        self.assertIs(err.kind, self.kind)
        self.assertIs(err.unit, unit)

    def test_named_unit_appears_in_message(self):
        unit = Unit(name="meter_clone", dimension=LENGTH, aliases=())
        err = KindDimensionMismatch(kind=self.kind, unit=unit)
        msg = str(err)
        self.assertIn("'meter_clone'", msg)
        self.assertIn("'test_mass_kind'", msg)
        # Both dimensions are surfaced so the reader can diagnose drift.
        self.assertIn(repr(MASS), msg)
        self.assertIn(repr(LENGTH), msg)

    def test_repr_fallback_when_name_missing(self):
        # The exception's message accesses ``unit.dimension`` directly, so
        # the stand-in for the missing-name case must still carry a
        # ``dimension`` attribute.
        nameless = SimpleNamespace(dimension=LENGTH)
        err = KindDimensionMismatch(kind=self.kind, unit=nameless)
        self.assertIn(repr(nameless), str(err))

    def test_falsy_name_falls_back_to_repr(self):
        empty_named = Unit(name="", dimension=LENGTH, aliases=())
        err = KindDimensionMismatch(kind=self.kind, unit=empty_named)
        self.assertIn(repr(empty_named), str(err))


if __name__ == "__main__":
    unittest.main()
