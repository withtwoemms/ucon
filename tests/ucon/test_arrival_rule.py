# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Tests for the arrival rule — the second half of ``Unit.default_kind``.

``#306`` shipped the declaration and its attachment at construction, and
left this open (``test_default_kind`` says so in its own docstring). ADR 011
states the rule and the defect motivating it: ``.to()`` preserves kind,
which is right for physics — J → kWh is still ``energy`` — and wrong for
exchange, where converted euros must not stay kinded ``usd``.

The rule as implemented serves both declarers ADR 011 names:

    the target's declared kind wins, unless it is already an ancestor
    of the current kind, in which case the finer kind survives — and when
    the kinds are siblings, only an edge licensed by a contingent context
    may re-kind; a static edge refuses.

**Currency** converts between *siblings* — ``usd`` and ``eur`` under a
``currency`` root — so arrival genuinely re-kinds. A rate edge transformed
the stuff.

**Information** converts *within* a kind — ``bit`` and ``byte`` both declare
``information`` — so arrival must not demote a Number carrying something
more specific. 8 bits of payload are 1 byte of payload, not 1 byte of
generic information.

Nothing in the shipped catalog declares a ``default_kind``, so every case
here is constructed locally and the rule is a no-op on existing behavior.
"""
import unittest

from ucon import KindArrivalRefused, Number, Unit, units as U
from ucon.contexts import ContextEdge, ConversionContext, using_context
from ucon.dimension import all_dimensions
from ucon.kinds import JoinPolicy, Kind, KindLattice
from ucon.maps import LinearMap
from ucon.system import active_system, use

COUNT = next(d for d in all_dimensions() if str(d) == "Dimension(count)")

# ── currency: siblings under a refuse root ──────────────────────────────
CURRENCY = Kind("currency", dimension=COUNT, join_policy=JoinPolicy.REFUSE)
USD_KIND = Kind("usd", dimension=COUNT, parent=CURRENCY)
EUR_KIND = Kind("eur", dimension=COUNT, parent=CURRENCY)
USD = Unit(name="arrUSD", dimension=COUNT, default_kind="usd")
EUR = Unit(name="arrEUR", dimension=COUNT, default_kind="eur")

# ── information: parent and child, both units declaring the parent ──────
INFORMATION = Kind("information", dimension=COUNT)
PAYLOAD = Kind("payload_size", dimension=COUNT, parent=INFORMATION)
BIT = Unit(name="arrBit", dimension=COUNT, default_kind="information")
BYTE = Unit(name="arrByte", dimension=COUNT, default_kind="information")

# A target declaring nothing, to pin the untouched path.
PLAIN = Unit(name="arrPlain", dimension=COUNT)

LATTICE = KindLattice([CURRENCY, USD_KIND, EUR_KIND, INFORMATION, PAYLOAD])

EDGES = ConversionContext(
    name="arrival-fixture",
    # A rate table is contingent (ADR 011, #320). That license is what lets
    # ``usd -> eur`` re-kind; see TestStaticEdgesBetweenSiblingsRefuse.
    contingent=True,
    edges=(
        ContextEdge(src=USD, dst=EUR, map=LinearMap(0.9214)),
        ContextEdge(src=BIT, dst=BYTE, map=LinearMap(0.125)),
        ContextEdge(src=BIT, dst=PLAIN, map=LinearMap(1.0)),
    ),
)


class ArrivalRuleTestCase(unittest.TestCase):
    """Shared scope: the lattice and the fixture edges."""

    def setUp(self):
        self._use = use(active_system(), kinds=LATTICE)
        self._ctx = using_context(EDGES)
        self._use.__enter__()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__(None, None, None)
        self._use.__exit__(None, None, None)


class TestCurrencyRekindsOnArrival(ArrivalRuleTestCase):
    """The defect ADR 011 was written to close."""

    def test_converted_euros_are_kinded_eur(self):
        result = Number(100.0, USD).to(EUR)
        self.assertEqual(result.kind, EUR_KIND)

    def test_the_value_is_untouched(self):
        """Re-kinding changes the label, never the number."""
        result = Number(100.0, USD).to(EUR)
        self.assertAlmostEqual(result.quantity, 92.14)

    def test_an_explicit_source_kind_does_not_survive(self):
        """`usd` and `eur` are siblings; the rate edge transformed the
        stuff, so the source kind must not carry through."""
        result = Number(100.0, USD, kind=USD_KIND).to(EUR)
        self.assertEqual(result.kind, EUR_KIND)
        self.assertNotEqual(result.kind, USD_KIND)

    def test_an_unkinded_number_adopts_the_declaration(self):
        plain = Number(100.0, USD)
        object.__setattr__(plain, "kind", None)
        self.assertEqual(plain.to(EUR).kind, EUR_KIND)


class TestInformationKeepsTheFinerKind(ArrivalRuleTestCase):
    """A scale change within one kind must not demote."""

    def test_a_descendant_kind_survives(self):
        """8 bits of payload are 1 byte of payload."""
        result = Number(8.0, BIT, kind=PAYLOAD).to(BYTE)
        self.assertEqual(result.kind, PAYLOAD)

    def test_the_declared_kind_is_kept_when_it_matches(self):
        result = Number(8.0, BIT, kind=INFORMATION).to(BYTE)
        self.assertEqual(result.kind, INFORMATION)

    def test_an_unkinded_number_adopts_the_declaration(self):
        result = Number(8.0, BIT).to(BYTE)
        self.assertEqual(result.kind, INFORMATION)

    def test_the_two_families_disagree_deliberately(self):
        """The same rule produces opposite outcomes, which is the point:
        siblings re-kind, ancestors do not."""
        currency = Number(100.0, USD, kind=USD_KIND).to(EUR)
        information = Number(8.0, BIT, kind=PAYLOAD).to(BYTE)
        self.assertEqual(currency.kind, EUR_KIND)      # changed
        self.assertEqual(information.kind, PAYLOAD)    # unchanged


class TestUndeclaredTargetsAreUntouched(ArrivalRuleTestCase):
    def test_kind_is_preserved_when_the_target_declares_nothing(self):
        """The physics case: J → kWh is still `energy`."""
        result = Number(8.0, BIT, kind=PAYLOAD).to(PLAIN)
        self.assertEqual(result.kind, PAYLOAD)

    def test_an_unkinded_number_stays_unkinded(self):
        result = Number(8.0, BIT).to(PLAIN)
        # BIT declares `information`, so construction attaches it; the
        # undeclared target leaves it alone rather than clearing it.
        self.assertEqual(result.kind, INFORMATION)


class TestAspectsAreOrthogonal(ArrivalRuleTestCase):
    def test_aspects_ride_through_a_re_kinding(self):
        """The arrival rule governs the kind stratum only."""
        from ucon.aspects import Aspect

        basis = Aspect(name="arr_basis", join_policy=JoinPolicy.REFUSE)
        nominal = Aspect(name="arr_nominal", parent=basis,
                         join_policy=JoinPolicy.REFUSE)
        source = Number(100.0, USD, kind=USD_KIND)._carry(frozenset({nominal}))

        result = source.to(EUR)
        self.assertEqual(result.kind, EUR_KIND)
        self.assertIn(nominal, result.aspects)


# ── dose: siblings under a refuse root, reached by a STATIC edge ────────
DOSE_D = U.gray.dimension
DOSE = Kind("dose", dimension=DOSE_D, join_policy=JoinPolicy.REFUSE)
ABSORBED = Kind("absorbed_dose", dimension=DOSE_D, parent=DOSE)
EQUIVALENT = Kind("dose_equivalent", dimension=DOSE_D, parent=DOSE)
DOSE_LATTICE = KindLattice([DOSE, ABSORBED, EQUIVALENT])
GY = Unit(name="arrGy", dimension=DOSE_D, default_kind="absorbed_dose")
SV = Unit(name="arrSv", dimension=DOSE_D, default_kind="dose_equivalent")
ANY_DOSE = Unit(name="arrDose", dimension=DOSE_D, default_kind="dose")

STATIC = ConversionContext(
    name="arrival-static",
    edges=(
        ContextEdge(src=GY, dst=SV, map=LinearMap(1.0)),
        ContextEdge(src=ANY_DOSE, dst=SV, map=LinearMap(1.0)),
    ),
)
DATED = ConversionContext(
    name="arrival-dated",
    contingent=True,
    edges=(ContextEdge(src=GY, dst=SV, map=LinearMap(1.0)),),
)


class TestStaticEdgesBetweenSiblingsRefuse(unittest.TestCase):
    """The refusing clause. Gy and Sv share a dimension; nothing on a
    factor-1 edge performed the weighting that makes `dose_equivalent`
    true, so arriving there must not relabel."""

    def test_a_static_edge_between_sibling_kinds_refuses(self):
        with use(active_system(), kinds=DOSE_LATTICE), using_context(STATIC):
            with self.assertRaises(KindArrivalRefused):
                Number(1.0, GY, kind=ABSORBED).to(SV)

    def test_the_refusal_names_both_kinds_and_the_unit(self):
        with use(active_system(), kinds=DOSE_LATTICE), using_context(STATIC):
            with self.assertRaises(KindArrivalRefused) as cm:
                Number(1.0, GY).to(SV)  # default_kind attaches absorbed_dose
        self.assertEqual(cm.exception.current, ABSORBED)
        self.assertEqual(cm.exception.arrival, EQUIVALENT)
        self.assertIs(cm.exception.unit, SV)

    def test_a_contingent_context_licenses_the_re_kind(self):
        """The currency case, in dose clothing: a dated table transformed
        the stuff, so the declaration wins."""
        with use(active_system(), kinds=DOSE_LATTICE), using_context(DATED):
            result = Number(1.0, GY, kind=ABSORBED).to(SV)
        self.assertEqual(result.kind, EQUIVALENT)

    def test_an_unkinded_source_still_adopts_the_declaration(self):
        """Nothing to refuse against: no kind arrived, so the unit's wins."""
        plain = Number(1.0, GY)
        object.__setattr__(plain, "kind", None)
        with use(active_system(), kinds=DOSE_LATTICE), using_context(STATIC):
            self.assertEqual(plain.to(SV).kind, EQUIVALENT)

    def test_a_narrowing_declaration_is_admitted(self):
        """Ancestor to descendant is not a sibling re-kind; the caller asked
        for the finer unit."""
        with use(active_system(), kinds=DOSE_LATTICE), using_context(STATIC):
            result = Number(1.0, ANY_DOSE, kind=DOSE).to(SV)
        self.assertEqual(result.kind, EQUIVALENT)

    def test_the_license_is_surfaced_by_the_graph(self):
        from ucon.conversion import get_default_graph
        with use(active_system(), kinds=DOSE_LATTICE), using_context(DATED):
            _, license_ = get_default_graph().convert_with_license(src=GY, dst=SV)
        self.assertEqual(license_, "arrival-dated")
        with use(active_system(), kinds=DOSE_LATTICE), using_context(STATIC):
            _, license_ = get_default_graph().convert_with_license(src=GY, dst=SV)
        self.assertIsNone(license_)


class TestBestEffortResolution(unittest.TestCase):
    """Matching attachment at construction: an unknown name does not raise."""

    def test_an_unresolvable_declaration_leaves_the_kind_alone(self):
        unknown = Unit(name="arrUnknown", dimension=COUNT,
                       default_kind="no_such_kind_xyz")
        edges = ConversionContext(
            name="arrival-unknown",
            edges=(ContextEdge(src=USD, dst=unknown, map=LinearMap(1.0)),),
        )
        with use(active_system(), kinds=LATTICE), using_context(edges):
            result = Number(1.0, USD, kind=USD_KIND).to(unknown)
        self.assertEqual(result.kind, USD_KIND)

    def test_no_active_lattice_lets_the_declaration_win(self):
        """Without a lattice the ancestry test cannot run, so the rule
        falls back to ADR 011's plain form — the currency case."""
        edges = ConversionContext(
            name="arrival-nolattice",
            edges=(ContextEdge(src=USD, dst=EUR, map=LinearMap(0.9214)),),
        )
        with using_context(edges):
            result = Number(100.0, USD).to(EUR)
        # With no lattice, `_resolve_default_kind` finds nothing to resolve
        # against, so the kind is left untouched rather than invented.
        self.assertIsNone(result.kind)


if __name__ == "__main__":
    unittest.main()
