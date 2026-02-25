# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Tests for standard bases and transforms."""

from fractions import Fraction

import pytest

from ucon.bases import (
    CGS,
    CGS_ESU,
    CGS_TO_SI,
    SI,
    SI_TO_CGS,
    SI_TO_CGS_ESU,
)
from ucon.basis import LossyProjection, Vector


# -----------------------------------------------------------------------------
# Standard Bases Tests
# -----------------------------------------------------------------------------


class TestSIBasis:
    """Tests for SI basis."""

    def test_si_has_8_components(self):
        """GIVEN SI basis, THEN it has 8 components."""
        assert len(SI) == 8

    def test_si_component_names(self):
        """GIVEN SI basis, THEN components have correct names."""
        assert SI.component_names == (
            "time",
            "length",
            "mass",
            "current",
            "temperature",
            "luminous_intensity",
            "amount_of_substance",
            "information",
        )

    def test_si_component_symbols(self):
        """GIVEN SI basis, THEN components have correct symbols."""
        assert "T" in SI
        assert "L" in SI
        assert "M" in SI
        assert "I" in SI
        assert "Θ" in SI
        assert "J" in SI
        assert "N" in SI
        assert "B" in SI

    def test_si_index_by_name_and_symbol(self):
        """GIVEN SI basis, THEN index works by name and symbol."""
        assert SI.index("time") == 0
        assert SI.index("T") == 0
        assert SI.index("length") == 1
        assert SI.index("L") == 1
        assert SI.index("current") == 3
        assert SI.index("I") == 3


class TestCGSBasis:
    """Tests for CGS basis."""

    def test_cgs_has_3_components(self):
        """GIVEN CGS basis, THEN it has 3 components."""
        assert len(CGS) == 3

    def test_cgs_component_names(self):
        """GIVEN CGS basis, THEN components have correct names."""
        assert CGS.component_names == ("length", "mass", "time")


class TestCGSESUBasis:
    """Tests for CGS-ESU basis."""

    def test_cgs_esu_has_4_components(self):
        """GIVEN CGS-ESU basis, THEN it has 4 components."""
        assert len(CGS_ESU) == 4

    def test_cgs_esu_component_names(self):
        """GIVEN CGS-ESU basis, THEN components have correct names."""
        assert CGS_ESU.component_names == ("length", "mass", "time", "charge")

    def test_cgs_esu_charge_symbol(self):
        """GIVEN CGS-ESU basis, THEN charge has symbol Q."""
        assert "Q" in CGS_ESU
        assert CGS_ESU.index("Q") == 3


# -----------------------------------------------------------------------------
# SI to CGS Transform Tests
# -----------------------------------------------------------------------------


class TestSIToCGS:
    """Tests for SI -> CGS transform."""

    def test_transform_pure_mechanical(self):
        """GIVEN a pure mechanical dimension, THEN it transforms cleanly."""
        # Velocity: L T^-1
        # SI order: T, L, M, I, Θ, J, N, B
        si_velocity = Vector(
            SI,
            (
                Fraction(-1),  # T
                Fraction(1),   # L
                Fraction(0),   # M
                Fraction(0),   # I
                Fraction(0),   # Θ
                Fraction(0),   # J
                Fraction(0),   # N
                Fraction(0),   # B
            ),
        )
        cgs_velocity = SI_TO_CGS(si_velocity)

        assert cgs_velocity.basis == CGS
        assert cgs_velocity["L"] == Fraction(1)
        assert cgs_velocity["T"] == Fraction(-1)

    def test_transform_current_raises_lossy(self):
        """GIVEN current dimension, THEN LossyProjection is raised."""
        # SI order: T, L, M, I, Θ, J, N, B
        si_current = Vector(
            SI,
            (
                Fraction(0),   # T
                Fraction(0),   # L
                Fraction(0),   # M
                Fraction(1),   # I = 1
                Fraction(0),   # Θ
                Fraction(0),   # J
                Fraction(0),   # N
                Fraction(0),   # B
            ),
        )
        with pytest.raises(LossyProjection) as exc_info:
            SI_TO_CGS(si_current)

        assert exc_info.value.component.name == "current"
        assert exc_info.value.source == SI
        assert exc_info.value.target == CGS

    def test_transform_current_with_allow_projection(self):
        """GIVEN current dimension with allow_projection=True, THEN it projects to zero."""
        # SI order: T, L, M, I, Θ, J, N, B
        si_current = Vector(
            SI,
            (
                Fraction(0),   # T
                Fraction(0),   # L
                Fraction(0),   # M
                Fraction(1),   # I = 1
                Fraction(0),   # Θ
                Fraction(0),   # J
                Fraction(0),   # N
                Fraction(0),   # B
            ),
        )
        cgs_result = SI_TO_CGS(si_current, allow_projection=True)

        assert cgs_result.is_dimensionless()


# -----------------------------------------------------------------------------
# SI to CGS-ESU Transform Tests
# -----------------------------------------------------------------------------


class TestSIToCGSESU:
    """Tests for SI -> CGS-ESU transform."""

    def test_transform_current_to_derived(self):
        """GIVEN SI current, THEN it transforms to derived dimension L^(3/2) M^(1/2) T^(-2)."""
        # SI order: T, L, M, I, Θ, J, N, B
        si_current = Vector(
            SI,
            (
                Fraction(0),   # T
                Fraction(0),   # L
                Fraction(0),   # M
                Fraction(1),   # I = 1
                Fraction(0),   # Θ
                Fraction(0),   # J
                Fraction(0),   # N
                Fraction(0),   # B
            ),
        )
        esu_current = SI_TO_CGS_ESU(si_current)

        assert esu_current.basis == CGS_ESU
        assert esu_current["L"] == Fraction(3, 2)
        assert esu_current["M"] == Fraction(1, 2)
        assert esu_current["T"] == Fraction(-2)
        assert esu_current["Q"] == Fraction(0)

    def test_transform_voltage(self):
        """GIVEN SI voltage (M L^2 T^-3 I^-1), THEN it transforms correctly."""
        # Voltage: M L^2 T^-3 I^-1
        # SI order: T, L, M, I, Θ, J, N, B
        si_voltage = Vector(
            SI,
            (
                Fraction(-3),  # T^-3
                Fraction(2),   # L^2
                Fraction(1),   # M
                Fraction(-1),  # I^-1
                Fraction(0),   # Θ
                Fraction(0),   # J
                Fraction(0),   # N
                Fraction(0),   # B
            ),
        )
        esu_voltage = SI_TO_CGS_ESU(si_voltage)

        # I^-1 contributes: -1 * (3/2, 1/2, -2, 0) = (-3/2, -1/2, 2, 0)
        # Total: L^2 + (-3/2) = 1/2, M + (-1/2) = 1/2, T^-3 + 2 = -1
        assert esu_voltage["L"] == Fraction(1, 2)
        assert esu_voltage["M"] == Fraction(1, 2)
        assert esu_voltage["T"] == Fraction(-1)


# -----------------------------------------------------------------------------
# Embedding Tests
# -----------------------------------------------------------------------------


class TestEmbeddings:
    """Tests for embedding transforms."""

    def test_cgs_to_si_embedding(self):
        """GIVEN CGS velocity, THEN embedding to SI preserves mechanical components."""
        # CGS order: L, M, T
        cgs_velocity = Vector(
            CGS,
            (Fraction(1), Fraction(0), Fraction(-1)),  # L=1, M=0, T=-1
        )
        si_velocity = CGS_TO_SI(cgs_velocity)

        assert si_velocity.basis == SI
        assert si_velocity["T"] == Fraction(-1)
        assert si_velocity["L"] == Fraction(1)
        assert si_velocity["M"] == Fraction(0)
        # Other components are zero
        assert si_velocity["I"] == Fraction(0)
        assert si_velocity["Θ"] == Fraction(0)

    def test_round_trip_mechanical(self):
        """GIVEN SI mechanical dimension, THEN SI -> CGS -> SI round trip preserves it."""
        # Energy: M L^2 T^-2
        # SI order: T, L, M, I, Θ, J, N, B
        si_energy = Vector(
            SI,
            (
                Fraction(-2),  # T^-2
                Fraction(2),   # L^2
                Fraction(1),   # M
                Fraction(0),   # I
                Fraction(0),   # Θ
                Fraction(0),   # J
                Fraction(0),   # N
                Fraction(0),   # B
            ),
        )
        cgs_energy = SI_TO_CGS(si_energy)
        si_recovered = CGS_TO_SI(cgs_energy)

        assert si_recovered == si_energy

