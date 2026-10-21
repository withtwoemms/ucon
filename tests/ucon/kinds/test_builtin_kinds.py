# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Tests for the built-in kind lattice shipped in comprehensive.ucon.toml."""

import pytest

from ucon import ConversionNotFound, DimensionMismatch, Number
from ucon.dimension import ANGLE, SOLID_ANGLE
from ucon.kinds import DisjointKinds, JoinPolicy, JoinRefused, KindLattice
from ucon.system import active_kinds
from ucon.units import (
    arcminute,
    arcsecond,
    degree,
    gradian,
    hertz,
    meter,
    radian,
    second,
    square_degree,
    steradian,
    turn,
    watt,
)


@pytest.fixture
def lattice() -> KindLattice:
    return active_kinds()


class TestBuiltinKindsLoaded:
    """Verify the lattice boots with the expected 29 kinds."""

    def test_lattice_count(self, lattice: KindLattice) -> None:
        assert len(lattice) == 29  # + plane_angle, solid_angle (#348)

    def test_all_root_kinds_present(self, lattice: KindLattice) -> None:
        roots = ["energy", "frequency", "specific_energy", "voltage",
                 "molar_energy", "molar_entropy", "power", "pressure"]
        for name in roots:
            assert name in lattice, f"Root kind {name!r} missing"

    def test_all_leaf_kinds_present(self, lattice: KindLattice) -> None:
        leaves = [
            "torque",
            "radioactive_activity",
            "absorbed_dose", "dose_equivalent",
            "electric_potential", "electromotive_force",
            "enthalpy", "gibbs_energy", "helmholtz_energy", "chemical_potential",
            "molar_entropy_quantity", "molar_heat_capacity",
            "real_power", "apparent_power", "reactive_power",
            "thermodynamic_pressure", "mechanical_stress",
        ]
        for name in leaves:
            assert name in lattice, f"Leaf kind {name!r} missing"


class TestBuiltinAliases:
    """Verify kind aliases resolve correctly."""

    def test_emf_alias(self, lattice: KindLattice) -> None:
        assert lattice.get("emf").name == "electromotive_force"

    def test_delta_H_alias(self, lattice: KindLattice) -> None:
        assert lattice.get("delta_H").name == "enthalpy"

    def test_delta_G_alias(self, lattice: KindLattice) -> None:
        assert lattice.get("delta_G").name == "gibbs_energy"

    def test_delta_A_alias(self, lattice: KindLattice) -> None:
        assert lattice.get("delta_A").name == "helmholtz_energy"

    def test_mu_chem_alias(self, lattice: KindLattice) -> None:
        assert lattice.get("mu_chem").name == "chemical_potential"


class TestRefuseClusters:
    """Sibling kinds under REFUSE roots must raise JoinRefused."""

    @pytest.mark.parametrize("a,b", [
        ("torque", "energy"),
        ("radioactive_activity", "frequency"),
        ("absorbed_dose", "dose_equivalent"),
        ("enthalpy", "gibbs_energy"),
        ("enthalpy", "chemical_potential"),
        ("gibbs_energy", "helmholtz_energy"),
        ("real_power", "apparent_power"),
        ("real_power", "reactive_power"),
        ("apparent_power", "reactive_power"),
        ("thermodynamic_pressure", "mechanical_stress"),
    ])
    def test_refuse_join(self, lattice: KindLattice, a: str, b: str) -> None:
        with pytest.raises(JoinRefused):
            lattice.join(lattice.get(a), lattice.get(b))


class TestLCAClusters:
    """Sibling kinds under LCA roots lift to the common ancestor."""

    def test_voltage_lca(self, lattice: KindLattice) -> None:
        result = lattice.join(
            lattice.get("electric_potential"),
            lattice.get("electromotive_force"),
        )
        assert result.name == "voltage"

    def test_molar_entropy_lca(self, lattice: KindLattice) -> None:
        result = lattice.join(
            lattice.get("molar_entropy_quantity"),
            lattice.get("molar_heat_capacity"),
        )
        assert result.name == "molar_entropy"


class TestKindDimensions:
    """Verify each kind references the correct named dimension."""

    @pytest.mark.parametrize("kind_name,dim_name", [
        ("energy", "energy"),
        ("torque", "energy"),
        ("frequency", "frequency"),
        ("radioactive_activity", "frequency"),
        ("specific_energy", "specific_energy"),
        ("absorbed_dose", "specific_energy"),
        ("dose_equivalent", "specific_energy"),
        ("voltage", "voltage"),
        ("molar_energy", "molar_energy"),
        ("enthalpy", "molar_energy"),
        ("molar_entropy", "molar_entropy"),
        ("molar_heat_capacity", "molar_entropy"),
        ("power", "power"),
        ("real_power", "power"),
        ("pressure", "pressure"),
        ("mechanical_stress", "pressure"),
    ])
    def test_kind_dimension(self, lattice: KindLattice, kind_name: str, dim_name: str) -> None:
        kind = lattice.get(kind_name)
        assert kind.dimension.name == dim_name


class TestParentEdges:
    """Verify parent relationships are correctly wired."""

    @pytest.mark.parametrize("child,parent", [
        ("torque", "energy"),
        ("radioactive_activity", "frequency"),
        ("absorbed_dose", "specific_energy"),
        ("dose_equivalent", "specific_energy"),
        ("electric_potential", "voltage"),
        ("electromotive_force", "voltage"),
        ("enthalpy", "molar_energy"),
        ("gibbs_energy", "molar_energy"),
        ("helmholtz_energy", "molar_energy"),
        ("chemical_potential", "molar_energy"),
        ("molar_entropy_quantity", "molar_entropy"),
        ("molar_heat_capacity", "molar_entropy"),
        ("real_power", "power"),
        ("apparent_power", "power"),
        ("reactive_power", "power"),
        ("thermodynamic_pressure", "pressure"),
        ("mechanical_stress", "pressure"),
    ])
    def test_parent_edge(self, lattice: KindLattice, child: str, parent: str) -> None:
        kind = lattice.get(child)
        assert kind.parent is not None
        assert kind.parent.name == parent

    @pytest.mark.parametrize("root", [
        "energy", "frequency", "specific_energy", "voltage",
        "molar_energy", "molar_entropy", "power", "pressure",
    ])
    def test_root_has_no_parent(self, lattice: KindLattice, root: str) -> None:
        kind = lattice.get(root)
        assert kind.parent is None


PLANE_ANGLE_UNITS = (radian, degree, gradian, turn, arcminute, arcsecond)
SOLID_ANGLE_UNITS = (steradian, square_degree)


class TestAngleKinds:
    """The angle KOQ floor (#348): declared kinds, carried by the units.

    These kinds are forward-looking insurance. ADR 013 dissolves the
    ``angle`` and ``solid_angle`` pseudo-dimension tags at 3.0.0, after
    which ``rad -> sr`` has nothing dimensional left to refuse on. The
    kinds must exist, and the units must carry them, *before* the tags go.
    """

    def test_plane_angle_declared(self, lattice: KindLattice) -> None:
        assert "plane_angle" in lattice
        assert lattice.get("plane_angle").dimension == ANGLE

    def test_solid_angle_declared(self, lattice: KindLattice) -> None:
        assert "solid_angle" in lattice
        assert lattice.get("solid_angle").dimension == SOLID_ANGLE

    @pytest.mark.parametrize("name", ["plane_angle", "solid_angle"])
    def test_angle_kinds_are_independent_roots(
        self, lattice: KindLattice, name: str
    ) -> None:
        """Neither hangs off a shared root.

        A shared root is not expressible: the two kinds have different
        dimensions, and a cross-dimension parent edge raises
        ``CrossDimensionParent``. ``sr = rad^2`` is a power relation, not
        a subtype relation, so no parent edge would capture it anyway.
        """
        assert lattice.get(name).parent is None

    @pytest.mark.parametrize("name", ["plane_angle", "solid_angle"])
    def test_angle_roots_refuse(self, lattice: KindLattice, name: str) -> None:
        assert lattice.get(name).join_policy is JoinPolicy.REFUSE

    def test_plane_and_solid_angle_do_not_join(self, lattice: KindLattice) -> None:
        """Disjoint roots, so joining is DisjointKinds, not JoinRefused."""
        with pytest.raises(DisjointKinds):
            lattice.join(lattice.get("plane_angle"), lattice.get("solid_angle"))

    @pytest.mark.parametrize("unit", PLANE_ANGLE_UNITS, ids=lambda u: u.name)
    def test_plane_angle_units_declare_kind(self, unit) -> None:
        assert unit.default_kind == "plane_angle"

    @pytest.mark.parametrize("unit", SOLID_ANGLE_UNITS, ids=lambda u: u.name)
    def test_solid_angle_units_declare_kind(self, unit) -> None:
        assert unit.default_kind == "solid_angle"

    @pytest.mark.parametrize("unit", PLANE_ANGLE_UNITS, ids=lambda u: u.name)
    def test_plane_angle_attaches_at_construction(
        self, lattice: KindLattice, unit
    ) -> None:
        assert Number(1, unit).kind == lattice.get("plane_angle")

    @pytest.mark.parametrize("unit", SOLID_ANGLE_UNITS, ids=lambda u: u.name)
    def test_solid_angle_attaches_at_construction(
        self, lattice: KindLattice, unit
    ) -> None:
        assert Number(1, unit).kind == lattice.get("solid_angle")


class TestAngleKindsChangeNoBehaviour:
    """The kinds add no gate today. Every refusal keeps its current reason.

    ``xdom-018``, ``xdom-020`` and ``pr-028`` are UnitSafe must-fails. Each
    must keep refusing, and keep refusing for the same reason it refuses
    without the kinds, so that declaring them is observably inert.
    """

    def test_xdom_018_radian_to_steradian_still_dimension_mismatch(self) -> None:
        with pytest.raises(DimensionMismatch):
            Number(1, radian).to(steradian)

    def test_xdom_020_radian_per_second_to_hertz_still_not_found(self) -> None:
        with pytest.raises(ConversionNotFound):
            Number(1, radian / second).to(hertz)

    def test_pr_028_irradiance_to_radiance_still_dimension_mismatch(self) -> None:
        with pytest.raises(DimensionMismatch):
            Number(1, watt / meter ** 2).to(watt / steradian)

    def test_degree_to_radian_still_converts(self) -> None:
        assert Number(1, degree).to(radian).value == pytest.approx(
            0.017453292519943295
        )

    def test_square_degree_to_steradian_keeps_squared_factor(self) -> None:
        """The only surviving trace of ``sr = rad^2``: a hand-squared edge."""
        assert Number(1, square_degree).to(steradian).value == pytest.approx(
            0.00030461741978670857
        )

    def test_kinds_do_not_propagate_into_unit_products(self) -> None:
        """``rad/s`` carries no kind, so ``xdom-020`` is not yet insured.

        ``default_kind`` attaches on atomic units only. Protecting
        ``xdom-020`` past the retirement needs ``default_kind`` on product
        signatures (#342, #343), which is not this change.
        """
        assert Number(1, radian / second).kind is None
        assert Number(1, watt / steradian).kind is None
