# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Tests for kind-aware arithmetic dispatch (v2.0 §4.3, §4.4, §4.9).

Pins the wiring between ``Number.__mul__``, ``__truediv__``, ``__add__``,
``__sub__`` and the active ``FormulaRegistry`` / ``KindLattice``.

Each test constructs its own ``Kind``, ``KindLattice``, ``KindFormula``,
and ``FormulaRegistry``; no dependency on pre-registered domain formulas.
"""

from __future__ import annotations

import warnings

import pytest

from ucon import KindMismatch, Number
from ucon.dimension import ENERGY, FORCE, LENGTH, MASS, NONE, POWER, TIME, VELOCITY
from ucon.formulas import FormulaRegistry, KindFormula
from ucon.formulas.exceptions import FormulaNotFound
from ucon.kinds import Kind, KindLattice, JoinPolicy
from ucon.kinds.exceptions import JoinRefused
from ucon.system import active_system, use
from ucon.units import joule, meter, newton, second, watt


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _energy_lattice():
    """Build a small energy-kind tree with LCA policy at the root."""
    energy = Kind("energy", dimension=ENERGY)
    ke = Kind("kinetic_energy", dimension=ENERGY, parent=energy)
    pe = Kind("potential_energy", dimension=ENERGY, parent=energy)
    lattice = KindLattice([energy, ke, pe])
    return lattice, energy, ke, pe


def _refuse_lattice():
    """Build a tree where the root refuses joins."""
    dose = Kind("dose", dimension=ENERGY, join_policy=JoinPolicy.REFUSE)
    absorbed = Kind("absorbed_dose", dimension=ENERGY, parent=dose)
    equivalent = Kind("equivalent_dose", dimension=ENERGY, parent=dose)
    lattice = KindLattice([dose, absorbed, equivalent])
    return lattice, dose, absorbed, equivalent


# ---------------------------------------------------------------------------
# Multiplication
# ---------------------------------------------------------------------------

class TestMulFormulaStampsKind:
    """__mul__: FormulaRegistry resolves output_kind when both operands
    carry a kind (§4.4, Q19)."""

    def test_mul_formula_stamps_kind(self) -> None:
        force_kind = Kind("force", dimension=FORCE)
        distance_kind = Kind("distance", dimension=LENGTH)
        work_kind = Kind("work", dimension=ENERGY)

        formula = KindFormula(
            name="work",
            expression="F * d",
            input_kinds={"F": force_kind, "d": distance_kind},
            output_kind=work_kind,
        )
        registry = FormulaRegistry([formula])
        lattice = KindLattice([force_kind, distance_kind, work_kind])
        sys = active_system()

        with use(sys, formulas=registry, kinds=lattice):
            f = Number(10, newton, kind=force_kind)
            d = Number(5, meter, kind=distance_kind)
            result = f * d
            assert result.kind is work_kind
            assert result.quantity == 50

    def test_mul_commutative_formula(self) -> None:
        """Commutative formula: d × F and F × d both resolve."""
        force_kind = Kind("force", dimension=FORCE)
        distance_kind = Kind("distance", dimension=LENGTH)
        work_kind = Kind("work", dimension=ENERGY)

        formula = KindFormula(
            name="work",
            expression="F * d",
            input_kinds={"F": force_kind, "d": distance_kind},
            output_kind=work_kind,
            commutative=True,
        )
        registry = FormulaRegistry([formula])
        lattice = KindLattice([force_kind, distance_kind, work_kind])
        sys = active_system()

        with use(sys, formulas=registry, kinds=lattice):
            f = Number(10, newton, kind=force_kind)
            d = Number(5, meter, kind=distance_kind)
            # Reverse order — should still resolve via commutative index.
            result = d * f
            assert result.kind is work_kind


class TestMulNoFormula:
    """__mul__: no formula match → kind=None."""

    def test_mul_no_formula_yields_none(self) -> None:
        kind_a = Kind("kind_a", dimension=FORCE)
        kind_b = Kind("kind_b", dimension=LENGTH)

        registry = FormulaRegistry()  # empty
        lattice = KindLattice([kind_a, kind_b])
        sys = active_system()

        with use(sys, formulas=registry, kinds=lattice):
            a = Number(10, newton, kind=kind_a)
            b = Number(5, meter, kind=kind_b)
            result = a * b
            assert result.kind is None


class TestMulUnkindedFastPath:
    """__mul__: Q19 fast path — one or both operands unkinded → kind=None,
    no registry consulted."""

    def test_mul_one_unkinded_yields_none(self) -> None:
        force_kind = Kind("force", dimension=FORCE)
        a = Number(10, newton, kind=force_kind)
        b = Number(5, meter)  # unkinded
        result = a * b
        assert result.kind is None

    def test_mul_both_unkinded_yields_none(self) -> None:
        a = Number(10, newton)
        b = Number(5, meter)
        result = a * b
        assert result.kind is None


class TestMulScalarPreservesKind:
    """__mul__: S1 — scalar multiplication preserves kind."""

    def test_mul_scalar_int_preserves_kind(self) -> None:
        ke = Kind("kinetic_energy", dimension=ENERGY)
        n = Number(100, joule, kind=ke)
        result = n * 3
        assert result.kind is ke
        assert result.quantity == 300

    def test_mul_scalar_float_preserves_kind(self) -> None:
        ke = Kind("kinetic_energy", dimension=ENERGY)
        n = Number(100, joule, kind=ke)
        result = n * 0.5
        assert result.kind is ke
        assert result.quantity == 50.0


# ---------------------------------------------------------------------------
# Division
# ---------------------------------------------------------------------------

class TestDivFormulaStampsKind:
    """__truediv__: FormulaRegistry resolves output_kind for dimensionful
    quotients."""

    def test_div_formula_stamps_kind(self) -> None:
        power_kind = Kind("power", dimension=POWER)
        velocity_kind = Kind("velocity", dimension=VELOCITY)
        force_kind = Kind("force_out", dimension=FORCE)

        formula = KindFormula(
            name="power_over_velocity",
            expression="P / v",
            input_kinds={"P": power_kind, "v": velocity_kind},
            output_kind=force_kind,
            commutative=False,
        )
        registry = FormulaRegistry([formula])
        lattice = KindLattice([power_kind, velocity_kind, force_kind])
        sys = active_system()

        with use(sys, formulas=registry, kinds=lattice):
            p = Number(100, watt, kind=power_kind)
            v = Number(10, meter / second, kind=velocity_kind)
            result = p / v
            assert result.kind is force_kind

    def test_div_no_formula_yields_none(self) -> None:
        kind_a = Kind("kind_a", dimension=FORCE)
        kind_b = Kind("kind_b", dimension=LENGTH)

        registry = FormulaRegistry()  # empty
        lattice = KindLattice([kind_a, kind_b])
        sys = active_system()

        with use(sys, formulas=registry, kinds=lattice):
            a = Number(10, newton, kind=kind_a)
            b = Number(5, meter, kind=kind_b)
            result = a / b
            assert result.kind is None


class TestDivDimensionlessYieldsNone:
    """__truediv__: S2 — same-unit division yields kind=None (dimensionless)."""

    def test_div_dimensionless_yields_none(self) -> None:
        ke = Kind("kinetic_energy", dimension=ENERGY)
        a = Number(100, joule, kind=ke)
        b = Number(50, joule, kind=ke)
        result = a / b
        assert result.kind is None
        assert result.quantity == 2.0


class TestDivScalarPreservesKind:
    """__truediv__: S1 — scalar division preserves kind."""

    def test_div_scalar_preserves_kind(self) -> None:
        ke = Kind("kinetic_energy", dimension=ENERGY)
        n = Number(100, joule, kind=ke)
        result = n / 2
        assert result.kind is ke
        assert result.quantity == 50.0


# ---------------------------------------------------------------------------
# Addition
# ---------------------------------------------------------------------------

class TestAddSameKindPreserves:
    """__add__: same kind → result carries that kind."""

    def test_add_same_kind_preserves(self) -> None:
        ke = Kind("kinetic_energy", dimension=ENERGY)
        lattice = KindLattice([ke])
        sys = active_system()

        with use(sys, kinds=lattice):
            a = Number(100, joule, kind=ke)
            b = Number(200, joule, kind=ke)
            result = a + b
            assert result.kind is ke
            assert result.quantity == 300


class TestAddLCAJoin:
    """__add__: different kinds with LCA parent → result is the LCA."""

    def test_add_lca_join(self) -> None:
        lattice, energy, ke, pe = _energy_lattice()
        sys = active_system()

        with use(sys, kinds=lattice):
            a = Number(100, joule, kind=ke)
            b = Number(200, joule, kind=pe)
            result = a + b
            assert result.kind == energy
            assert result.kind.name == "energy"


class TestAddJoinRefused:
    """__add__: kinds under a REFUSE parent → JoinRefused."""

    def test_add_join_refused(self) -> None:
        lattice, dose, absorbed, equivalent = _refuse_lattice()
        sys = active_system()

        with use(sys, kinds=lattice):
            a = Number(100, joule, kind=absorbed)
            b = Number(200, joule, kind=equivalent)
            with pytest.raises(JoinRefused):
                a + b


class TestAddKindedUnkindedStrict:
    """__add__: kinded + unkinded under strict=True → KindMismatch."""

    def test_add_kinded_left_unkinded_right_raises(self) -> None:
        ke = Kind("kinetic_energy", dimension=ENERGY)
        sys = active_system()

        with use(sys, strict=True):
            a = Number(100, joule, kind=ke)
            b = Number(200, joule)
            with pytest.raises(KindMismatch) as exc_info:
                a + b
            exc = exc_info.value
            assert exc.kinded is ke
            assert exc.unkinded_side == "right"

    def test_add_unkinded_left_kinded_right_raises(self) -> None:
        ke = Kind("kinetic_energy", dimension=ENERGY)
        sys = active_system()

        with use(sys, strict=True):
            a = Number(100, joule)
            b = Number(200, joule, kind=ke)
            with pytest.raises(KindMismatch) as exc_info:
                a + b
            exc = exc_info.value
            assert exc.kinded is ke
            assert exc.unkinded_side == "left"


class TestAddKindedUnkindedPermissive:
    """__add__: kinded + unkinded under strict=False → warns, inherits kind."""

    def test_add_kinded_unkinded_permissive_warns(self) -> None:
        ke = Kind("kinetic_energy", dimension=ENERGY)
        sys = active_system()

        with use(sys, strict=False):
            a = Number(100, joule, kind=ke)
            b = Number(200, joule)
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                result = a + b
            assert result.kind is ke
            assert result.quantity == 300
            assert len(w) == 1
            assert "kinetic_energy" in str(w[0].message)


class TestAddBothUnkinded:
    """__add__: both unkinded → no kind logic, kind=None."""

    def test_add_both_unkinded_succeeds(self) -> None:
        a = Number(100, joule)
        b = Number(200, joule)
        result = a + b
        assert result.kind is None
        assert result.quantity == 300


# ---------------------------------------------------------------------------
# Subtraction
# ---------------------------------------------------------------------------

class TestSubSameKindPreserves:
    """__sub__: same kind → result carries that kind."""

    def test_sub_same_kind_preserves(self) -> None:
        ke = Kind("kinetic_energy", dimension=ENERGY)
        lattice = KindLattice([ke])
        sys = active_system()

        with use(sys, kinds=lattice):
            a = Number(300, joule, kind=ke)
            b = Number(100, joule, kind=ke)
            result = a - b
            assert result.kind is ke
            assert result.quantity == 200


class TestSubJoinRefused:
    """__sub__: REFUSE policy → JoinRefused."""

    def test_sub_join_refused(self) -> None:
        lattice, dose, absorbed, equivalent = _refuse_lattice()
        sys = active_system()

        with use(sys, kinds=lattice):
            a = Number(300, joule, kind=absorbed)
            b = Number(100, joule, kind=equivalent)
            with pytest.raises(JoinRefused):
                a - b


class TestSubLCAJoin:
    """__sub__: different kinds with LCA parent → result is the LCA."""

    def test_sub_lca_join(self) -> None:
        lattice, energy, ke, pe = _energy_lattice()
        sys = active_system()

        with use(sys, kinds=lattice):
            a = Number(300, joule, kind=ke)
            b = Number(100, joule, kind=pe)
            result = a - b
            assert result.kind == energy
            assert result.kind.name == "energy"
