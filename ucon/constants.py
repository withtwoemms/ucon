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

from ucon.core import Number

if TYPE_CHECKING:
    from ucon.core import Unit, UnitProduct
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
    aliases: tuple = ()

    def as_number(self) -> 'Number':
        """Return as Number for calculations."""
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


def _build_constants():
    """Load constants from the TOML via the central loader.

    Returns a dict keyed by descriptive name (e.g. 'speed_of_light'),
    matching the contract expected by ``all_constants()`` and ``__getattr__``.
    """
    from ucon._loader import get_graph

    graph = get_graph()
    constants: dict[str, Constant] = {}
    for const in graph._package_constants:
        # Find the short descriptive alias (e.g. "speed_of_light") if available,
        # otherwise derive from the full name.
        descriptive = None
        for alias in getattr(const, 'aliases', ()):
            # Prefer the snake_case descriptive alias (not symbols like "Eh")
            if '_' in alias or alias.replace('_', '').isalpha():
                descriptive = alias
                break
        if descriptive is None:
            descriptive = const.name.replace(" ", "_").replace("-", "_").lower()
        constants[descriptive] = const
    return constants


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
        All built-in CODATA physical constants.

    Examples
    --------
    >>> from ucon.constants import all_constants
    >>> constants = all_constants()
    >>> len(constants)
    17
    >>> [c.symbol for c in constants if c.category == "exact"]
    ... # ['ΔνCs', 'c', 'h', 'e', 'k', 'NA', 'Kcd']
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
        'gₙ': 'standard_gravity',
        'Eₕ': 'hartree_energy',
        'a₀': 'bohr_radius',
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
        'g_n': 'standard_gravity',
        'g_0': 'standard_gravity',
        'E_h': 'hartree_energy',
        'a_0': 'bohr_radius',
        'm_P': 'planck_mass',
        'l_P': 'planck_length',
        't_P': 'planck_time',
        'T_P': 'planck_temperature',
    }

    if symbol in _unicode_aliases:
        return constants[_unicode_aliases[symbol]]
    if symbol in _ascii_aliases:
        return constants[_ascii_aliases[symbol]]

    return None


def __getattr__(name: str):
    """Lazy attribute access for constants and aliases."""
    # Don't intercept dunder attributes (e.g. __path__, __spec__)
    if name.startswith('__') and name.endswith('__'):
        raise AttributeError(name)

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
        'gₙ': 'standard_gravity',
        'Eₕ': 'hartree_energy',
        'a₀': 'bohr_radius',
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
        'g_n': 'standard_gravity',
        'g_0': 'standard_gravity',
        'E_h': 'hartree_energy',
        'a_0': 'bohr_radius',
        'm_P': 'planck_mass',
        'l_P': 'planck_length',
        't_P': 'planck_time',
        'T_P': 'planck_temperature',
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
    # Exact definitional
    'standard_gravity',
    # Measured constants
    'gravitational_constant',
    'fine_structure_constant',
    'electron_mass',
    'proton_mass',
    'neutron_mass',
    'vacuum_permittivity',
    'vacuum_permeability',
    # Atomic-scale measured
    'hartree_energy',
    'rydberg_energy',
    'bohr_radius',
    'atomic_unit_of_time',
    # Planck-scale measured
    'planck_mass',
    'planck_length',
    'planck_time',
    'planck_temperature',
    # Unicode aliases
    'c', 'h', 'ℏ', 'e', 'k_B', 'N_A', 'G', 'α', 'ε₀', 'μ₀', 'mₑ', 'mₚ', 'mₙ', 'σ', 'R',
    'gₙ', 'Eₕ', 'a₀',
    # ASCII aliases
    'hbar', 'alpha', 'epsilon_0', 'mu_0', 'm_e', 'm_p', 'm_n',
    'g_n', 'g_0', 'E_h', 'a_0', 'm_P', 'l_P', 't_P', 'T_P',
]
