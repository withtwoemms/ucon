# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
"""``Number.to(..., kind=)`` — the kind the caller claims the result is.

Covers #373. The cases here are drawn from UnitSafe's ``cluster_5_Nm`` and
``cluster_7_Pa_stress_energy_density``, which is the point of the parameter:
those clusters' errors live in the claim, not in the units, so no property
attached to a unit can reach them.
"""

import pytest

from ucon import Number, parse_unit, units
from ucon.core.exceptions import KindClaimRefused
from ucon.kinds.exceptions import KindNotFound
from ucon.system import active_kinds


@pytest.fixture
def kinds():
    return active_kinds()


@pytest.fixture
def newton_metre():
    return parse_unit('N*m')


class TestClaimIsOptional:
    """No claim means no change. Every existing call takes this path."""

    def test_omitting_the_claim_leaves_arrival_in_charge(self, newton_metre):
        assert str(Number(1, newton_metre).to(units.joule)) == '<1.0 J>'

    def test_the_two_rows_the_claim_exists_to_separate_are_identical(self):
        """Same operation, same result -- which is why tagging cannot work.

        ``0.5 MJ/m³ -> kPa`` is a must-pass (a modulus of resilience) and
        ``500 kJ/m³ -> kPa`` is a must-fail (energy density called a stress).
        Unclaimed, they are one conversion.
        """
        a = Number(0.5, parse_unit('MJ/m^3')).to(parse_unit('kPa'))
        b = Number(500, parse_unit('kJ/m^3')).to(parse_unit('kPa'))
        assert str(a) == str(b) == '<500.0 kPa>'


class TestClusterFiveTorqueEnergy:
    """#342 — 8 must-fails, all claiming across torque and energy."""

    def test_torque_claimed_as_energy_refuses(self, kinds, newton_metre):
        """*"A wrench applies 50 N·m of torque. Report this as the work done
        in joules."*"""
        with pytest.raises(KindClaimRefused):
            Number(50, newton_metre, kind=kinds.get('torque')).to(
                units.joule, kind='energy'
            )

    def test_energy_claimed_as_torque_also_refuses(self, kinds):
        """The reverse reading, *"the work done is 500 J, equate this ..."*.

        Narrowing is refused as well as widening, so the direction a problem
        is phrased in does not decide whether it is caught.
        """
        with pytest.raises(KindClaimRefused):
            Number(500, units.joule, kind=kinds.get('energy')).to(
                parse_unit('N*m'), kind='torque'
            )

    def test_torque_to_torque_admits(self, kinds, newton_metre):
        """*"Convert 100 N·m of torque to ft·lbf."* -- a must-pass."""
        result = Number(100, newton_metre, kind=kinds.get('torque')).to(
            parse_unit('ft*lbf'), kind='torque'
        )
        assert result.kind.name == 'torque'
        assert result.quantity == pytest.approx(73.7562149, rel=1e-6)

    def test_energy_to_energy_admits(self, kinds, newton_metre):
        """*"Convert seismic moment 1e18 N·m to dyn·cm."* -- a must-pass.

        The same unit as the torque rows, claimed as energy. This row is the
        counterexample to giving ``N·m`` a ``default_kind``: a tag would have
        to pick one of the two and would break whichever row it did not pick.
        """
        result = Number(1e18, newton_metre, kind=kinds.get('energy')).to(
            parse_unit('dyn*cm'), kind='energy'
        )
        assert result.kind.name == 'energy'


class TestClusterSevenPressureFamily:
    """#343 — the four must-fails that convert a unit to itself."""

    def test_stress_claimed_as_pressure_refuses_at_the_same_unit(self, kinds):
        """*"Convert 100 MPa tensile stress directly to 100 MPa hydrostatic
        pressure."*

        ``MPa -> MPa``. Source and target are the same unit, so this is
        unreachable by any catalog change.
        """
        mpa = parse_unit('MPa')
        with pytest.raises(KindClaimRefused):
            Number(100, mpa, kind=kinds.get('mechanical_stress')).to(
                mpa, kind='thermodynamic_pressure'
            )

    def test_stress_to_stress_admits(self, kinds):
        """*"Convert 250 MPa tensile stress to psi."* -- one of 27 must-passes."""
        result = Number(250, parse_unit('MPa'), kind=kinds.get('mechanical_stress')).to(
            parse_unit('psi'), kind='mechanical_stress'
        )
        assert result.kind.name == 'mechanical_stress'
        assert result.quantity == pytest.approx(36259.4344, rel=1e-6)

    def test_energy_density_claimed_as_pressure_refuses(self, kinds):
        """*"Equate the energy density of an EM field (1 J/m³) with a pressure
        of 1 Pa."*"""
        with pytest.raises(KindClaimRefused):
            Number(1, parse_unit('J/m^3'), kind=kinds.get('energy_density')).to(
                units.pascal, kind='thermodynamic_pressure'
            )

    def test_energy_density_claimed_as_stress_refuses(self, kinds):
        """*"Convert energy density of a compressed gas (500 kJ/m³) to a stress
        of 500 kPa."*"""
        with pytest.raises(KindClaimRefused):
            Number(500, parse_unit('kJ/m^3'), kind=kinds.get('energy_density')).to(
                parse_unit('kPa'), kind='mechanical_stress'
            )

    def test_energy_density_to_energy_density_admits(self, kinds):
        """*"The modulus of resilience is 0.5 MJ/m³. Express in kPa."*

        The must-pass half of the identical pair. Reporting an energy density
        in pressure units is ordinary practice; claiming it *is* a stress is
        the error.
        """
        result = Number(0.5, parse_unit('MJ/m^3'), kind=kinds.get('energy_density')).to(
            parse_unit('kPa'), kind='energy_density'
        )
        assert result.kind.name == 'energy_density'
        assert result.quantity == pytest.approx(500.0)


class TestClaimSemantics:
    """The gate's edges."""

    def test_claim_stands_when_there_is_no_current_kind(self, newton_metre):
        result = Number(1, newton_metre).to(units.joule, kind='torque')
        assert result.kind.name == 'torque'

    def test_claim_restating_the_current_kind_admits(self, kinds, newton_metre):
        result = Number(1, newton_metre, kind=kinds.get('torque')).to(
            parse_unit('ft*lbf'), kind='torque'
        )
        assert result.kind.name == 'torque'

    def test_a_kind_object_and_its_name_behave_alike(self, kinds, newton_metre):
        by_name = Number(1, newton_metre).to(units.joule, kind='torque')
        by_obj = Number(1, newton_metre).to(units.joule, kind=kinds.get('torque'))
        assert by_name.kind == by_obj.kind

    def test_unresolvable_claim_raises(self, newton_metre):
        with pytest.raises(KindNotFound):
            Number(1, newton_metre).to(units.joule, kind='no_such_kind')

    def test_claiming_is_not_the_predicate_addition_applies(self, kinds):
        """The claim gate is *not* ``+``'s join, and must not be.

        Join answers "what do these two yield together" and lifts to their
        ancestor under its policy. A claim asks "does the value support this
        assertion", which the lift does not answer -- a family can be freely
        summable and still have members that are not interchangeable.

        ``voltage`` is the witness: its root carries ``JoinPolicy.LCA``, so
        ``+`` admits its children and joins them at the root, while claiming
        one child for a value carrying the other is refused.
        """
        potential = kinds.get('electric_potential')
        emf = kinds.get('electromotive_force')

        total = Number(1, units.volt, kind=potential) + Number(1, units.volt, kind=emf)
        assert total.kind.name == 'voltage'

        with pytest.raises(KindClaimRefused):
            Number(1, units.volt, kind=potential).to(units.volt, kind='electromotive_force')

    def test_a_refusing_ancestor_still_refuses_the_weakening(self, kinds):
        """``energy`` declines to stand for ``torque`` -- the cluster-5 case.

        Weakening is admitted only where the ancestor's policy permits
        generalizing across its children. ``energy.join_policy`` is
        ``refuse``, so it does not.
        """
        with pytest.raises(KindClaimRefused):
            Number(1, parse_unit('N*m'), kind=kinds.get('torque')).to(
                units.joule, kind='energy'
            )

    def test_weakening_to_a_permitting_ancestor_admits(self, kinds):
        """``electric_potential`` may be reported as the generic ``voltage``.

        Deliberate forgetting: a weaker claim the value does support.
        """
        result = Number(1, units.volt, kind=kinds.get('electric_potential')).to(
            units.volt, kind='voltage'
        )
        assert result.kind.name == 'voltage'

    def test_strengthening_refuses(self, kinds):
        """A generic value may not be claimed as a particular.

        ``1 V`` carrying only ``voltage`` is not an electromotive force, and
        nothing measured which. Gating on join admitted this, because the lift
        of an ancestor with its own descendant is the descendant.
        """
        with pytest.raises(KindClaimRefused):
            Number(1, units.volt, kind=kinds.get('voltage')).to(
                units.volt, kind='electromotive_force'
            )

    def test_sibling_swap_refuses_under_a_permitting_root(self, kinds):
        """The other hole gating on join left open, in both directions.

        ``molar_entropy`` is the second ``LCA``-rooted family in the catalog.
        """
        jmol = parse_unit('J/(mol*K)')
        quantity = kinds.get('molar_entropy_quantity')
        capacity = kinds.get('molar_heat_capacity')
        with pytest.raises(KindClaimRefused):
            Number(1, jmol, kind=quantity).to(jmol, kind='molar_heat_capacity')
        with pytest.raises(KindClaimRefused):
            Number(1, jmol, kind=capacity).to(jmol, kind='molar_entropy_quantity')
