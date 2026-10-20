# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Tests for BaseForm, UnitProduct.to_base_form(), and the arithmetic
regressions that motivated the base-unit decomposition feature.

In v1.3.0, ``BaseForm`` is *definitional*: it is set on each ``Unit`` at
construction time in ``ucon/units.py`` and never mutated thereafter.
The previous v1.2.x behavior populated this field lazily by walking the
``ConversionGraph`` after import; that mechanism (and the ``_ensure_graph``
autouse fixture it required) is gone.

The ``TestNoGraphInit`` class below proves the new property: arithmetic
on quantities works *without* the default ``ConversionGraph`` ever being
materialized.
"""

import math
from fractions import Fraction
import subprocess
import sys

import pytest

from ucon import Scale, Number, Ratio, UnitsNotNormalizable
from ucon import units
from ucon.core import BaseForm, UnitProduct, UnitFactor
from ucon import graph as graph_mod
from ucon.core import Unit
from ucon.conversion import get_default_graph
from ucon.dimension import LENGTH, TEMPERATURE
from ucon.maps import AffineMap


# -----------------------------------------------------------------------
# TestNoGraphInit — graph independence regression net
# -----------------------------------------------------------------------

class TestNoGraphInit:
    """Verify that base_form works WITHOUT initializing the default graph.

    These tests prove that v1.3.0's definitional ``base_form`` is independent
    of the conversion graph. They monkeypatch out the cached default graph
    and assert that core arithmetic still works.
    """

    def test_kilogram_base_form_no_graph(self, monkeypatch):
        monkeypatch.setattr(graph_mod, '_default_graph', None, raising=False)
        assert units.kilogram.base_form is not None
        assert units.kilogram.base_form.prefactor == 1.0

    def test_canonical_magnitude_no_graph(self, monkeypatch):
        monkeypatch.setattr(graph_mod, '_default_graph', None, raising=False)
        n = units.gram(1000)
        assert abs(n._canonical_magnitude - 1.0) < 1e-12

    def test_arithmetic_no_graph(self, monkeypatch):
        monkeypatch.setattr(graph_mod, '_default_graph', None, raising=False)
        n = units.newton(1)
        d = (Scale.kilo * units.gram * units.meter / units.second ** 2)(1)
        assert n == d  # must work with no graph initialized

    def test_cold_start_subprocess(self):
        """A truly fresh interpreter must not need the default graph for
        ``units.gram(1000) == units.kilogram(1)`` to hold.

        Subprocess isolation guarantees no test-suite import has already
        triggered graph construction as a side effect.
        """
        code = (
            "from ucon import units; "
            "assert units.gram(1000) == units.kilogram(1)"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"cold-start smoke test failed:\n"
            f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
        )


# -----------------------------------------------------------------------
# BaseForm field tests
# -----------------------------------------------------------------------

class TestBaseFormField:
    """Verify base_form is set correctly on standard units."""

    def test_kilogram_prefactor(self):
        assert units.kilogram.base_form is not None
        assert units.kilogram.base_form.prefactor == 1.0

    def test_kilogram_factors(self):
        bf = units.kilogram.base_form
        assert len(bf.factors) == 1
        assert bf.factors[0] == (units.kilogram, 1.0)

    def test_gram_prefactor(self):
        bf = units.gram.base_form
        assert bf is not None
        assert abs(bf.prefactor - 0.001) < 1e-12

    def test_meter_prefactor(self):
        bf = units.meter.base_form
        assert bf is not None
        assert bf.prefactor == 1.0

    def test_second_prefactor(self):
        bf = units.second.base_form
        assert bf is not None
        assert bf.prefactor == 1.0

    def test_pascal_prefactor(self):
        bf = units.pascal.base_form
        assert bf is not None
        assert abs(bf.prefactor - 1.0) < 1e-12

    def test_pascal_factors(self):
        bf = units.pascal.base_form
        factor_dict = dict(bf.factors)
        assert abs(factor_dict[units.kilogram] - 1.0) < 1e-12
        assert abs(factor_dict[units.meter] - (-1.0)) < 1e-12
        assert abs(factor_dict[units.second] - (-2.0)) < 1e-12

    def test_bar_prefactor(self):
        bf = units.bar.base_form
        assert bf is not None
        assert abs(bf.prefactor - 100000.0) < 1e-6

    def test_foot_prefactor(self):
        bf = units.foot.base_form
        assert bf is not None
        assert abs(bf.prefactor - 0.3048) < 1e-6

    def test_calorie_prefactor(self):
        bf = units.calorie.base_form
        assert bf is not None
        assert abs(bf.prefactor - 4.184) < 1e-6

    def test_newton_prefactor(self):
        bf = units.newton.base_form
        assert bf is not None
        assert abs(bf.prefactor - 1.0) < 1e-12

    def test_joule_prefactor(self):
        bf = units.joule.base_form
        assert bf is not None
        assert abs(bf.prefactor - 1.0) < 1e-12

    def test_watt_prefactor(self):
        bf = units.watt.base_form
        assert bf is not None
        assert abs(bf.prefactor - 1.0) < 1e-12

    def test_dimensionless_unit_has_no_base_form(self):
        u = Unit()
        assert u.base_form is None

    def test_celsius_has_no_base_form(self):
        """Affine units cannot be expressed as (prefactor, factors)."""
        assert units.celsius.base_form is None

    def test_fahrenheit_has_no_base_form(self):
        assert units.fahrenheit.base_form is None


# -----------------------------------------------------------------------
# to_base_form() tests
# -----------------------------------------------------------------------

class TestToBaseForm:
    """Verify UnitProduct.to_base_form() algebraic expansion."""

    def test_pascal_times_second(self):
        """Pa·s should expand to kg·m⁻¹·s⁻¹ with prefactor 1.0."""
        up = units.pascal * units.second
        base_factors, prefactor = up.to_base_form()
        assert abs(prefactor - 1.0) < 1e-12
        assert abs(base_factors[units.kilogram] - 1.0) < 1e-12
        assert abs(base_factors[units.meter] - (-1.0)) < 1e-12
        assert abs(base_factors[units.second] - (-1.0)) < 1e-12

    def test_kg_m_per_s_squared(self):
        """kg·m/s² should expand to {kg:1, m:1, s:-2} with prefactor 1.0."""
        up = UnitProduct({
            UnitFactor(units.kilogram, Scale.one): 1,
            UnitFactor(units.meter, Scale.one): 1,
            UnitFactor(units.second, Scale.one): -2,
        })
        base_factors, prefactor = up.to_base_form()
        assert abs(prefactor - 1.0) < 1e-12
        assert abs(base_factors[units.kilogram] - 1.0) < 1e-12
        assert abs(base_factors[units.meter] - 1.0) < 1e-12
        assert abs(base_factors[units.second] - (-2.0)) < 1e-12

    def test_bar_times_second(self):
        """bar·s should have prefactor 100000."""
        up = units.bar * units.second
        base_factors, prefactor = up.to_base_form()
        assert abs(prefactor - 100000.0) < 1e-6
        assert abs(base_factors[units.kilogram] - 1.0) < 1e-12
        assert abs(base_factors[units.meter] - (-1.0)) < 1e-12
        assert abs(base_factors[units.second] - (-1.0)) < 1e-12

    def test_kilo_gram_product(self):
        """kilo*gram should have prefactor 1.0 (= 1 kg in base units)."""
        up = Scale.kilo * units.gram
        _, prefactor = up.to_base_form()
        # kilo * gram: scale=kilo (1000), gram base_form prefactor=0.001
        # total = 1000 * 0.001 = 1.0
        assert abs(prefactor - 1.0) < 1e-12


# -----------------------------------------------------------------------
# Arithmetic regression tests (the motivation for this feature)
# -----------------------------------------------------------------------

class TestArithmeticRegressions:
    """Verify that derived ÷ base-unit expression gives correct dimensionless results."""

    def test_newton_div_kg_m_per_s2(self):
        """N ÷ (kg·m/s²) should equal 1.0."""
        n = units.newton(1)
        d = (Scale.kilo * units.gram * units.meter / units.second ** 2)(1)
        result = n / d
        assert abs(result.quantity - 1.0) < 1e-9

    def test_pascal_div_kg_per_m_s2(self):
        """Pa ÷ (kg/(m·s²)) should equal 1.0."""
        n = units.pascal(1)
        d = (Scale.kilo * units.gram / (units.meter * units.second ** 2))(1)
        result = n / d
        assert abs(result.quantity - 1.0) < 1e-9

    def test_joule_div_kg_m2_per_s2(self):
        """J ÷ (kg·m²/s²) should equal 1.0."""
        n = units.joule(1)
        d = (Scale.kilo * units.gram * units.meter ** 2 / units.second ** 2)(1)
        result = n / d
        assert abs(result.quantity - 1.0) < 1e-9

    def test_watt_div_kg_m2_per_s3(self):
        """W ÷ (kg·m²/s³) should equal 1.0."""
        n = units.watt(1)
        d = (Scale.kilo * units.gram * units.meter ** 2 / units.second ** 3)(1)
        result = n / d
        assert abs(result.quantity - 1.0) < 1e-9

    def test_1000g_eq_1kg(self):
        """1000 g == 1 kg (cross-unit equality via _canonical_magnitude)."""
        assert units.gram(1000) == units.kilogram(1)

    def test_1N_eq_1_kg_m_per_s2(self):
        """1 N == 1 kg·m/s² (derived unit identity)."""
        n = units.newton(1)
        d = (Scale.kilo * units.gram * units.meter / units.second ** 2)(1)
        assert n == d

    def test_500g_div_1kg(self):
        """500 g / 1 kg should equal 0.5 (existing behavior preserved)."""
        result = units.gram(500) / units.kilogram(1)
        assert abs(result.quantity - 0.5) < 1e-12

    def test_km_simplify(self):
        """km(5).simplify() should give 5000 m (simplify unchanged)."""
        km = Scale.kilo * units.meter
        result = km(5).simplify()
        assert abs(result.quantity - 5000.0) < 1e-12

    def test_ratio_newton_over_kg_m_s2(self):
        """Ratio(N(1), kg·m/s²(1)).evaluate().quantity should be 1.0."""
        n = units.newton(1)
        d = (Scale.kilo * units.gram * units.meter / units.second ** 2)(1)
        r = Ratio(n, d)
        result = r.evaluate()
        assert abs(result.quantity - 1.0) < 1e-9

    def test_reynolds_number(self):
        """Reynolds number: ρ·v·L / μ for water at standard conditions.

        ρ = 1000 kg/m³, v = 1 m/s, L = 0.1 m, μ = 0.001 Pa·s
        Re = 1000 * 1 * 0.1 / 0.001 = 100000
        """
        rho = (Scale.kilo * units.gram / units.meter ** 3)(1000)
        v = (units.meter / units.second)(1)
        L = units.meter(0.1)
        mu = units.pascal_second(0.001)
        Re = (rho * v * L) / mu
        assert abs(Re.quantity - 100000.0) < 1e-6


class TestRankineBaseForm:
    """``rankine`` is a pure scaling of kelvin, so it carries a base_form (#339).

    It had been named in ``generate_base_forms._NULL_BASE_FORM_NAMES`` beside
    the three conventional-zero scales, which asserted its base_form stay
    ``None``. Rankine is the absolute Fahrenheit-degree scale: ``0 °R = 0 K``,
    factor 5/9. Only the degree *size* is Fahrenheit's.
    """

    def test_rankine_prefactor_is_the_exact_seed_rounded_once(self):
        # House convention (v2.1.6/2.1.7, tests/ucon/test_customary_prefactors.py):
        # compose the exact value in ``Fraction`` and convert to float exactly
        # once, then assert *equality* with that double — not a tolerance. The
        # Rankine scale is defined by T/°R = (9/5)(T/K), so the seed is 5/9 and
        # is exact by definition rather than measured.
        bf = units.rankine.base_form
        assert bf is not None
        assert bf.factors == ((units.kelvin, 1.0),)
        assert bf.prefactor == float(Fraction(5, 9))

    def test_rankine_prefactor_matches_its_declared_edge(self):
        # The catalog declares kelvin -> rankine as factor 1.8; the base_form
        # prefactor is its reciprocal and must agree bit-for-bit, or the two
        # routes to kelvin disagree.
        assert units.rankine.base_form.prefactor == 1 / 1.8

    def test_conventional_zero_scales_still_have_none(self):
        # celsius/fahrenheit/reaumur are affine to kelvin; no prefactor can
        # express an offset, so their base_form must stay None.
        assert units.celsius.base_form is None
        assert units.fahrenheit.base_form is None
        assert units.reaumur.base_form is None

    def test_rankine_shares_kelvins_zero(self):
        assert abs(units.rankine(0).to(units.kelvin).quantity) < 1e-15

    def test_canonical_magnitude_is_in_kelvin(self):
        # Before #339 this silently returned the raw quantity (20), because
        # _canonical_magnitude falls back to it when base_form is None.
        assert abs(units.rankine(20).canonical_magnitude - 100.0 / 9.0) < 1e-12

    def test_to_base_converts_rather_than_no_ops(self):
        assert abs(units.rankine(20).to_base().quantity - 100.0 / 9.0) < 1e-12

    def test_addition_with_kelvin_is_admitted(self):
        # The missing base_form made this raise UnitsNotNormalizable.
        result = units.rankine(20) + units.kelvin(5)
        assert abs(result.to(units.kelvin).quantity - (100.0 / 9.0 + 5.0)) < 1e-12


class TestAffineScalesAreSelfSuppressing:
    """The BFS oracle must not mint a base_form across an offset (#339).

    ``_NULL_BASE_FORM_NAMES`` used to list the conventional-zero temperature
    scales by hand, because the oracle propagated an affine edge's *slope* and
    ignored its offset — minting ``1·K`` for ``celsius``. The oracle now
    refuses to cross an offset-bearing edge, so those units are absent from
    the expected map on their own and the list is empty.
    """

    def _expected(self):
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
        from generate_base_forms import _compute_expected_base_forms
        from ucon.conversion import get_default_graph
        return _compute_expected_base_forms(get_default_graph())

    def test_allowlist_is_empty(self):
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
        from generate_base_forms import _NULL_BASE_FORM_NAMES
        assert _NULL_BASE_FORM_NAMES == set()

    def test_conventional_zero_scales_are_not_derived(self):
        expected = self._expected()
        for u in (units.celsius, units.fahrenheit, units.reaumur):
            assert u not in expected, f"{u.name} must not be derivable across its offset"

    def test_pure_scaling_sibling_is_derived(self):
        # rankine shares kelvin's zero, so the oracle must reach it.
        expected = self._expected()
        assert units.rankine in expected
        assert abs(expected[units.rankine].prefactor - 5.0 / 9.0) < 1e-15


# -----------------------------------------------------------------------
# BaseForm validates its own invariants (#340)
# -----------------------------------------------------------------------

class TestBaseFormValidation:
    """``BaseForm`` enforced none of the invariants its docstring claimed.

    ``BaseForm(factors=(), prefactor=-1)``, ``nan``, ``0.0`` and the
    empty factor tuple were all accepted, so a ``base_form`` that existed
    was no evidence that it meant anything.
    """

    @pytest.mark.parametrize("prefactor", [
        -1, -1.0, 0, 0.0, float("nan"), float("inf"), float("-inf"),
    ])
    def test_prefactor_must_be_positive_and_finite(self, prefactor):
        with pytest.raises(ValueError, match="positive and finite"):
            BaseForm(factors=((units.meter, 1.0),), prefactor=prefactor)

    @pytest.mark.parametrize("prefactor", ["1.0", None, object()])
    def test_prefactor_must_be_a_real_number(self, prefactor):
        with pytest.raises(TypeError, match="real number"):
            BaseForm(factors=((units.meter, 1.0),), prefactor=prefactor)

    def test_exact_rational_prefactor_is_admitted(self):
        """Strict on value, permissive on type: a ``Fraction`` is a real."""
        bf = BaseForm(factors=((units.meter, 1.0),), prefactor=Fraction(1, 3))
        assert float(bf.prefactor) == pytest.approx(1 / 3)

    def test_factors_must_be_non_empty(self):
        """The empty product is not a decomposition — see the ADR 013 note.

        A dimensionless unit carries ``base_form=None``; the route to
        making one normalizable is a self-referential factorization, which
        is non-empty. Admitting ``()`` would also give every dimensionless
        unit the same empty ``base_signature``.
        """
        with pytest.raises(ValueError, match="at least one factor"):
            BaseForm(factors=())
        with pytest.raises(ValueError, match="at least one factor"):
            BaseForm(factors=(), prefactor=2.0)

    @pytest.mark.parametrize("factors", [
        ((units.meter,),),
        ((units.meter, 1.0, 2.0),),
        ([units.meter, 1.0],),
        ("meter",),
    ])
    def test_factors_must_be_unit_exponent_pairs(self, factors):
        with pytest.raises(TypeError):
            BaseForm(factors=factors)

    def test_factor_exponent_must_be_a_real_number(self):
        with pytest.raises(TypeError, match="exponent"):
            BaseForm(factors=((units.meter, "1.0"),))

    def test_nothing_shipped_violates_the_invariants(self):
        """The validation is a guard, not a migration: the catalog is clean.

        Checked over the graph's nodes rather than ``ucon.units``, so the
        TOML loader and the cache round-trip are both covered.
        """
        graph = get_default_graph()
        checked = 0
        for adjacency in graph._unit_edges.values():
            for node in adjacency:
                bf = getattr(node, "base_form", None)
                if bf is None:
                    continue
                checked += 1
                assert bf.factors, f"{node.name} has an empty base_form"
                assert bf.prefactor > 0 and math.isfinite(bf.prefactor), (
                    f"{node.name} has prefactor {bf.prefactor!r}"
                )
        assert checked > 100, "sweep found suspiciously few base forms"


# -----------------------------------------------------------------------
# _set_base_form guards the normalizability proxy (#340)
# -----------------------------------------------------------------------

class TestSetBaseFormGuard:
    """``_set_base_form`` guarded only "already set".

    One call installing a plausible ``BaseForm`` on ``decibel_watt`` made
    ``10 dBW + 1 W`` answer ``<11.0 dBW>`` — 11 W is 10.414 dBW — with
    ``make base-forms-check`` still green. The proxy "nothing with a
    populated base_form has a non-ratio chart" was a contingent fact
    about the shipped TOML; the guard makes it structural.
    """

    _WATT_FORM = ((units.kilogram, 1.0), (units.meter, 2.0),
                  (units.second, -3.0))

    def test_a_level_is_refused(self):
        with pytest.raises(ValueError, match="level coordinate"):
            units.decibel_watt._set_base_form(
                BaseForm(self._WATT_FORM, 1.0)
            )

    def test_the_refusal_keeps_the_2_2_2_guard_sound(self):
        """The attack from the issue, run and then checked."""
        with pytest.raises(ValueError):
            units.decibel_watt._set_base_form(
                BaseForm(self._WATT_FORM, 1.0)
            )
        assert units.decibel_watt.base_form is None
        with pytest.raises(UnitsNotNormalizable):
            Number(10, units.decibel_watt) + Number(1, units.watt)

    @pytest.mark.parametrize("name", [
        "decibel_milliwatt", "decibel_volt", "decibel_spl",
    ])
    def test_every_shipped_level_is_refused(self, name):
        with pytest.raises(ValueError, match="level coordinate"):
            getattr(units, name)._set_base_form(
                BaseForm(self._WATT_FORM, 1.0)
            )

    def test_an_interval_point_is_refused(self):
        with pytest.raises(ValueError, match="point coordinate"):
            units.celsius._set_base_form(
                BaseForm(((units.kelvin, 1.0),), 1.0)
            )

    def test_reaumur_is_refused_though_its_own_edge_has_no_offset(self):
        """The case locality misses.

        ``reaumur``'s only declared edge is a pure scaling to ``celsius``.
        It must stay ``None`` all the same, because its only path to
        ``kelvin`` runs through ``celsius``'s offset — so the guard walks
        the multiplicative neighbourhood rather than the unit's own edges.
        """
        with pytest.raises(ValueError, match="point coordinate"):
            units.reaumur._set_base_form(
                BaseForm(((units.kelvin, 1.0),), 1.25)
            )

    def test_a_gain_is_refused_too(self):
        """``dB`` admits scalar arithmetic but still has no base form.

        The two acceptance sets differ on purpose: a gain composes under
        addition, and has no ``(prefactor, factors)`` representation in
        SI base units.
        """
        with pytest.raises(ValueError, match="gain coordinate"):
            units.decibel._set_base_form(BaseForm(((units.meter, 1.0),)))

    def test_a_unit_with_no_declared_edges_is_still_admitted(self):
        """What keeps the two sanctioned callers working.

        ``base_form`` is resolved in load pass 6b; edges are materialized
        in pass 9. A unit the graph declares nothing about reads as a
        ratio scale, because absence of structure is not evidence of
        non-ratio structure.
        """
        metre = Unit(name="metre", dimension=LENGTH, aliases=("metre",))
        metre._set_base_form(units.meter.base_form)
        assert metre.base_form is units.meter.base_form

    def test_a_foreign_interval_unit_is_admitted_for_the_same_reason(self):
        """The declared gap, stated: locality is not the limit, declaration is.

        A brand-new temperature unit nothing has wired up is indistinguishable
        from an unanchored ratio scale, so the guard admits it.
        """
        centigrade = Unit(name="centigrade", dimension=TEMPERATURE)
        centigrade._set_base_form(BaseForm(((units.kelvin, 1.0),), 1.0))
        assert centigrade.base_form is not None

    def test_the_prior_guards_still_hold(self):
        with pytest.raises(TypeError, match="expects a BaseForm"):
            units.meter._set_base_form("not a base form")
        with pytest.raises(ValueError, match="already set"):
            units.meter._set_base_form(BaseForm(((units.meter, 1.0),)))


# -----------------------------------------------------------------------
# Graph.scale_class — the structural query both guards ask (#340)
# -----------------------------------------------------------------------

class TestScaleClass:
    """The #356 edge rule, read from a unit outward instead of inward.

    ``scripts/generate_base_forms.py`` refuses to propagate a base form
    across a log/exp edge or an offset-bearing affine edge.
    ``Graph.scale_class`` walks the same two blocks in the other
    direction, so the operators and the mutation contract can ask offline
    what the oracle answers.
    """

    @pytest.mark.parametrize(("name", "expected"), [
        ("meter", "ratio"),
        ("kelvin", "ratio"),
        ("rankine", "ratio"),      # a pure scaling of kelvin, true zero
        ("gray", "ratio"),
        ("radian", "ratio"),       # unanchored pseudo-dimension
        ("percent", "ratio"),
        ("fraction", "ratio"),     # the referent side of every log edge
        ("gauss", "ratio"),        # cross-basis, no same-dimension edges
        ("celsius", "point"),
        ("fahrenheit", "point"),
        ("reaumur", "point"),
        ("decibel", "gain"),
        ("bel", "gain"),
        ("neper", "gain"),
        ("decibel_watt", "level"),
        ("decibel_milliwatt", "level"),
        ("decibel_volt", "level"),
        ("decibel_spl", "level"),
        ("pH", "level"),           # wired only through a product edge
        ("nines", "level"),        # a composed map, not a bare logarithm
    ])
    def test_shipped_classification(self, name, expected):
        assert get_default_graph().scale_class(getattr(units, name)) == expected

    def test_only_eleven_shipped_units_are_not_ratio_scales(self):
        """The whole catalog, so a new non-ratio unit shows up here."""
        graph = get_default_graph()
        verdicts = {}
        for adjacency in graph._unit_edges.values():
            for node in adjacency:
                if isinstance(node, Unit) and type(node) is Unit:
                    verdicts[node.name] = graph.scale_class(node)
        for name in ("pH", "nines"):
            verdicts[name] = graph.scale_class(getattr(units, name))
        assert sorted(n for n, v in verdicts.items() if v == "point") == [
            "celsius", "fahrenheit", "reaumur",
        ]
        assert sorted(n for n, v in verdicts.items() if v == "gain") == [
            "bel", "decibel", "neper",
        ]
        assert sorted(n for n, v in verdicts.items() if v == "level") == [
            "decibel_milliwatt", "decibel_spl", "decibel_volt",
            "decibel_watt", "nines", "pH",
        ]

    def test_a_new_edge_invalidates_the_memoized_verdict(self):
        """The verdict is cached per graph, so `add_edge` must clear it.

        A freshly-declared unit reads as a ratio scale until the edge that
        makes it a point arrives.
        """
        graph = get_default_graph().copy()
        centigrade = Unit(name="centigrade_edge", dimension=TEMPERATURE)
        graph.register_unit(centigrade)
        assert graph.scale_class(centigrade) == "ratio"
        graph.add_edge(
            src=centigrade, dst=units.kelvin, map=AffineMap(a=1.0, b=273.15),
        )
        assert graph.scale_class(centigrade) == "point"

    def test_a_product_is_as_unscalable_as_its_worst_factor(self):
        graph = get_default_graph()
        assert graph.scale_class(units.meter / units.second) == "ratio"
        assert graph.scale_class(units.celsius / units.second) == "point"
        assert graph.scale_class(units.decibel_watt / units.second) == "level"

    def test_no_non_ratio_unit_carries_a_base_form(self):
        """The positive assertion ``_NULL_BASE_FORM_NAMES`` used to make.

        The allowlist emptied in #339 once the oracle became
        self-suppressing, and its surviving comment records that the
        *positive* claim — "these units must stay ``None``" — had no
        replacement, because absence from the expected map conflates
        "underivable" with "unreached". ``scale_class`` separates the two,
        so the claim is assertable again: this is the invariant the v2.2.2
        normalizability proxy rests on.
        """
        graph = get_default_graph()
        offenders = []
        for adjacency in graph._unit_edges.values():
            for node in adjacency:
                if getattr(node, "base_form", None) is None:
                    continue
                verdict = graph.scale_class(node)
                if verdict != "ratio":
                    offenders.append((node.name, verdict))
        assert offenders == []
