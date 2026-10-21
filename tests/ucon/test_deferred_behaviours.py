# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""Behaviour that is known-wrong and deliberately deferred.

Every assertion in this file pins what ucon does **today**, not what it
ought to do: each one is a filed, blocked defect whose fix is sequenced
on the ROADMAP behind a release that has not happened. A failure here
therefore means the behaviour *changed* — read the failing test's
docstring, which names the issue, what blocks it, and the release that
closes it, and then move the pin rather than re-diagnosing the symptom.
This file is **not** a specification of intent: nothing asserted here is
desirable, and nothing here may be cited as a contract downstream.

The reason it exists is that symptoms of these causes keep being
rediscovered and re-derived from scratch — `3 nines * 2` refusing while
`3 nines + 3 nines` admits is #341, filed, with the diagnosis written
down. `tests/ucon/core/test_operator_stratum_grid.py` does the same job
for the operator x stratum cross-product; this file does it for
behaviours that are not cells of that grid.

Where a behaviour is wrong because it contradicts a *second* behaviour,
both sides are asserted in one test, so the pin is the contradiction and
not half of it.
"""

from __future__ import annotations

import pytest

from ucon import (
    DimensionMismatch,
    KindDimensionMismatch,
    Number,
    ScalarArithmeticRefused,
    parse_unit,
    units,
)
from ucon._active import active


class TestNinesScalarVersusAdditive:
    """#341 — the `nines` edge hides a change of quantity."""

    def test_scalar_refuses_while_the_equivalent_sum_admits(self) -> None:
        """`3 nines * 2` refuses; `3 nines + 3 nines` answers `<6 9s>`.

        Issue: #341 (`nines` composes an inner `x ↦ 1 − x` — a change of
        *quantity* — into a `map` whose job is a change of *scale*, so
        the unit charts unavailability while the edge's far end is
        availability).

        Blocked by: the `Dimension(none)`/`Dimension(ratio)` fiber merge
        in 3.0.0's pseudo-dimension retirement, alongside the
        dimensionless kinds of #344.

        Fixed in: v3.1.0 (ROADMAP, *The post-retirement KOQ floor*).

        The contradiction is the point. #340 derived scalar `*` from
        repeated addition (`a * n == a + a + …`) and gated it on
        `Graph.scale_class`, which reads `nines` as a `level`. But
        `nines` addition has exactly one meaning and it is sound — the
        parallel-redundancy law, `−log₁₀[(1−x)(1−y)]` — so the sum
        admits and answers the same `<6 9s>` the refused product would
        have. One of the two is wrong; #341 says which, and why neither
        can be fixed locally.
        """
        with pytest.raises(ScalarArithmeticRefused):
            Number(3, units.nines) * 2

        total = Number(3, units.nines) + Number(3, units.nines)
        assert str(total) == '<6 9s>'
        # And the sum is not nonsense: 1e-3 unavailability squared.
        assert str(total.to(units.fraction)) == '<0.999999 frac>'

    def test_the_gain_sibling_admits_the_scalar(self) -> None:
        """`3 dB * 2` admits where `3 nines * 2` refuses.

        Issue: #341. Blocked by: as above. Fixed in: v3.1.0.

        Both units are logarithmic, and `decibel` relates affinely to
        `bel` while `nines` relates to `decibel` non-affinely — which is
        #341's consequence clause: nothing keyed on "logarithmic" can
        treat the catalog's levels uniformly while this edge stands.
        """
        assert str(Number(3, units.decibel) * 2) == '<6 dB>'
        with pytest.raises(ScalarArithmeticRefused):
            Number(3, units.nines) * 2


class TestSameUnitAdditiveOnNonRatioCharts:
    """The additive half of #340's hole — no chart dispatch yet."""

    def test_identical_points_and_levels_add(self) -> None:
        """`20 °C + 20 °C → <40 °C>`; `10 dBW + 10 dBW → <20 dBW>`.

        Issue: none filed on its own — it is the remainder #340
        explicitly placed out of scope (see
        `Number._require_scalar_scaling`: "`20 °C + 20 °C` still answers
        `<40 °C>`, because `_require_normalizable` exempts same-unit
        operands … Closing that is the additive half of the same hole").

        Blocked by: four-stratum arithmetic dispatch — the chart stratum
        is the only one that must refuse on *identical* operands (ADR
        009 §3, "Chart is the only stratum that refuses on identical
        operands"), and every check `Number` currently runs is
        difference-based.

        Fixed in: v3.2.0 (ROADMAP, *Where the chart defects land*:
        "`20 °C + 5 °C` refuses as `point + point`"; and v3.2.0's
        logarithmic-chart dispatch, "`dBm + dB` admits, `dBm + dBm`
        refuses").

        Both sides are asserted because the defect *is* the asymmetry:
        the scalar forms refuse (#340 gated them, having no second
        operand to exempt) while the sums they expand to admit.
        """
        assert str(Number(20, units.celsius)
                   + Number(20, units.celsius)) == '<40 °C>'
        assert str(Number(10, units.decibel_watt)
                   + Number(10, units.decibel_watt)) == '<20 dBW>'
        # The other half of the asymmetry, for contrast: the scalar
        # forms of the very same sums are gated.
        with pytest.raises(ScalarArithmeticRefused):
            Number(20, units.celsius) * 2
        with pytest.raises(ScalarArithmeticRefused):
            Number(10, units.decibel_watt) * 2

    def test_a_product_crosses_the_chart_without_comment(self) -> None:
        """`1 °C * 1 K → <1 °C·K>`.

        Issue: none filed on its own. Blocked by: chart dispatch, as
        above — multiplication consults dimension, kind and aspect and
        never the chart. Fixed in: v3.2.0 (ROADMAP, "Chart-crossing
        arithmetic returns a value").

        `tests/ucon/core/test_operator_stratum_grid.py` pins this cell's
        *classification* (it admits); what is pinned here is the value,
        so that an interval coordinate silently entering a product
        signature is visible.
        """
        assert str(Number(1, units.celsius) * Number(1, units.kelvin)) \
            == '<1 °C·K>'


class TestLumenBaseForm:
    """#346 — `lumen.base_form` is `cd`, so `lm → cd` passes."""

    def test_lumen_converts_to_candela(self) -> None:
        """`1 lm → <1.0 cd>`, because `lumen` and `candela` share a form.

        Issue: #346 (`lumen.base_form` is `cd`, not `cd·sr`, so the two
        units are indistinguishable to every `base_form` consumer).

        Blocked by: `steradian` being pseudo-dimensional —
        `BaseForm.factors` may reference only canonical base units, and
        the BFS oracle skips pseudo-dimensional units — which is #348
        and ADR 013's retirement at 3.0.0.

        Fixed in: v3.1.0 (ROADMAP: "`lumen.base_form = cd·sr`,
        unwritable while `steradian` is pseudo-dimensional").
        """
        assert str(Number(1, units.lumen).to(units.candela)) == '<1.0 cd>'
        assert units.lumen.base_form == units.candela.base_form
        assert [u.name for u, _ in units.lumen.base_form.factors] \
            == ['candela']


class TestDimensionlessKindsCannotAttach:
    """#344 — the dimensionless KOQ cluster has no kinds to attach."""

    def test_the_only_none_dimension_kind_refuses_percent_and_fraction(
        self,
    ) -> None:
        """A `Dimension(none)` kind cannot sit on a `Dimension(ratio)` unit.

        Issue: #344 (the dimensionless KOQ cluster — efficiency, strain,
        Reynolds, Mach and the rest — is undeclared; the catalog holds
        exactly one kind on `Dimension(none)`,
        `radiation_weighting_factor`, and `percent`/`fraction` carry
        `Dimension(ratio)`, a different fiber).

        Blocked by: the fiber merge — `Dimension(none)` and
        `Dimension(ratio)` becoming one fiber — prepared by #307 and
        #318 at v2.3.1 and landing with 3.0.0's pseudo-dimension
        retirement (`ratio` empties into `Scale`).

        Fixed in: v3.1.0 (ROADMAP: "the ten dimensionless kinds beyond
        the angle set, now that `Dimension(none)` and
        `Dimension(ratio)` are one fiber rather than two (#344)").
        """
        lattice = active().kinds
        none_kind = lattice.get('radiation_weighting_factor')

        for unit in (units.percent, units.fraction):
            with pytest.raises(KindDimensionMismatch):
                Number(1, unit, kind=none_kind)

        # Why there is no second kind to try: the ratio fiber is empty,
        # and the none fiber holds that one kind.
        assert lattice.kinds_for_dimension(units.percent.dimension) == []
        assert [k.name for k
                in lattice.kinds_for_dimension(none_kind.dimension)] \
            == ['radiation_weighting_factor']


class TestSteradianIsNotRadianSquared:
    """#348 — `sr = rad²` is unrepresentable."""

    def test_the_relation_refuses_in_both_directions(self) -> None:
        """`rad² ↔ sr` refuses, and the tag algebra is idempotent.

        Issue: #348 (`sr = rad²` survives only as a hand-squared edge
        factor; the pseudo-dimension tags are *idempotent*, so
        `angle × angle` is `angle`, not `solid_angle`, and the relation
        cannot be written down).

        Blocked by: 3.0.0's pseudo-dimension retirement (the tags must
        be gone) plus composing kinds — a normal-form `DerivedKind` —
        which is v3.2.0.

        Fixed in: v3.1.0 (ROADMAP: "`sr = rad²` made representable,
        which needs both the tags gone and composing kinds (#348)").

        Both halves are pinned together: the refusal is a *symptom* of
        the idempotence, so changing either without the other is the
        error this test is here to catch.
        """
        with pytest.raises(DimensionMismatch):
            Number(1, parse_unit('rad^2')).to(units.steradian)
        with pytest.raises(DimensionMismatch):
            Number(1, units.steradian).to(parse_unit('rad^2'))

        angle = units.radian.dimension
        assert angle * angle == angle
        assert angle != units.steradian.dimension


class TestNumberIsUnhashable:
    """#353's remaining half — `Number` has no `__hash__`."""

    def test_hashing_a_number_raises(self) -> None:
        """`hash(units.meter(1))` is a `TypeError`.

        Issue: #353 (the comparison protocol's unshipped half — defining
        `__eq__` without `__hash__` makes Python set `__hash__ = None`,
        so a `Number` cannot be a dict key, enter a set, or be
        `lru_cache`d).

        Blocked by: #362, freezing `Number` — it is a mutable dataclass,
        and hashing mutable fields is the hazard `__hash__ = None`
        exists to prevent. The hash must also be taken on the canonical
        magnitude, since `1 m == 100 cm`.

        Fixed in: v3.0.0 (ROADMAP v2.3.0, "Not in this release:
        `__hash__` … blocked rather than deferred … the hash waits on
        freezing it (#362, 3.0.0)"; ADR 009 sequences "`Number` frozen"
        there).
        """
        with pytest.raises(TypeError):
            hash(units.meter(1))

        # The contradiction, for the record: equality is defined and
        # total, so the type behaves as a value everywhere but a dict.
        assert units.meter(1) == parse_unit('centimeter')(100)


class TestExponentiationDropsTheKind:
    """`**` yields an unkinded result."""

    def test_squaring_a_kinded_number_loses_the_kind(self) -> None:
        """`(1 Gy[absorbed_dose]) ** 2` has `kind is None`.

        Issue: none filed on its own — it is a ROADMAP deliverable.

        Blocked by: the kind algebra. There is no `**` dispatch row;
        kinds do not compose, so there is nothing for the operator to
        answer with. A normal-form `DerivedKind` and "a `**` dispatch
        row" are v3.2.0 (ADR 013 §4).

        Fixed in: v2.3.1 (ROADMAP, *Unity and the dimensionless fold*:
        "`**` never yields an unkinded result").
        """
        dose = active().kinds.get('absorbed_dose')
        kinded = Number(1, units.gray, kind=dose)
        assert kinded.kind is dose
        assert (kinded ** 2).kind is None


class TestDegeneracyClustersConvertFreely:
    """#342, #343 — product signatures carry no `default_kind`."""

    def test_torque_converts_to_energy(self) -> None:
        """`1 N·m → <1.0 J>`.

        Issue: #342 (the torque/energy cluster converts freely; `torque`
        is a descendant of `energy`, and the distinguishing unit is a
        `UnitProduct`, which cannot declare a kind).

        Blocked by: `default_kind` on product-unit **signatures** — the
        mechanism v2.4.0 introduces. v2.3.0 shipped `default_kind` on
        `Unit` only, so a `UnitProduct` has nowhere to carry the
        fiber's generic kind.

        Fixed in: v2.4.0 (ROADMAP, *The pre-retirement KOQ floor*).
        """
        assert str(Number(1, parse_unit('N*m')).to(units.joule)) == '<1.0 J>'

    def test_pressure_converts_to_energy_density(self) -> None:
        """`1 Pa → <1.0 J/m³>`.

        Issue: #343 (the pressure/stress/energy-density cluster converts
        freely, and no unit declares the sibling kinds that already
        exist).

        Blocked by: the same missing mechanism as #342 — `default_kind`
        on product signatures; `J/m^3` is a `UnitProduct`.

        Fixed in: v2.4.0 (ROADMAP, *The pre-retirement KOQ floor*).
        """
        assert str(Number(1, units.pascal).to(parse_unit('J/m^3'))) \
            == '<1.0 J/m³>'
