# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
"""``Number.to(..., aspect=)`` — the aspect the caller claims the result carries.

Closes the last two must-fails of UnitSafe's
``cluster_7_Pa_stress_energy_density`` (#343). They are the cases where the
quantity is the same on both sides and only an *adjective* differs, so neither
a unit nor a kind can separate them.

The pair of behaviours this file exists to hold apart:

* ``static + dynamic`` must **sum** — Bernoulli's ``P0 = P + ½ρV²`` is a
  must-pass row, so the family carries ``JoinPolicy.LCA`` and the sum lifts to
  the family root.
* ``dynamic`` reported **as** ``static`` must **refuse**, which the join admits
  and the implication rule does not.
"""

import pytest

from ucon import Number, parse_unit, units
from ucon.aspects.exceptions import (
    AspectClaimRefused,
    AspectError,
    AspectNotApplicable,
)
from ucon.conversion import get_default_graph
from ucon.system import active_kinds


@pytest.fixture
def pressure():
    return active_kinds().get('thermodynamic_pressure')


@pytest.fixture
def aspect():
    forest = get_default_graph()._aspect_forest
    return forest.get


def held(value, unit, kind, aspect_obj):
    return Number(value, unit, kind=kind, aspects=frozenset({aspect_obj}))


class TestFamiliesAreDeclared:
    def test_both_families_load_from_the_catalog(self, aspect):
        for name in (
            'pressure_role', 'static_pressure', 'dynamic_pressure',
            'pressure_origin', 'atmospheric_pressure',
            'lithostatic_pressure', 'hydrostatic_pressure',
        ):
            assert aspect(name) is not None, name

    def test_the_roots_permit_generalizing(self, aspect):
        """``lca``, not ``refuse`` — this is what lets the sum lift."""
        from ucon.kinds.types import JoinPolicy
        assert aspect('pressure_role').join_policy is JoinPolicy.LCA
        assert aspect('pressure_origin').join_policy is JoinPolicy.LCA

    def test_they_do_not_attach_to_an_unkinded_quantity(self, aspect):
        """``applies_to`` names the pressure kinds only.

        Stating a role requires stating what it is a role *of*.
        """
        with pytest.raises(AspectNotApplicable):
            Number(1, units.pascal, aspects=frozenset({aspect('static_pressure')}))

    def test_they_do_not_attach_outside_the_pressure_kinds(self, aspect):
        with pytest.raises(AspectNotApplicable):
            Number(1, parse_unit('N*m'), kind=active_kinds().get('torque'),
                   aspects=frozenset({aspect('static_pressure')}))


class TestAdditionMustLift:
    """The must-pass half, and the reason these are not kinds."""

    def test_bernoulli_sums_and_lifts_to_the_family_root(self, pressure, aspect):
        """*"Stagnation pressure: P0 = P + ½ρV²"* — a must-pass row.

        Kinds refuse addition across disjoint members, so declaring static and
        dynamic as kinds would make this refuse. As aspects on an ``lca``
        family the sum resolves to "some pressure, role unspecified", which is
        what a stagnation pressure is.
        """
        static = held(101325, units.pascal, pressure, aspect('static_pressure'))
        dynamic = held(1531, units.pascal, pressure, aspect('dynamic_pressure'))
        total = static + dynamic
        assert total.quantity == 102856
        assert {a.name for a in total.aspects} == {'pressure_role'}


class TestClusterSevenRemainingMustFails:
    """The two rows no unit and no kind could reach."""

    def test_dynamic_reported_as_static_refuses(self, pressure, aspect):
        """*"Report dynamic pressure (½ρV²) as static pressure without
        qualification."*"""
        value = held(1, units.pascal, pressure, aspect('dynamic_pressure'))
        with pytest.raises(AspectClaimRefused):
            value.to(units.pascal, kind='thermodynamic_pressure',
                     aspect='static_pressure')

    def test_atmospheric_equated_with_lithostatic_refuses(self, pressure, aspect):
        """*"Equate atmospheric pressure (1013 hPa) with lithostatic pressure
        (1013 hPa) as the same physical ..."*"""
        hpa = parse_unit('hPa')
        value = held(1013, hpa, pressure, aspect('atmospheric_pressure'))
        with pytest.raises(AspectClaimRefused):
            value.to(hpa, kind='thermodynamic_pressure',
                     aspect='lithostatic_pressure')


class TestClaimSemantics:
    def test_omitting_the_claim_carries_aspects_through(self, pressure, aspect):
        value = held(1, units.pascal, pressure, aspect('dynamic_pressure'))
        assert {a.name for a in value.to(units.pascal).aspects} == {'dynamic_pressure'}

    def test_restating_the_held_aspect_admits(self, pressure, aspect):
        value = held(1, units.pascal, pressure, aspect('dynamic_pressure'))
        result = value.to(units.pascal, kind='thermodynamic_pressure',
                          aspect='dynamic_pressure')
        assert {a.name for a in result.aspects} == {'dynamic_pressure'}

    def test_weakening_to_the_family_root_admits(self, pressure, aspect):
        """Deliberate forgetting: "some pressure, role unspecified"."""
        value = held(1, units.pascal, pressure, aspect('dynamic_pressure'))
        result = value.to(units.pascal, kind='thermodynamic_pressure',
                          aspect='pressure_role')
        assert {a.name for a in result.aspects} == {'pressure_role'}

    def test_strengthening_refuses(self, pressure, aspect):
        """An unspecified role may not be claimed as a particular one."""
        value = held(1, units.pascal, pressure, aspect('pressure_role'))
        with pytest.raises(AspectClaimRefused):
            value.to(units.pascal, kind='thermodynamic_pressure',
                     aspect='dynamic_pressure')

    def test_claim_stands_when_the_family_is_empty(self, pressure, aspect):
        """Nothing held in that family, so nothing is contradicted."""
        value = Number(1, units.pascal, kind=pressure)
        result = value.to(units.pascal, kind='thermodynamic_pressure',
                          aspect='static_pressure')
        assert {a.name for a in result.aspects} == {'static_pressure'}

    def test_resolution_is_family_wise(self, pressure, aspect):
        """A claim in one family leaves the other alone."""
        value = Number(1, units.pascal, kind=pressure, aspects=frozenset({
            aspect('dynamic_pressure'), aspect('atmospheric_pressure'),
        }))
        result = value.to(units.pascal, kind='thermodynamic_pressure',
                          aspect='pressure_role')
        assert {a.name for a in result.aspects} == {
            'pressure_role', 'atmospheric_pressure',
        }

    def test_an_aspect_object_and_its_name_behave_alike(self, pressure, aspect):
        value = Number(1, units.pascal, kind=pressure)
        by_name = value.to(units.pascal, kind='thermodynamic_pressure',
                           aspect='static_pressure')
        by_obj = value.to(units.pascal, kind='thermodynamic_pressure',
                          aspect=aspect('static_pressure'))
        assert by_name.aspects == by_obj.aspects

    def test_unknown_aspect_name_raises(self, pressure):
        """The forest's own ``AspectError`` propagates, naming the bad name."""
        value = Number(1, units.pascal, kind=pressure)
        with pytest.raises(AspectError):
            value.to(units.pascal, kind='thermodynamic_pressure',
                     aspect='no_such_aspect')

    def test_claiming_is_not_the_predicate_addition_applies(self, pressure, aspect):
        """The whole point, in one test.

        The same pair sums and refuses, depending on which question is asked.
        """
        static = held(1, units.pascal, pressure, aspect('static_pressure'))
        dynamic = held(1, units.pascal, pressure, aspect('dynamic_pressure'))

        assert {a.name for a in (static + dynamic).aspects} == {'pressure_role'}

        with pytest.raises(AspectClaimRefused):
            dynamic.to(units.pascal, kind='thermodynamic_pressure',
                       aspect='static_pressure')
