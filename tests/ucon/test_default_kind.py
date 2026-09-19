# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Tests for the ``Unit.default_kind`` declaration.

``default_kind`` is the first unit→kind association ucon carries: a unit
may name the :class:`~ucon.kinds.Kind` it measures when nothing says
otherwise, and a :class:`~ucon.core.Number` built on that unit with no
explicit ``kind=`` picks the declaration up at construction.

Three properties are pinned here:

1. The field defaults to ``None`` — no unit in the built-in catalog
   declares one, so nothing about existing behavior changes.
2. An explicit ``kind=`` always beats the declaration.
3. The TOML key round-trips through the package loader, the graph
   serializer, and the binary cache.

Resolution is deliberately best-effort at construction: a declaration
naming a kind the active lattice does not know leaves the Number
unkinded rather than raising. Declaration errors are caught at load
time, where the lattice that ought to contain the name is known.

The *arrival* rule — what ``Number.to()`` should do when the target unit
declares a conflicting ``default_kind`` — is an open design question
(ucon#305) and is not exercised here.
"""

import tempfile
import unittest
from pathlib import Path

from ucon import (
    Dimension,
    Number,
    PackageLoadError,
    get_default_graph,
    load_package,
    units,
)
from ucon._cache import _from_primitives, _to_primitives
from ucon.core import Unit, UnitProduct
from ucon.dimension import LENGTH, NONE
from ucon.graph import ConversionGraph
from ucon.kinds import Kind, KindLattice
from ucon.packages import UnitDef
from ucon.serialization import GraphLoadError, from_toml, to_toml
from ucon.system import active_system, use


CURRENCY = Kind("currency", dimension=NONE)
USD = Kind("usd", dimension=NONE, parent=CURRENCY)
EUR = Kind("eur", dimension=NONE, parent=CURRENCY)
SPAN = Kind("span", dimension=LENGTH)
CURRENCY_LATTICE = KindLattice([CURRENCY, USD, EUR, SPAN])

usd_unit = Unit(
    name="usd",
    dimension=Dimension.none,
    aliases=("USD",),
    scalable=False,
    default_kind="usd",
)
# A dimensioned declarant: unlike a dimensionless one, this survives the
# UnitProduct wrapping that ``unit(quantity)`` and ``.to()`` apply.
cubit = Unit(
    name="cubit",
    dimension=Dimension.length,
    aliases=("cbt",),
    default_kind="span",
)
plain_unit = Unit(name="widget", dimension=Dimension.none, aliases=("wgt",))


# Enough of an SI preamble for ``from_toml`` to resolve "none".
PREAMBLE = '''
[bases.SI]
components = [
  {name = "time", symbol = "T"},
  {name = "length", symbol = "L"},
  {name = "mass", symbol = "M"},
  {name = "current", symbol = "I"},
  {name = "temperature", symbol = "Θ"},
  {name = "luminous_intensity", symbol = "J"},
  {name = "amount_of_substance", symbol = "N"},
  {name = "information", symbol = "B"},
]

[dimensions.none]
basis = "SI"
vector = [0, 0, 0, 0, 0, 0, 0, 0]
'''


def _write_toml(content: str) -> Path:
    """Write *content* to a temporary ``.ucon.toml`` and return its path."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".ucon.toml", delete=False
    ) as fh:
        fh.write(content)
        fh.flush()
        return Path(fh.name)


class TestDefaultKindField(unittest.TestCase):
    """The ``default_kind`` field on Unit."""

    def test_default_is_none(self):
        u = Unit(name="widget", dimension=Dimension.none, aliases=())
        self.assertIsNone(u.default_kind)

    def test_explicit_value_is_stored(self):
        self.assertEqual(usd_unit.default_kind, "usd")

    def test_builtin_units_declare_no_default_kind(self):
        # The catalog is untouched: default_kind is opt-in, per package.
        self.assertIsNone(units.meter.default_kind)
        self.assertIsNone(units.gray.default_kind)
        self.assertIsNone(units.sievert.default_kind)

    def test_default_kind_excluded_from_identity(self):
        # Like ``scalable``, ``default_kind`` is metadata rather than an
        # identity attribute: two units differing only in the declaration
        # compare equal and hash identically, so toggling it cannot make
        # the registry inconsistent.
        bare = Unit(name="usd", dimension=Dimension.none, aliases=("USD",))
        declared = Unit(
            name="usd",
            dimension=Dimension.none,
            aliases=("USD",),
            default_kind="usd",
        )
        self.assertEqual(bare, declared)
        self.assertEqual(hash(bare), hash(declared))

    def test_unit_remains_frozen(self):
        with self.assertRaises(Exception):
            usd_unit.default_kind = "eur"


class TestUnitProductDefaultKind(unittest.TestCase):
    """A single-unit product inherits its one factor's declaration."""

    def test_single_factor_product_inherits(self):
        self.assertEqual(UnitProduct.from_unit(cubit).default_kind, "span")

    def test_undeclared_single_factor_product_is_none(self):
        self.assertIsNone(UnitProduct.from_unit(units.meter).default_kind)

    def test_compound_product_declares_nothing(self):
        # A kind for cubit/second follows from a formula, not from either
        # factor's declaration.
        self.assertIsNone((cubit / units.second).default_kind)

    def test_single_factor_survives_cancellation(self):
        # The general (non-fast) canonicalization path: cubit·s/s reduces
        # to a lone cubit, which still declares what a cubit declares.
        reduced = (cubit * units.second) / units.second
        self.assertEqual(list(reduced.factors.values()), [1])
        self.assertEqual(reduced.default_kind, "span")

    def test_non_unit_exponent_declares_nothing(self):
        # cubit² is an area and cubit⁻¹ a wavenumber; neither is a span.
        self.assertIsNone(UnitProduct({cubit: 2}).default_kind)
        self.assertIsNone(UnitProduct({cubit: -1}).default_kind)

    def test_empty_product_declares_nothing(self):
        self.assertIsNone(UnitProduct({}).default_kind)


class TestNumberAutoAttachment(unittest.TestCase):
    """``Number`` picks up its unit's declaration when no kind is given."""

    def test_declared_kind_attaches_when_kind_omitted(self):
        with use(active_system(), kinds=CURRENCY_LATTICE):
            n = Number(100, usd_unit)
        self.assertIs(n.kind, USD)

    def test_unit_call_syntax_attaches(self):
        with use(active_system(), kinds=CURRENCY_LATTICE):
            n = cubit(3)
        self.assertIs(n.kind, SPAN)

    def test_explicit_kind_beats_declaration(self):
        with use(active_system(), kinds=CURRENCY_LATTICE):
            n = Number(100, usd_unit, kind=EUR)
        self.assertIs(n.kind, EUR)

    def test_explicit_parent_kind_beats_declaration(self):
        # Not merely "a different leaf wins" — any explicit kind wins,
        # including a coarser ancestor of the declared one.
        with use(active_system(), kinds=CURRENCY_LATTICE):
            n = Number(100, usd_unit, kind=CURRENCY)
        self.assertIs(n.kind, CURRENCY)

    def test_undeclared_unit_is_unaffected(self):
        with use(active_system(), kinds=CURRENCY_LATTICE):
            self.assertIsNone(Number(100, plain_unit).kind)
            self.assertIsNone(Number(5, units.meter).kind)
            self.assertIsNone(units.meter(5).kind)
            self.assertIsNone(Number(5).kind)

    def test_declaration_unknown_to_active_lattice_is_ignored(self):
        # Best-effort by design: a unit declared by one package may be
        # used in a context whose lattice never heard of the kind.
        other = KindLattice([Kind("length_kind", dimension=LENGTH)])
        with use(active_system(), kinds=other):
            self.assertIsNone(Number(100, usd_unit).kind)

    def test_declaration_may_name_an_alias(self):
        aliased = KindLattice(
            [Kind("currency:usd", dimension=NONE, aliases=("usd",))]
        )
        with use(active_system(), kinds=aliased):
            n = Number(100, usd_unit)
        self.assertIsNotNone(n.kind)
        self.assertEqual(n.kind.name, "currency:usd")

    def test_repr_surfaces_the_attached_kind(self):
        with use(active_system(), kinds=CURRENCY_LATTICE):
            self.assertIn("[usd]", repr(Number(100, usd_unit)))


class TestUnitDefDeclaration(unittest.TestCase):
    """``UnitDef`` carries the TOML key onto the materialized Unit."""

    def test_default_is_none(self):
        unit_def = UnitDef(name="slug", dimension="mass")
        self.assertIsNone(unit_def.default_kind)
        self.assertIsNone(unit_def.materialize().default_kind)

    def test_materialize_resolves_against_local_lattice(self):
        unit_def = UnitDef(name="usd", dimension="none", default_kind="usd")
        unit = unit_def.materialize(kind_lattice=CURRENCY_LATTICE)
        self.assertEqual(unit.default_kind, "usd")

    def test_materialize_canonicalizes_an_alias(self):
        lattice = KindLattice(
            [Kind("currency:usd", dimension=NONE, aliases=("usd",))]
        )
        unit_def = UnitDef(name="usd", dimension="none", default_kind="usd")
        unit = unit_def.materialize(kind_lattice=lattice)
        self.assertEqual(unit.default_kind, "currency:usd")

    def test_unresolvable_declaration_raises(self):
        unit_def = UnitDef(
            name="usd", dimension="none", default_kind="no_such_kind",
        )
        with self.assertRaises(PackageLoadError) as ctx:
            unit_def.materialize(kind_lattice=CURRENCY_LATTICE)
        self.assertIn("no_such_kind", str(ctx.exception))


class TestPackageLoading(unittest.TestCase):
    """``default_kind`` travels through ``load_package`` / ``with_package``."""

    FX = '''
[package]
name = "fx"

[[kinds]]
name = "currency"
dimension = "none"

[[kinds]]
name = "usd"
dimension = "none"
parent = "currency"

[[units]]
name = "us_dollar"
dimension = "none"
aliases = ["USD"]
scalable = false
default_kind = "usd"
'''

    def test_load_package_parses_the_key(self):
        path = _write_toml(self.FX)
        try:
            pkg = load_package(path)
            self.assertEqual(pkg.units[0].default_kind, "usd")
        finally:
            path.unlink()

    def test_novel_kind_declared_by_a_unit_in_the_same_package(self):
        # The package defines both the kind and the unit that names it,
        # so resolution must consult the package's own lattice — the
        # ambient one has never heard of "usd".
        path = _write_toml(self.FX)
        try:
            pkg = load_package(path)
            graph = get_default_graph().with_package(pkg)
            resolved = graph.resolve_unit("us_dollar")
            self.assertIsNotNone(resolved)
            self.assertEqual(resolved[0].default_kind, "usd")
        finally:
            path.unlink()

    def test_namespace_qualifies_the_declaration(self):
        path = _write_toml(self.FX.replace(
            '[package]\nname = "fx"',
            '[package]\nname = "fx"\nnamespace = "fx"',
        ))
        try:
            pkg = load_package(path)
            self.assertEqual(pkg.units[0].default_kind, "fx:usd")
        finally:
            path.unlink()

    def test_unresolvable_declaration_raises_on_install(self):
        path = _write_toml('''
[package]
name = "fx"

[[units]]
name = "us_dollar"
dimension = "none"
default_kind = "no_such_kind"
''')
        try:
            pkg = load_package(path)
            with self.assertRaises(PackageLoadError):
                get_default_graph().with_package(pkg)
        finally:
            path.unlink()


class TestSerializationRoundTrip(unittest.TestCase):
    """``default_kind`` survives the TOML round-trip."""

    def _round_trip(self, units_to_register, lattice=None):
        src = ConversionGraph()
        for u in units_to_register:
            src.register_unit(u)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".toml", delete=False
        ) as fh:
            tmp_path = Path(fh.name)
        try:
            to_toml(src, tmp_path, kinds=lattice)
            raw = tmp_path.read_text()
            dst = from_toml(tmp_path)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
        return dst, raw

    def test_declared_unit_round_trips(self):
        dst, raw = self._round_trip([usd_unit], lattice=CURRENCY_LATTICE)
        self.assertIn('default_kind = "usd"', raw)
        recovered = dst.resolve_unit("usd")
        self.assertIsNotNone(recovered)
        self.assertEqual(recovered[0].default_kind, "usd")

    def test_undeclared_unit_emits_no_key(self):
        dst, raw = self._round_trip([plain_unit])
        widget_block = raw.split('name = "widget"', 1)[1].split("[[")[0]
        self.assertNotIn("default_kind", widget_block)
        recovered = dst.resolve_unit("widget")
        self.assertIsNotNone(recovered)
        self.assertIsNone(recovered[0].default_kind)

    def test_unknown_declaration_raises_graph_load_error(self):
        path = _write_toml(PREAMBLE + '''
[[units]]
name = "us_dollar"
dimension = "none"
default_kind = "no_such_kind"
''')
        try:
            with self.assertRaises(GraphLoadError) as ctx:
                from_toml(path)
            self.assertIn("no_such_kind", str(ctx.exception))
        finally:
            path.unlink()

    def test_declaration_resolves_against_the_files_own_kinds(self):
        path = _write_toml(PREAMBLE + '''
[[kinds]]
name = "usd"
dimension = "none"

[[units]]
name = "us_dollar"
dimension = "none"
default_kind = "usd"
''')
        try:
            graph = from_toml(path)
            recovered = graph.resolve_unit("us_dollar")
            self.assertIsNotNone(recovered)
            self.assertEqual(recovered[0].default_kind, "usd")
        finally:
            path.unlink()


class TestCacheRoundTrip(unittest.TestCase):
    """``default_kind`` survives the marshal-based graph cache."""

    def _graph_with(self, unit):
        graph = get_default_graph().copy()
        graph.register_unit(unit)
        return graph

    def test_declared_unit_round_trips(self):
        src = self._graph_with(cubit)
        dst = _from_primitives(_to_primitives(src))
        recovered = dst.resolve_unit("cubit")
        self.assertIsNotNone(recovered)
        self.assertEqual(recovered[0].default_kind, "span")

    def test_undeclared_unit_omits_the_key(self):
        src = self._graph_with(plain_unit)
        prims = _to_primitives(src)
        self.assertNotIn("dk", prims["u:widget"])
        dst = _from_primitives(prims)
        recovered = dst.resolve_unit("widget")
        self.assertIsNotNone(recovered)
        self.assertIsNone(recovered[0].default_kind)

    def test_builtin_catalog_marshals_without_the_key(self):
        # No catalog unit declares one, so the cache payload is
        # byte-identical to what it was before the field existed.
        prims = _to_primitives(get_default_graph())
        declared = [
            key for key, val in prims.items()
            if key.startswith("u:") and "dk" in val
        ]
        self.assertEqual(declared, [])


if __name__ == "__main__":
    unittest.main()
