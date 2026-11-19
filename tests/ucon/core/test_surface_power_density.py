# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
"""The surface power density cluster — three quantities sharing W/m².

Covers two of the unclustered `koq_mismatch` must-fails in UnitSafe (#344).
`irradiance`, `radiative_forcing` and `heat_flux` are distinct ISO 80000-7 /
IPCC quantities on one unit, so nothing about the unit distinguishes them; the
caller states which is meant and a crossing refuses.

The dimension is also the first in the catalog carried by a kind as an
*expression* (`mass/time^3`) rather than a registered name — W/m² reduces to
M·T⁻³, which SI does not name.
"""

import pytest

from ucon import Number, parse_unit
from ucon.core.exceptions import KindClaimRefused
from ucon.system import active_kinds


@pytest.fixture
def kinds():
    return active_kinds()


@pytest.fixture
def wm2():
    return parse_unit('W/m^2')


class TestFamilyIsDeclared:
    def test_all_four_kinds_load(self, kinds):
        for name in ('surface_power_density', 'irradiance',
                     'radiative_forcing', 'heat_flux'):
            assert kinds.get(name) is not None, name

    def test_the_root_refuses_joins(self, kinds):
        """Disjoint siblings, matching the power/pressure/frequency idiom."""
        from ucon.kinds.types import JoinPolicy
        root = kinds.get('surface_power_density')
        assert root.join_policy is JoinPolicy.REFUSE
        assert root.parent is None

    def test_the_dimension_matches_watts_per_square_metre(self, kinds, wm2):
        assert kinds.get('irradiance').dimension == wm2.dimension

    def test_the_dimension_survives_a_toml_round_trip(self, kinds):
        """``derived(mass/time^3)`` is a rendering, not an identifier.

        Serializing the name would emit something ``parse_dimension`` rejects,
        so the expression form is written instead.
        """
        from ucon.parsing.dimensions import parse_dimension
        from ucon.serialization import _dimension_to_expression
        dim = kinds.get('heat_flux').dimension
        expression = _dimension_to_expression(dim)
        assert not expression.startswith('derived(')
        assert parse_dimension(expression) == dim


class TestTheMustFails:
    def test_forcing_equated_with_heat_flux_refuses(self, kinds, wm2):
        """*"Equate radiative forcing (W/m²) with heat flux (W/m²) as
        physically identical quantities."*"""
        value = Number(1, wm2, kind=kinds.get('radiative_forcing'))
        with pytest.raises(KindClaimRefused):
            value.to(wm2, kind='heat_flux')

    def test_irradiance_reported_as_forcing_refuses(self, kinds, wm2):
        """*"Report solar irradiance (W/m²) as radiative forcing (W/m²)
        without accounting for albedo ..."*"""
        value = Number(1, wm2, kind=kinds.get('irradiance'))
        with pytest.raises(KindClaimRefused):
            value.to(wm2, kind='radiative_forcing')

    def test_the_crossing_refuses_in_both_directions(self, kinds, wm2):
        value = Number(1, wm2, kind=kinds.get('heat_flux'))
        with pytest.raises(KindClaimRefused):
            value.to(wm2, kind='irradiance')


class TestTheMustPasses:
    """Every must-pass row in this cluster is a same-kind unit conversion."""

    @pytest.mark.parametrize('src,dst,kind,expected', [
        ('W/m^2', 'mW/cm^2', 'irradiance', 0.1),
        ('W/m^2', 'mW/m^2', 'radiative_forcing', 1000.0),
        ('kW/m^2', 'W/m^2', 'heat_flux', 1000.0),
    ])
    def test_same_kind_conversions_admit(self, kinds, src, dst, kind, expected):
        result = Number(1, parse_unit(src), kind=kinds.get(kind)).to(
            parse_unit(dst), kind=kind)
        assert result.kind.name == kind
        assert result.quantity == pytest.approx(expected)

    def test_unclaimed_conversion_is_unchanged(self, wm2):
        """Nothing is forced onto a bare W/m²: the unit does not say which
        quantity it carries, so no ``default_kind`` is attached."""
        assert Number(1, wm2).kind is None
        result = Number(1, wm2).to(parse_unit('mW/cm^2'))
        assert result.quantity == pytest.approx(0.1)
        assert result.kind is None

    def test_weakening_to_the_generic_refuses(self, kinds, wm2):
        """The root declines to stand for its children, as ``energy`` does.

        Weakening is admitted only where the ancestor's ``join_policy``
        permits generalizing; ``surface_power_density`` is declared
        ``refuse``, so a forcing may not be reported as merely "some surface
        power density".
        """
        value = Number(1, wm2, kind=kinds.get('radiative_forcing'))
        with pytest.raises(KindClaimRefused):
            value.to(wm2, kind='surface_power_density')
