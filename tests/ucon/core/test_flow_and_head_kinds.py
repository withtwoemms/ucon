# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
"""Clearance vs blood flow, and hydraulic head vs distance (#344).

Two more of UnitSafe's unclustered `koq_mismatch` must-fails. Both are pairs of
quantities that share a unit and are not the same thing, and in both cases the
pair fails the add-test — a total clearance is the sum of *clearances*, never of
a clearance and a flow; a head and a distance do not sum at all — so they are
kinds rather than aspects.
"""

import pytest

from ucon import Number, parse_unit, units
from ucon.core.exceptions import KindClaimRefused
from ucon.system import active_kinds


@pytest.fixture
def kinds():
    return active_kinds()


class TestVolumetricFlowRate:
    """#344 — *"equate renal clearance with hepatic blood flow"*."""

    def test_the_family_is_declared(self, kinds):
        from ucon.kinds.types import JoinPolicy
        root = kinds.get('volumetric_flow_rate')
        assert root is not None and root.parent is None
        assert root.join_policy is JoinPolicy.REFUSE
        for name in ('clearance', 'blood_flow'):
            assert kinds.get(name).parent.name == 'volumetric_flow_rate'

    def test_clearance_equated_with_blood_flow_refuses(self, kinds):
        value = Number(120, parse_unit('mL/min'), kind=kinds.get('clearance'))
        with pytest.raises(KindClaimRefused):
            value.to(parse_unit('L/min'), kind='blood_flow')

    def test_it_refuses_in_both_directions(self, kinds):
        value = Number(1.5, parse_unit('L/min'), kind=kinds.get('blood_flow'))
        with pytest.raises(KindClaimRefused):
            value.to(parse_unit('mL/min'), kind='clearance')

    @pytest.mark.parametrize('value,src,dst,expected', [
        (1.5, 'L/min', 'mL/min', 1500.0),
        (120, 'mL/min', 'L/h', 7.2),
        (1.8, 'mL/s', 'mL/min', 108.0),
    ])
    def test_the_clearance_must_passes_stay_same_kind(
        self, kinds, value, src, dst, expected
    ):
        """Every clearance row in the benchmark is a unit conversion.

        Hepatic 1.5 L/min to mL/min, renal 120 mL/min to L/h, creatinine
        1.8 mL/s to mL/min — all must pass, and all are same-kind.
        """
        result = Number(value, parse_unit(src), kind=kinds.get('clearance')).to(
            parse_unit(dst), kind='clearance')
        assert result.kind.name == 'clearance'
        assert result.quantity == pytest.approx(expected)

    def test_gfr_is_deliberately_not_split_from_clearance(self, kinds):
        """The benchmark keys its GFR must-passes as ``clearance``.

        Declaring ``gfr`` as a sibling would refuse a claim the dataset makes,
        so that pair waits on the harness question rather than being guessed at
        here. Recorded as a test so the omission is visible as a decision.
        """
        from ucon.kinds.exceptions import KindNotFound
        with pytest.raises(KindNotFound):
            kinds.get('gfr')


class TestLengthValuedQuantities:
    """#344 — *"equate 10 meters of pump head with 10 meters of pipe length"*."""

    def test_the_family_is_declared(self, kinds):
        from ucon.kinds.types import JoinPolicy
        root = kinds.get('length_quantity')
        assert root is not None and root.parent is None
        assert root.join_policy is JoinPolicy.REFUSE
        for name in ('distance', 'hydraulic_head'):
            assert kinds.get(name).parent.name == 'length_quantity'

    def test_head_equated_with_distance_refuses(self, kinds):
        value = Number(10, units.meter, kind=kinds.get('hydraulic_head'))
        with pytest.raises(KindClaimRefused):
            value.to(units.meter, kind='distance')

    def test_it_refuses_in_both_directions(self, kinds):
        value = Number(10, units.meter, kind=kinds.get('distance'))
        with pytest.raises(KindClaimRefused):
            value.to(units.meter, kind='hydraulic_head')

    def test_head_converts_between_length_units(self, kinds):
        result = Number(10, units.meter, kind=kinds.get('hydraulic_head')).to(
            units.foot, kind='hydraulic_head')
        assert result.kind.name == 'hydraulic_head'
        assert result.quantity == pytest.approx(32.8083989, rel=1e-6)


class TestNothingIsAttached:
    """The units carry no ``default_kind``, and must not."""

    def test_a_bare_length_carries_no_kind(self):
        """Most lengths are plain distances; tagging ``meter`` would force a
        claim onto every one of them."""
        assert units.meter.default_kind is None
        result = Number(10, units.meter).to(units.foot)
        assert result.kind is None
        assert result.quantity == pytest.approx(32.8083989, rel=1e-6)

    def test_a_bare_flow_rate_carries_no_kind(self):
        value = Number(120, parse_unit('mL/min'))
        assert value.kind is None
        assert value.to(parse_unit('L/min')).quantity == pytest.approx(0.12)
