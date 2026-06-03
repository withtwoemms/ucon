# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Tests for the built-in kind lattice shipped in comprehensive.ucon.toml."""

import pytest

from ucon.kinds import JoinRefused, KindLattice
from ucon.system import active_kinds


@pytest.fixture
def lattice() -> KindLattice:
    return active_kinds()


class TestBuiltinKindsLoaded:
    """Verify the lattice boots with the expected 25 kinds."""

    def test_lattice_count(self, lattice: KindLattice) -> None:
        assert len(lattice) == 25

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
