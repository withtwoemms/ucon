# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
ucon.constants
==============

Physical constants with CODATA 2022 uncertainties.

The 2019 SI redefinition made 7 constants exact by definition.
Measured constants carry uncertainties that propagate through calculations.

Examples
--------
>>> from ucon.constants import c, h, G
>>> from ucon import units

# E = mc²
>>> mass = units.kilogram(1)
>>> energy = mass * c ** 2
>>> energy.dimension
Dimension.energy

# E = hν (photon energy)
>>> frequency = units.hertz(5e14)
>>> energy = h * frequency

# Gravitational force (uncertainty propagates)
>>> F = G * units.kilogram(1) * units.kilogram(1) / units.meter(1) ** 2
>>> F.uncertainty is not None
True
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from ucon.core import Number, Unit, UnitProduct
    from ucon.dimension import Dimension


@dataclass(frozen=True)
class Constant:
    """A physical constant with CODATA uncertainty.

    Attributes
    ----------
    symbol : str
        Standard symbol (e.g., "c", "h", "G").
    name : str
        Full name (e.g., "speed of light in vacuum").
    value : float
        Numeric value in SI units.
    unit : Unit | UnitProduct
        SI unit of the constant.
    uncertainty : float | None
        Standard uncertainty. None indicates exact (by definition).
    source : str
        Data source (default: "CODATA 2022").
    category : str
        Category: "exact", "derived", "measured", or "session".

    Examples
    --------
    >>> from ucon.constants import speed_of_light
    >>> speed_of_light.symbol
    'c'
    >>> speed_of_light.is_exact
    True
    >>> speed_of_light.as_number()
    <299792458 m/s>
    """
    symbol: str
    name: str
    value: float
    unit: Union['Unit', 'UnitProduct']
    uncertainty: Union[float, None]
    source: str = "CODATA 2022"
    category: str = "measured"

    def as_number(self) -> 'Number':
        """Return as Number for calculations."""
        from ucon.core import Number
        return Number(
            quantity=self.value,
            unit=self.unit,
            uncertainty=self.uncertainty,
        )

    @property
    def dimension(self) -> 'Dimension':
        """Dimension of the constant."""
        return self.unit.dimension

    @property
    def is_exact(self) -> bool:
        """True if constant is exact by definition."""
        return self.uncertainty is None

    # -------------------------------------------------------------------------
    # Arithmetic (returns Number, not Constant)
    # -------------------------------------------------------------------------

    def __mul__(self, other) -> 'Number':
        return self.as_number() * other

    def __rmul__(self, other) -> 'Number':
        return other * self.as_number()

    def __truediv__(self, other) -> 'Number':
        return self.as_number() / other

    def __rtruediv__(self, other) -> 'Number':
        return other / self.as_number()

    def __add__(self, other) -> 'Number':
        return self.as_number() + other

    def __radd__(self, other) -> 'Number':
        return other + self.as_number()

    def __sub__(self, other) -> 'Number':
        return self.as_number() - other

    def __rsub__(self, other) -> 'Number':
        return other - self.as_number()

    def __pow__(self, exp) -> 'Number':
        return self.as_number() ** exp

    def __neg__(self) -> 'Number':
        return -self.as_number()

    def __pos__(self) -> 'Number':
        return +self.as_number()

    def __repr__(self) -> str:
        unit_str = self.unit.shorthand if hasattr(self.unit, 'shorthand') else str(self.unit)
        if self.is_exact:
            return f"<{self.symbol} = {self.value} {unit_str} (exact)>"
        else:
            return f"<{self.symbol} = {self.value} ± {self.uncertainty} {unit_str}>"


# =============================================================================
# SI Defining Constants (Exact)
# =============================================================================
# The 2019 SI redefinition fixed these 7 constants exactly.

def _build_constants():
    """Build constants after units module is loaded."""
    from ucon import units
    from ucon.core import Scale

    # -------------------------------------------------------------------------
    # SI Defining Constants (Exact)
    # -------------------------------------------------------------------------

    hyperfine_transition_frequency = Constant(
        symbol="ΔνCs",
        name="hyperfine transition frequency of caesium-133",
        value=9192631770,
        unit=units.hertz,
        uncertainty=None,
        category="exact",
    )

    speed_of_light = Constant(
        symbol="c",
        name="speed of light in vacuum",
        value=299792458,
        unit=units.meter / units.second,
        uncertainty=None,
        category="exact",
    )

    planck_constant = Constant(
        symbol="h",
        name="Planck constant",
        value=6.62607015e-34,
        unit=units.joule * units.second,
        uncertainty=None,
        category="exact",
    )

    elementary_charge = Constant(
        symbol="e",
        name="elementary charge",
        value=1.602176634e-19,
        unit=units.coulomb,
        uncertainty=None,
        category="exact",
    )

    boltzmann_constant = Constant(
        symbol="k",
        name="Boltzmann constant",
        value=1.380649e-23,
        unit=units.joule / units.kelvin,
        uncertainty=None,
        category="exact",
    )

    avogadro_constant = Constant(
        symbol="NA",
        name="Avogadro constant",
        value=6.02214076e23,
        unit=units.none / units.mole,
        uncertainty=None,
        category="exact",
    )

    luminous_efficacy = Constant(
        symbol="Kcd",
        name="luminous efficacy of 540 THz radiation",
        value=683,
        unit=units.lumen / units.watt,
        uncertainty=None,
        category="exact",
    )

    # -------------------------------------------------------------------------
    # Derived Constants (Exact, derived from exact constants)
    # -------------------------------------------------------------------------

    import math
    reduced_planck_constant = Constant(
        symbol="ℏ",
        name="reduced Planck constant",
        value=6.62607015e-34 / (2 * math.pi),
        unit=units.joule * units.second,
        uncertainty=None,
        category="derived",
    )

    molar_gas_constant = Constant(
        symbol="R",
        name="molar gas constant",
        value=8.314462618,
        unit=units.joule / (units.mole * units.kelvin),
        uncertainty=None,
        category="derived",
    )

    stefan_boltzmann_constant = Constant(
        symbol="σ",
        name="Stefan-Boltzmann constant",
        value=5.670374419e-8,
        unit=units.watt / (units.meter ** 2 * units.kelvin ** 4),
        uncertainty=None,
        category="derived",
    )

    # -------------------------------------------------------------------------
    # Measured Constants (With Uncertainty)
    # -------------------------------------------------------------------------

    gravitational_constant = Constant(
        symbol="G",
        name="Newtonian constant of gravitation",
        value=6.67430e-11,
        unit=units.meter ** 3 / (units.kilogram * units.second ** 2),
        uncertainty=0.00015e-11,
        category="measured",
    )

    fine_structure_constant = Constant(
        symbol="α",
        name="fine-structure constant",
        value=7.2973525693e-3,
        unit=units.none,
        uncertainty=0.0000000011e-3,
        category="measured",
    )

    electron_mass = Constant(
        symbol="mₑ",
        name="electron mass",
        value=9.1093837015e-31,
        unit=units.kilogram,
        uncertainty=0.0000000028e-31,
        category="measured",
    )

    proton_mass = Constant(
        symbol="mₚ",
        name="proton mass",
        value=1.67262192369e-27,
        unit=units.kilogram,
        uncertainty=0.00000000051e-27,
        category="measured",
    )

    neutron_mass = Constant(
        symbol="mₙ",
        name="neutron mass",
        value=1.67492749804e-27,
        unit=units.kilogram,
        uncertainty=0.00000000095e-27,
        category="measured",
    )

    vacuum_permittivity = Constant(
        symbol="ε₀",
        name="vacuum electric permittivity",
        value=8.8541878128e-12,
        unit=units.farad / units.meter,
        uncertainty=0.0000000013e-12,
        category="measured",
    )

    vacuum_permeability = Constant(
        symbol="μ₀",
        name="vacuum magnetic permeability",
        value=1.25663706212e-6,
        unit=units.henry / units.meter,
        uncertainty=0.00000000019e-6,
        category="measured",
    )

    return {
        # SI defining (exact)
        'hyperfine_transition_frequency': hyperfine_transition_frequency,
        'speed_of_light': speed_of_light,
        'planck_constant': planck_constant,
        'elementary_charge': elementary_charge,
        'boltzmann_constant': boltzmann_constant,
        'avogadro_constant': avogadro_constant,
        'luminous_efficacy': luminous_efficacy,
        # Derived (exact)
        'reduced_planck_constant': reduced_planck_constant,
        'molar_gas_constant': molar_gas_constant,
        'stefan_boltzmann_constant': stefan_boltzmann_constant,
        # Measured
        'gravitational_constant': gravitational_constant,
        'fine_structure_constant': fine_structure_constant,
        'electron_mass': electron_mass,
        'proton_mass': proton_mass,
        'neutron_mass': neutron_mass,
        'vacuum_permittivity': vacuum_permittivity,
        'vacuum_permeability': vacuum_permeability,
    }


# Lazy initialization to avoid circular imports
_constants_cache: dict = {}


def _get_constants() -> dict:
    """Get or build constants cache."""
    global _constants_cache
    if not _constants_cache:
        _constants_cache = _build_constants()
    return _constants_cache


def all_constants() -> list[Constant]:
    """Return all built-in constants.

    Returns
    -------
    list[Constant]
        All 17 CODATA physical constants.

    Examples
    --------
    >>> from ucon.constants import all_constants
    >>> constants = all_constants()
    >>> len(constants)
    17
    >>> [c.symbol for c in constants if c.category == "exact"]
    ['ΔνCs', 'c', 'h', 'e', 'k', 'NA', 'Kcd']
    """
    return list(_get_constants().values())


def get_constant_by_symbol(symbol: str) -> Constant | None:
    """Look up a constant by symbol or alias.

    Parameters
    ----------
    symbol : str
        Symbol to look up (e.g., "c", "h", "G", "hbar", "ℏ").

    Returns
    -------
    Constant | None
        The matching constant, or None if not found.

    Examples
    --------
    >>> from ucon.constants import get_constant_by_symbol
    >>> c = get_constant_by_symbol("c")
    >>> c.name
    'speed of light in vacuum'
    >>> get_constant_by_symbol("hbar").symbol
    'ℏ'
    """
    constants = _get_constants()

    # Direct symbol match
    for const in constants.values():
        if const.symbol == symbol:
            return const

    # Unicode aliases
    _unicode_aliases = {
        'c': 'speed_of_light',
        'h': 'planck_constant',
        'ℏ': 'reduced_planck_constant',
        'e': 'elementary_charge',
        'k_B': 'boltzmann_constant',
        'k': 'boltzmann_constant',
        'N_A': 'avogadro_constant',
        'NA': 'avogadro_constant',
        'G': 'gravitational_constant',
        'α': 'fine_structure_constant',
        'ε₀': 'vacuum_permittivity',
        'μ₀': 'vacuum_permeability',
        'mₑ': 'electron_mass',
        'mₚ': 'proton_mass',
        'mₙ': 'neutron_mass',
        'σ': 'stefan_boltzmann_constant',
        'R': 'molar_gas_constant',
        'Kcd': 'luminous_efficacy',
        'ΔνCs': 'hyperfine_transition_frequency',
    }

    # ASCII aliases
    _ascii_aliases = {
        'hbar': 'reduced_planck_constant',
        'alpha': 'fine_structure_constant',
        'epsilon_0': 'vacuum_permittivity',
        'mu_0': 'vacuum_permeability',
        'm_e': 'electron_mass',
        'm_p': 'proton_mass',
        'm_n': 'neutron_mass',
    }

    if symbol in _unicode_aliases:
        return constants[_unicode_aliases[symbol]]
    if symbol in _ascii_aliases:
        return constants[_ascii_aliases[symbol]]

    return None


def __getattr__(name: str):
    """Lazy attribute access for constants and aliases."""
    constants = _get_constants()

    # Direct constant names
    if name in constants:
        return constants[name]

    # Unicode aliases
    _unicode_aliases = {
        'c': 'speed_of_light',
        'h': 'planck_constant',
        'ℏ': 'reduced_planck_constant',
        'e': 'elementary_charge',
        'k_B': 'boltzmann_constant',
        'N_A': 'avogadro_constant',
        'G': 'gravitational_constant',
        'α': 'fine_structure_constant',
        'ε₀': 'vacuum_permittivity',
        'μ₀': 'vacuum_permeability',
        'mₑ': 'electron_mass',
        'mₚ': 'proton_mass',
        'mₙ': 'neutron_mass',
        'σ': 'stefan_boltzmann_constant',
        'R': 'molar_gas_constant',
    }

    # ASCII aliases
    _ascii_aliases = {
        'hbar': 'reduced_planck_constant',
        'alpha': 'fine_structure_constant',
        'epsilon_0': 'vacuum_permittivity',
        'mu_0': 'vacuum_permeability',
        'm_e': 'electron_mass',
        'm_p': 'proton_mass',
        'm_n': 'neutron_mass',
    }

    if name in _unicode_aliases:
        return constants[_unicode_aliases[name]]
    if name in _ascii_aliases:
        return constants[_ascii_aliases[name]]

    raise AttributeError(f"module 'ucon.constants' has no attribute {name!r}")


__all__ = [
    'Constant',
    # Enumeration functions
    'all_constants',
    'get_constant_by_symbol',
    # SI defining constants (exact)
    'hyperfine_transition_frequency',
    'speed_of_light',
    'planck_constant',
    'elementary_charge',
    'boltzmann_constant',
    'avogadro_constant',
    'luminous_efficacy',
    # Derived constants (exact)
    'reduced_planck_constant',
    'molar_gas_constant',
    'stefan_boltzmann_constant',
    # Measured constants
    'gravitational_constant',
    'fine_structure_constant',
    'electron_mass',
    'proton_mass',
    'neutron_mass',
    'vacuum_permittivity',
    'vacuum_permeability',
    # Unicode aliases
    'c', 'h', 'ℏ', 'e', 'k_B', 'N_A', 'G', 'α', 'ε₀', 'μ₀', 'mₑ', 'mₚ', 'mₙ', 'σ', 'R',
    # ASCII aliases
    'hbar', 'alpha', 'epsilon_0', 'mu_0', 'm_e', 'm_p', 'm_n',
]
