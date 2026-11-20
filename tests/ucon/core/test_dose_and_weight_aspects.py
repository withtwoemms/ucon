# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
"""Weight basis and administration route as aspects (#344).

Two more unclustered `koq_mismatch` must-fails. Both pairs share a unit *and*
share a quantity — what differs is an adjective, so they are aspects rather
than kinds.

The administration-route family is the clearer case of why: oral and
intravenous morphine equivalents genuinely **sum** into a total opioid burden,
which is the entire purpose of a morphine-equivalent dose. Kinds refuse
addition across disjoint members, so kind-ifying them would break that sum,
while an `lca` aspect family lifts it to "total dose, route unspecified" and
still refuses the relabel.
"""

import pytest

from ucon import Number, parse_unit, units
from ucon.aspects.exceptions import AspectClaimRefused
from ucon.conversion import get_default_graph
from ucon.system import active_kinds


@pytest.fixture
def kinds():
    return active_kinds()


@pytest.fixture
def aspect():
    return get_default_graph()._aspect_forest.get


class TestFamiliesAreDeclared:
    def test_the_carrier_kinds_exist(self, kinds):
        """The aspects need a kind to sit on; ``mass`` had none."""
        for name in ('body_mass', 'drug_dose'):
            assert kinds.get(name).dimension == units.kilogram.dimension

    @pytest.mark.parametrize('root,members', [
        ('body_weight_basis', ('ideal_body_weight', 'actual_body_weight')),
        ('administration_route', ('oral_route', 'intravenous_route')),
    ])
    def test_the_families_load_on_lca(self, aspect, root, members):
        from ucon.kinds.types import JoinPolicy
        assert aspect(root).join_policy is JoinPolicy.LCA
        for m in members:
            assert aspect(m).parent.name == root


class TestTheMustFails:
    def test_ideal_treated_as_actual_body_weight_refuses(self, kinds, aspect):
        """*"Treat ideal body weight (IBW) and actual body weight (ABW) as
        identical for dosing."*"""
        value = Number(70, units.kilogram, kind=kinds.get('body_mass'),
                       aspects=frozenset({aspect('ideal_body_weight')}))
        with pytest.raises(AspectClaimRefused):
            value.to(units.kilogram, kind='body_mass',
                     aspect='actual_body_weight')

    def test_oral_equated_with_intravenous_refuses(self, kinds, aspect):
        """*"Equate oral morphine equivalent dose with IV morphine equivalent
        dose as interchangeable."*"""
        mg = parse_unit('mg')
        value = Number(30, mg, kind=kinds.get('drug_dose'),
                       aspects=frozenset({aspect('oral_route')}))
        with pytest.raises(AspectClaimRefused):
            value.to(mg, kind='drug_dose', aspect='intravenous_route')


class TestAdditionStillLifts:
    """Why these are aspects: the pair sums."""

    def test_routes_sum_to_a_total_burden(self, kinds, aspect):
        mg = parse_unit('mg')
        oral = Number(30, mg, kind=kinds.get('drug_dose'),
                      aspects=frozenset({aspect('oral_route')}))
        iv = Number(10, mg, kind=kinds.get('drug_dose'),
                    aspects=frozenset({aspect('intravenous_route')}))
        total = oral + iv
        assert total.quantity == 40
        assert {a.name for a in total.aspects} == {'administration_route'}


class TestClaimSemantics:
    def test_same_route_conversion_admits(self, kinds, aspect):
        mg = parse_unit('mg')
        value = Number(30, mg, kind=kinds.get('drug_dose'),
                       aspects=frozenset({aspect('oral_route')}))
        result = value.to(parse_unit('g'), kind='drug_dose', aspect='oral_route')
        assert result.quantity == pytest.approx(0.03)
        assert {a.name for a in result.aspects} == {'oral_route'}

    def test_weakening_to_the_family_root_admits(self, kinds, aspect):
        value = Number(70, units.kilogram, kind=kinds.get('body_mass'),
                       aspects=frozenset({aspect('ideal_body_weight')}))
        result = value.to(units.kilogram, kind='body_mass',
                          aspect='body_weight_basis')
        assert {a.name for a in result.aspects} == {'body_weight_basis'}

    def test_a_bare_mass_is_untouched(self):
        """Nothing attaches these; most masses are neither a dose nor a body
        weight."""
        assert units.kilogram.default_kind is None
        result = Number(70, units.kilogram).to(units.pound)
        assert result.kind is None
        assert result.aspects == frozenset()
        assert result.quantity == pytest.approx(154.3235835, rel=1e-6)
