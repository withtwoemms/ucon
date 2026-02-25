# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Tests for physical constants (v0.9.0)."""

import math

import pytest

from ucon import Constant, Number, units, constants
from ucon.dimension import Dimension


class TestConstantClass:
    """Tests for Constant dataclass."""

    def test_constant_creation(self):
        """Constant can be created with valid attributes."""
        c = Constant(
            symbol="c",
            name="speed of light",
            value=299792458,
            unit=units.meter / units.second,
            uncertainty=None,
        )
        assert c.symbol == "c"
        assert c.name == "speed of light"
        assert c.value == 299792458
        assert c.uncertainty is None

    def test_is_exact_true(self):
        """is_exact returns True when uncertainty is None."""
        c = Constant(
            symbol="c",
            name="speed of light",
            value=299792458,
            unit=units.meter / units.second,
            uncertainty=None,
        )
        assert c.is_exact is True

    def test_is_exact_false(self):
        """is_exact returns False when uncertainty is set."""
        G = Constant(
            symbol="G",
            name="gravitational constant",
            value=6.67430e-11,
            unit=units.meter ** 3 / (units.kilogram * units.second ** 2),
            uncertainty=0.00015e-11,
        )
        assert G.is_exact is False

    def test_as_number(self):
        """as_number() returns Number with correct attributes."""
        c = constants.speed_of_light
        n = c.as_number()
        assert isinstance(n, Number)
        assert n.quantity == 299792458
        assert n.uncertainty is None

    def test_as_number_with_uncertainty(self):
        """as_number() includes uncertainty for measured constants."""
        G = constants.gravitational_constant
        n = G.as_number()
        assert isinstance(n, Number)
        assert n.uncertainty is not None

    def test_dimension_property(self):
        """dimension property returns correct dimension."""
        c = constants.speed_of_light
        assert c.dimension == Dimension.velocity

    def test_repr_exact(self):
        """repr shows (exact) for exact constants."""
        c = constants.speed_of_light
        assert "(exact)" in repr(c)

    def test_repr_measured(self):
        """repr shows uncertainty for measured constants."""
        G = constants.gravitational_constant
        assert "±" in repr(G)


class TestSIDefiningConstants:
    """Tests for SI defining constants (exact)."""

    def test_speed_of_light_exact(self):
        """Speed of light is exact."""
        assert constants.speed_of_light.is_exact
        assert constants.speed_of_light.value == 299792458

    def test_planck_constant_exact(self):
        """Planck constant is exact."""
        assert constants.planck_constant.is_exact
        assert constants.planck_constant.value == 6.62607015e-34

    def test_elementary_charge_exact(self):
        """Elementary charge is exact."""
        assert constants.elementary_charge.is_exact
        assert constants.elementary_charge.value == 1.602176634e-19

    def test_boltzmann_constant_exact(self):
        """Boltzmann constant is exact."""
        assert constants.boltzmann_constant.is_exact
        assert constants.boltzmann_constant.value == 1.380649e-23

    def test_avogadro_constant_exact(self):
        """Avogadro constant is exact."""
        assert constants.avogadro_constant.is_exact
        assert constants.avogadro_constant.value == 6.02214076e23

    def test_luminous_efficacy_exact(self):
        """Luminous efficacy is exact."""
        assert constants.luminous_efficacy.is_exact
        assert constants.luminous_efficacy.value == 683

    def test_hyperfine_transition_exact(self):
        """Hyperfine transition frequency is exact."""
        assert constants.hyperfine_transition_frequency.is_exact
        assert constants.hyperfine_transition_frequency.value == 9192631770


class TestDerivedConstants:
    """Tests for derived constants."""

    def test_reduced_planck_constant(self):
        """Reduced Planck constant is h/2π."""
        h = constants.planck_constant.value
        hbar = constants.reduced_planck_constant.value
        assert hbar == pytest.approx(h / (2 * math.pi))

    def test_reduced_planck_constant_exact(self):
        """Reduced Planck constant is exact (derived from exact h)."""
        assert constants.reduced_planck_constant.is_exact

    def test_molar_gas_constant_exact(self):
        """Molar gas constant is exact."""
        assert constants.molar_gas_constant.is_exact

    def test_stefan_boltzmann_constant_exact(self):
        """Stefan-Boltzmann constant is exact."""
        assert constants.stefan_boltzmann_constant.is_exact


class TestMeasuredConstants:
    """Tests for measured constants (with uncertainty)."""

    def test_gravitational_constant_has_uncertainty(self):
        """Gravitational constant has uncertainty."""
        G = constants.gravitational_constant
        assert not G.is_exact
        assert G.uncertainty is not None
        assert G.uncertainty > 0

    def test_fine_structure_constant_has_uncertainty(self):
        """Fine-structure constant has uncertainty."""
        alpha = constants.fine_structure_constant
        assert not alpha.is_exact
        assert alpha.uncertainty is not None

    def test_electron_mass_has_uncertainty(self):
        """Electron mass has uncertainty."""
        m_e = constants.electron_mass
        assert not m_e.is_exact
        assert m_e.uncertainty is not None


class TestConstantAliases:
    """Tests for Unicode and ASCII aliases."""

    def test_unicode_c(self):
        """'c' alias works."""
        assert constants.c is constants.speed_of_light

    def test_unicode_h(self):
        """'h' alias works."""
        assert constants.h is constants.planck_constant

    def test_unicode_hbar(self):
        """'ℏ' alias works."""
        hbar = getattr(constants, 'ℏ')
        assert hbar is constants.reduced_planck_constant

    def test_unicode_G(self):
        """'G' alias works."""
        assert constants.G is constants.gravitational_constant

    def test_unicode_alpha(self):
        """'α' alias works."""
        assert constants.α is constants.fine_structure_constant

    def test_ascii_hbar(self):
        """'hbar' ASCII alias works."""
        assert constants.hbar is constants.reduced_planck_constant

    def test_ascii_alpha(self):
        """'alpha' ASCII alias works."""
        assert constants.alpha is constants.fine_structure_constant

    def test_ascii_epsilon_0(self):
        """'epsilon_0' ASCII alias works."""
        assert constants.epsilon_0 is constants.vacuum_permittivity

    def test_ascii_m_e(self):
        """'m_e' ASCII alias works."""
        assert constants.m_e is constants.electron_mass


class TestConstantArithmetic:
    """Tests for constant arithmetic with Numbers."""

    def test_constant_times_number(self):
        """Constant * Number returns Number."""
        freq = units.hertz(5e14)
        energy = constants.h * freq
        assert isinstance(energy, Number)

    def test_number_times_constant(self):
        """Number * Constant returns Number."""
        mass = units.kilogram(1)
        energy = mass * constants.c ** 2
        assert isinstance(energy, Number)

    def test_scalar_times_constant(self):
        """scalar * Constant returns Number."""
        half_c = constants.c * 0.5
        assert isinstance(half_c, Number)
        assert half_c.quantity == 0.5 * 299792458

    def test_constant_division(self):
        """Constant / Number returns Number."""
        result = constants.h / units.second(1)
        assert isinstance(result, Number)

    def test_constant_power(self):
        """Constant ** exp returns Number."""
        c_squared = constants.c ** 2
        assert isinstance(c_squared, Number)
        assert c_squared.quantity == pytest.approx(299792458 ** 2)

    def test_constant_subtraction(self):
        """Constant - Number returns Number."""
        result = constants.c - units.meter(1) / units.second(1)
        assert isinstance(result, Number)


class TestPhysicsFormulas:
    """Tests for constants in real physics formulas."""

    def test_e_equals_mc_squared(self):
        """E = mc² works correctly."""
        mass = units.kilogram(1)
        energy = mass * constants.c ** 2
        expected = 299792458 ** 2
        assert energy.quantity == pytest.approx(expected)
        assert energy.unit.dimension == Dimension.energy

    def test_photon_energy(self):
        """E = hν works correctly."""
        frequency = units.hertz(5e14)
        energy = constants.h * frequency
        expected = 6.62607015e-34 * 5e14
        assert energy.quantity == pytest.approx(expected)

    def test_de_broglie_wavelength(self):
        """λ = h/p works correctly."""
        momentum = units.kilogram(1) * (units.meter / units.second)(1)
        wavelength = constants.h / momentum
        expected = 6.62607015e-34
        assert wavelength.quantity == pytest.approx(expected)

    def test_ideal_gas_constant(self):
        """R = k_B * N_A relationship."""
        # R should be approximately k_B * N_A
        k_B = constants.boltzmann_constant.value
        N_A = constants.avogadro_constant.value
        R = constants.molar_gas_constant.value
        assert R == pytest.approx(k_B * N_A)


class TestUncertaintyPropagation:
    """Tests for uncertainty propagation through calculations."""

    def test_measured_constant_propagates_uncertainty(self):
        """Measured constant uncertainty propagates through arithmetic."""
        mass = units.kilogram(1)
        # G has uncertainty, so result should too
        G = constants.G
        force = G * mass * mass / units.meter(1) ** 2
        # The result should have uncertainty from G
        assert force.uncertainty is not None

    def test_exact_constant_no_uncertainty(self):
        """Exact constant doesn't add uncertainty."""
        mass = units.kilogram(1)
        energy = mass * constants.c ** 2
        # c is exact, mass has no uncertainty, so result has no uncertainty
        assert energy.uncertainty is None


class TestCustomConstants:
    """Tests for user-defined constants."""

    def test_custom_constant_creation(self):
        """Users can create domain-specific constants."""
        speed_of_sound = Constant(
            symbol="vₛ",
            name="speed of sound in dry air at 20°C",
            value=343,
            unit=units.meter / units.second,
            uncertainty=None,
            source="Engineering Tables",
        )
        assert speed_of_sound.symbol == "vₛ"
        assert speed_of_sound.is_exact
        assert speed_of_sound.source == "Engineering Tables"

    def test_custom_constant_with_uncertainty(self):
        """Custom constants can have uncertainty."""
        band_gap = Constant(
            symbol="Eg",
            name="silicon band gap at 300K",
            value=1.12,
            unit=units.joule,  # simplified - eV not in standard units
            uncertainty=0.01,
            source="Sze, Physics of Semiconductor Devices",
        )
        assert not band_gap.is_exact
        assert band_gap.uncertainty == 0.01

    def test_custom_constant_arithmetic(self):
        """Custom constants work in arithmetic."""
        my_constant = Constant(
            symbol="X",
            name="test constant",
            value=42,
            unit=units.meter,
            uncertainty=1,
        )
        result = my_constant * 2
        assert isinstance(result, Number)
        assert result.quantity == 84


class TestModuleExports:
    """Tests for module-level exports."""

    def test_constant_exported_from_ucon(self):
        """Constant class is exported from ucon."""
        from ucon import Constant
        assert Constant is not None

    def test_constants_module_exported(self):
        """constants module is exported from ucon."""
        from ucon import constants
        assert constants is not None
        assert hasattr(constants, 'speed_of_light')
