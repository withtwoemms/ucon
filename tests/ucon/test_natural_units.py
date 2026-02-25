# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Tests for natural units support (v0.9.3).

Natural units set c = h_bar = k_B = 1, collapsing length, time, mass, and
temperature into expressions of a single energy dimension.
"""

from fractions import Fraction

import pytest

from ucon.basis import (
    BasisComponent,
    ConstantAwareBasisTransform,
    ConstantBinding,
    LossyProjection,
    Vector,
)
from ucon.bases import (
    NATURAL,
    NATURAL_TO_SI,
    SI,
    SI_TO_NATURAL,
)


# -----------------------------------------------------------------------------
# NATURAL Basis Structure Tests
# -----------------------------------------------------------------------------


class TestNaturalBasis:
    """Tests for the NATURAL basis structure."""

    def test_has_single_component(self):
        """GIVEN NATURAL basis, THEN it has exactly 1 component (energy)."""
        assert len(NATURAL) == 1

    def test_component_is_energy(self):
        """GIVEN NATURAL basis, THEN its component is named 'energy'."""
        assert NATURAL[0].name == "energy"
        assert NATURAL[0].symbol == "E"

    def test_energy_in_basis(self):
        """GIVEN NATURAL basis, THEN 'energy' and 'E' are in the basis."""
        assert "energy" in NATURAL
        assert "E" in NATURAL

    def test_basis_name(self):
        """GIVEN NATURAL basis, THEN its name is 'natural'."""
        assert NATURAL.name == "natural"


# -----------------------------------------------------------------------------
# ConstantBinding Tests
# -----------------------------------------------------------------------------


class TestConstantBinding:
    """Tests for ConstantBinding dataclass."""

    def test_frozen_immutable(self):
        """GIVEN a ConstantBinding, THEN it cannot be mutated."""
        binding = ConstantBinding(
            source_component=BasisComponent("length", "L"),
            target_expression=Vector(NATURAL, (Fraction(-1),)),
            constant_symbol="c",
            exponent=Fraction(1),
        )
        with pytest.raises(AttributeError):
            binding.constant_symbol = "h"

    def test_hashable(self):
        """GIVEN a ConstantBinding, THEN it is hashable for dict/set usage."""
        binding = ConstantBinding(
            source_component=BasisComponent("length", "L"),
            target_expression=Vector(NATURAL, (Fraction(-1),)),
            constant_symbol="c",
            exponent=Fraction(1),
        )
        d = {binding: "value"}
        assert d[binding] == "value"

    def test_default_exponent(self):
        """GIVEN a ConstantBinding without exponent, THEN default is 1."""
        binding = ConstantBinding(
            source_component=BasisComponent("length", "L"),
            target_expression=Vector(NATURAL, (Fraction(-1),)),
            constant_symbol="c",
        )
        assert binding.exponent == Fraction(1)

    def test_fractional_exponent(self):
        """GIVEN a ConstantBinding with fractional exponent, THEN it is stored."""
        binding = ConstantBinding(
            source_component=BasisComponent("current", "I"),
            target_expression=Vector(NATURAL, (Fraction(1),)),
            constant_symbol="e",
            exponent=Fraction(1, 2),
        )
        assert binding.exponent == Fraction(1, 2)


# -----------------------------------------------------------------------------
# SI_TO_NATURAL Transform Tests
# -----------------------------------------------------------------------------


class TestSIToNatural:
    """Tests for SI_TO_NATURAL transform."""

    def test_is_constant_aware_transform(self):
        """GIVEN SI_TO_NATURAL, THEN it is a ConstantAwareBasisTransform."""
        assert isinstance(SI_TO_NATURAL, ConstantAwareBasisTransform)

    def test_source_is_si(self):
        """GIVEN SI_TO_NATURAL, THEN source is SI basis."""
        assert SI_TO_NATURAL.source == SI

    def test_target_is_natural(self):
        """GIVEN SI_TO_NATURAL, THEN target is NATURAL basis."""
        assert SI_TO_NATURAL.target == NATURAL

    def test_has_bindings(self):
        """GIVEN SI_TO_NATURAL, THEN it has constant bindings."""
        assert len(SI_TO_NATURAL.bindings) == 4  # L, T, M, Θ

    def test_length_to_inverse_energy(self):
        """GIVEN length dimension, THEN it transforms to E⁻¹."""
        # SI: T=0, L=1, M=0, I=0, Θ=0, J=0, N=0, B=0
        si_length = Vector(
            SI,
            (Fraction(0), Fraction(1), Fraction(0), Fraction(0),
             Fraction(0), Fraction(0), Fraction(0), Fraction(0)),
        )
        natural_result = SI_TO_NATURAL(si_length)

        assert natural_result.basis == NATURAL
        assert natural_result["E"] == Fraction(-1)

    def test_time_to_inverse_energy(self):
        """GIVEN time dimension, THEN it transforms to E⁻¹."""
        # SI: T=1, L=0, M=0, I=0, Θ=0, J=0, N=0, B=0
        si_time = Vector(
            SI,
            (Fraction(1), Fraction(0), Fraction(0), Fraction(0),
             Fraction(0), Fraction(0), Fraction(0), Fraction(0)),
        )
        natural_result = SI_TO_NATURAL(si_time)

        assert natural_result["E"] == Fraction(-1)

    def test_mass_to_energy(self):
        """GIVEN mass dimension, THEN it transforms to E."""
        # SI: T=0, L=0, M=1, I=0, Θ=0, J=0, N=0, B=0
        si_mass = Vector(
            SI,
            (Fraction(0), Fraction(0), Fraction(1), Fraction(0),
             Fraction(0), Fraction(0), Fraction(0), Fraction(0)),
        )
        natural_result = SI_TO_NATURAL(si_mass)

        assert natural_result["E"] == Fraction(1)

    def test_temperature_to_energy(self):
        """GIVEN temperature dimension, THEN it transforms to E."""
        # SI: T=0, L=0, M=0, I=0, Θ=1, J=0, N=0, B=0
        si_temp = Vector(
            SI,
            (Fraction(0), Fraction(0), Fraction(0), Fraction(0),
             Fraction(1), Fraction(0), Fraction(0), Fraction(0)),
        )
        natural_result = SI_TO_NATURAL(si_temp)

        assert natural_result["E"] == Fraction(1)

    def test_velocity_is_dimensionless(self):
        """GIVEN velocity (L/T), THEN it transforms to E⁰ (dimensionless).

        This is the key consequence of c = 1: velocity is dimensionless.
        """
        # Velocity: L¹T⁻¹
        # SI: T=-1, L=1, M=0, I=0, Θ=0, J=0, N=0, B=0
        si_velocity = Vector(
            SI,
            (Fraction(-1), Fraction(1), Fraction(0), Fraction(0),
             Fraction(0), Fraction(0), Fraction(0), Fraction(0)),
        )
        natural_result = SI_TO_NATURAL(si_velocity)

        # L → E⁻¹, T⁻¹ → E¹, so L¹T⁻¹ → E⁻¹·E¹ = E⁰
        assert natural_result["E"] == Fraction(0)
        assert natural_result.is_dimensionless()

    def test_energy_dimension_preserved(self):
        """GIVEN energy dimension (ML²T⁻²), THEN it transforms to E¹."""
        # Energy: M¹L²T⁻²
        # SI: T=-2, L=2, M=1, I=0, Θ=0, J=0, N=0, B=0
        si_energy = Vector(
            SI,
            (Fraction(-2), Fraction(2), Fraction(1), Fraction(0),
             Fraction(0), Fraction(0), Fraction(0), Fraction(0)),
        )
        natural_result = SI_TO_NATURAL(si_energy)

        # M → E, L² → E⁻², T⁻² → E², so M¹L²T⁻² → E¹·E⁻²·E² = E¹
        assert natural_result["E"] == Fraction(1)

    def test_action_is_dimensionless(self):
        """GIVEN action (ML²T⁻¹), THEN it transforms to E⁰ (dimensionless).

        This is the consequence of ℏ = 1: action is dimensionless.
        """
        # Action: M¹L²T⁻¹ (same as ℏ)
        # SI: T=-1, L=2, M=1, I=0, Θ=0, J=0, N=0, B=0
        si_action = Vector(
            SI,
            (Fraction(-1), Fraction(2), Fraction(1), Fraction(0),
             Fraction(0), Fraction(0), Fraction(0), Fraction(0)),
        )
        natural_result = SI_TO_NATURAL(si_action)

        # M → E, L² → E⁻², T⁻¹ → E¹, so M¹L²T⁻¹ → E¹·E⁻²·E¹ = E⁰
        assert natural_result["E"] == Fraction(0)
        assert natural_result.is_dimensionless()

    def test_current_raises_lossy_projection(self):
        """GIVEN current dimension (I), THEN LossyProjection is raised."""
        # SI: T=0, L=0, M=0, I=1, Θ=0, J=0, N=0, B=0
        si_current = Vector(
            SI,
            (Fraction(0), Fraction(0), Fraction(0), Fraction(1),
             Fraction(0), Fraction(0), Fraction(0), Fraction(0)),
        )

        with pytest.raises(LossyProjection) as exc_info:
            SI_TO_NATURAL(si_current)

        assert "current" in str(exc_info.value)

    def test_current_with_allow_projection(self):
        """GIVEN current with allow_projection=True, THEN projected to zero."""
        si_current = Vector(
            SI,
            (Fraction(0), Fraction(0), Fraction(0), Fraction(1),
             Fraction(0), Fraction(0), Fraction(0), Fraction(0)),
        )

        result = SI_TO_NATURAL(si_current, allow_projection=True)
        assert result.is_dimensionless()

    def test_luminous_intensity_raises_lossy_projection(self):
        """GIVEN luminous_intensity (J), THEN LossyProjection is raised."""
        # SI: T=0, L=0, M=0, I=0, Θ=0, J=1, N=0, B=0
        si_luminosity = Vector(
            SI,
            (Fraction(0), Fraction(0), Fraction(0), Fraction(0),
             Fraction(0), Fraction(1), Fraction(0), Fraction(0)),
        )

        with pytest.raises(LossyProjection):
            SI_TO_NATURAL(si_luminosity)


# -----------------------------------------------------------------------------
# NATURAL_TO_SI (Inverse Transform) Tests
# -----------------------------------------------------------------------------


class TestNaturalToSI:
    """Tests for NATURAL_TO_SI inverse transform."""

    def test_is_constant_aware_transform(self):
        """GIVEN NATURAL_TO_SI, THEN it is a ConstantAwareBasisTransform."""
        assert isinstance(NATURAL_TO_SI, ConstantAwareBasisTransform)

    def test_source_is_natural(self):
        """GIVEN NATURAL_TO_SI, THEN source is NATURAL basis."""
        assert NATURAL_TO_SI.source == NATURAL

    def test_target_is_si(self):
        """GIVEN NATURAL_TO_SI, THEN target is SI basis."""
        assert NATURAL_TO_SI.target == SI

    def test_bindings_have_negated_exponents(self):
        """GIVEN NATURAL_TO_SI, THEN binding exponents are negated from forward."""
        # The inverse should have bindings with negated exponents
        for inv_binding in NATURAL_TO_SI.bindings:
            # Find corresponding forward binding
            for fwd_binding in SI_TO_NATURAL.bindings:
                if inv_binding.constant_symbol == fwd_binding.constant_symbol:
                    assert inv_binding.exponent == -fwd_binding.exponent
                    break

    def test_energy_transforms_to_si(self):
        """GIVEN energy in natural units, THEN it can transform to SI."""
        natural_energy = Vector(NATURAL, (Fraction(1),))
        si_result = NATURAL_TO_SI(natural_energy)

        assert si_result.basis == SI
        # The result should have the SI energy dimension signature
        # Note: The exact mapping depends on which binding is primary


# -----------------------------------------------------------------------------
# Round-Trip Tests
# -----------------------------------------------------------------------------


class TestRoundTrip:
    """Tests for SI → NATURAL → SI round-trip consistency."""

    def test_velocity_round_trip(self):
        """GIVEN velocity, WHEN round-tripped, THEN dimensionless preserved."""
        # Velocity L¹T⁻¹ → dimensionless (c=1)
        si_velocity = Vector(
            SI,
            (Fraction(-1), Fraction(1), Fraction(0), Fraction(0),
             Fraction(0), Fraction(0), Fraction(0), Fraction(0)),
        )

        natural = SI_TO_NATURAL(si_velocity)
        assert natural.is_dimensionless()

        # Going back: dimensionless stays dimensionless
        si_back = NATURAL_TO_SI(natural)
        assert si_back.is_dimensionless()

    def test_energy_round_trip(self):
        """GIVEN energy dimension, WHEN round-tripped via natural units, THEN consistent."""
        # Energy M¹L²T⁻² → E¹
        si_energy = Vector(
            SI,
            (Fraction(-2), Fraction(2), Fraction(1), Fraction(0),
             Fraction(0), Fraction(0), Fraction(0), Fraction(0)),
        )

        natural = SI_TO_NATURAL(si_energy)
        assert natural["E"] == Fraction(1)

        # Going back gives the primary SI representation of energy
        si_back = NATURAL_TO_SI(natural)
        assert si_back.basis == SI


# -----------------------------------------------------------------------------
# Particle Physics Dimensions Tests
# -----------------------------------------------------------------------------


class TestParticlePhysicsDimensions:
    """Tests for particle physics dimensional analysis."""

    def test_cross_section_dimension(self):
        """GIVEN cross-section (L²), THEN it transforms to E⁻²."""
        # Cross-section: L²
        si_cross_section = Vector(
            SI,
            (Fraction(0), Fraction(2), Fraction(0), Fraction(0),
             Fraction(0), Fraction(0), Fraction(0), Fraction(0)),
        )
        natural_result = SI_TO_NATURAL(si_cross_section)

        # L² → (E⁻¹)² = E⁻²
        assert natural_result["E"] == Fraction(-2)

    def test_decay_width_dimension(self):
        """GIVEN decay width (T⁻¹), THEN it transforms to E."""
        # Decay width: T⁻¹ (same dimension as frequency)
        si_decay_width = Vector(
            SI,
            (Fraction(-1), Fraction(0), Fraction(0), Fraction(0),
             Fraction(0), Fraction(0), Fraction(0), Fraction(0)),
        )
        natural_result = SI_TO_NATURAL(si_decay_width)

        # T⁻¹ → (E⁻¹)⁻¹ = E
        assert natural_result["E"] == Fraction(1)

    def test_momentum_dimension(self):
        """GIVEN momentum (MLT⁻¹), THEN it transforms to E."""
        # Momentum: M¹L¹T⁻¹
        si_momentum = Vector(
            SI,
            (Fraction(-1), Fraction(1), Fraction(1), Fraction(0),
             Fraction(0), Fraction(0), Fraction(0), Fraction(0)),
        )
        natural_result = SI_TO_NATURAL(si_momentum)

        # M → E, L → E⁻¹, T⁻¹ → E, so M¹L¹T⁻¹ → E¹·E⁻¹·E¹ = E¹
        assert natural_result["E"] == Fraction(1)

    def test_wavelength_dimension(self):
        """GIVEN wavelength (L), THEN it transforms to E⁻¹."""
        # Wavelength is just length
        si_wavelength = Vector(
            SI,
            (Fraction(0), Fraction(1), Fraction(0), Fraction(0),
             Fraction(0), Fraction(0), Fraction(0), Fraction(0)),
        )
        natural_result = SI_TO_NATURAL(si_wavelength)

        assert natural_result["E"] == Fraction(-1)


# -----------------------------------------------------------------------------
# ConstantAwareBasisTransform General Tests
# -----------------------------------------------------------------------------


class TestConstantAwareBasisTransform:
    """General tests for ConstantAwareBasisTransform."""

    def test_wrong_basis_raises(self):
        """GIVEN a vector in wrong basis, THEN ValueError raised."""
        natural_vec = Vector(NATURAL, (Fraction(1),))

        with pytest.raises(ValueError, match="expects basis 'SI'"):
            SI_TO_NATURAL(natural_vec)

    def test_matrix_dimension_validation(self):
        """GIVEN wrong matrix dimensions, THEN ValueError raised."""
        with pytest.raises(ValueError, match="Matrix has 2 rows"):
            ConstantAwareBasisTransform(
                source=SI,  # 8 components
                target=NATURAL,  # 1 component
                matrix=(
                    (Fraction(1),),
                    (Fraction(1),),
                    # Missing 6 rows
                ),
            )

    def test_as_basis_transform(self):
        """GIVEN ConstantAwareBasisTransform, THEN as_basis_transform works."""
        from ucon.basis import BasisTransform

        plain = SI_TO_NATURAL.as_basis_transform()
        assert isinstance(plain, BasisTransform)
        assert plain.source == SI
        assert plain.target == NATURAL
        assert plain.matrix == SI_TO_NATURAL.matrix

    def test_repr(self):
        """GIVEN ConstantAwareBasisTransform, THEN repr is informative."""
        assert "SI" in repr(SI_TO_NATURAL)
        assert "natural" in repr(SI_TO_NATURAL)
