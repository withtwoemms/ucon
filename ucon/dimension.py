# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
ucon.dimension
==============

Defines physical dimensions using basis-aware exponent vectors.

The Dimension class represents physical dimensions as immutable dataclasses
backed by Vector exponents. This replaces the previous Enum-based approach
with a more flexible system that supports:

- Algebraic operations (multiplication, division, exponentiation)
- Named dimensions via attribute access (Dimension.length, Dimension.mass)
- Module constants (LENGTH, MASS, etc.) for static imports
- Derived dimensions created dynamically from algebraic expressions
- Pseudo-dimensions (ANGLE, RATIO, COUNT) that are semantically isolated
- Basis-aware transformations for cross-system dimensional analysis

Example
-------
>>> from ucon import Dimension
>>> Dimension.length / Dimension.time == Dimension.velocity
True
>>> Dimension.length ** 2
Dimension(area)

# Module constants also available:
>>> from ucon.dimension import LENGTH, TIME
>>> LENGTH / TIME
Dimension(velocity)
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import TYPE_CHECKING

from ucon.basis import Basis, BasisComponent, Vector, get_default_basis
from ucon.basis.builtin import SI

if TYPE_CHECKING:
    from ucon.basis import BasisTransform


# -----------------------------------------------------------------------------
# Registry for dimension resolution
# -----------------------------------------------------------------------------

_REGISTRY: dict[Vector, "Dimension"] = {}
_DIM_MUL_CACHE: dict[tuple[int, int], "Dimension"] = {}
_DIM_DIV_CACHE: dict[tuple[int, int], "Dimension"] = {}
_DIM_POW_CACHE: dict[tuple[int, object], "Dimension"] = {}


def _register(dim: "Dimension") -> "Dimension":
    """Register a dimension for resolution by vector."""
    if dim.tag is None:  # Don't register pseudo-dimensions
        _REGISTRY[dim.vector] = dim
    return dim


def resolve(vector: Vector) -> "Dimension":
    """Resolve a vector to a named dimension, or create a derived dimension.

    Parameters
    ----------
    vector : Vector
        The dimensional exponent vector to resolve.

    Returns
    -------
    Dimension
        A registered dimension if one matches, otherwise a new derived dimension.

    Examples
    --------
    >>> from ucon.dimension import SI, resolve
    >>> from ucon.basis import Vector
    >>> from fractions import Fraction
    >>> v = Vector(SI, (Fraction(-1), Fraction(1), Fraction(0), Fraction(0),
    ...                  Fraction(0), Fraction(0), Fraction(0), Fraction(0)))
    >>> resolve(v)
    Dimension(velocity)
    """
    if vector in _REGISTRY:
        return _REGISTRY[vector]

    # Zero vector always resolves to NONE
    if vector.is_dimensionless():
        none_vector = Vector(vector.basis, tuple(0 for _ in vector.components))
        if none_vector in _REGISTRY:
            return _REGISTRY[none_vector]

    # Create a derived dimension
    name = _vector_to_dim_expr(vector)
    return Dimension(vector=vector, name=f"derived({name})")


def _vector_to_dim_expr(v: Vector) -> str:
    """Render a Vector as a human-readable dimensional expression.

    Positive exponents go in the numerator, negative in the denominator.
    Exponent 1 is implicit. Integer fractions render as ints.

    Examples:
        Vector(T=-2, L=1, M=1) -> "length*mass/time^2"
        Vector(L=3, T=-1)      -> "length^3/time"
        Vector()               -> "dimensionless"
    """
    numerator = []
    denominator = []

    for comp, exp in zip(v.basis, v.components):
        if exp == 0:
            continue

        name = comp.name
        exp_val = int(exp) if isinstance(exp, int) or (isinstance(exp, Fraction) and exp.denominator == 1) else float(exp)
        abs_exp = abs(exp_val)

        token = name if abs_exp == 1 else f"{name}^{abs_exp}"

        if exp > 0:
            numerator.append(token)
        else:
            denominator.append(token)

    if not numerator and not denominator:
        return "dimensionless"

    num_str = "*".join(numerator) if numerator else "1"
    if denominator:
        return f"{num_str}/{'*'.join(denominator)}"
    return num_str


# -----------------------------------------------------------------------------
# Dimension Dataclass
# -----------------------------------------------------------------------------

# Registry for Dimension.length style attribute access
_DIMENSION_ATTRS: dict[str, "Dimension"] = {}


def _register_attr(dim: "Dimension") -> "Dimension":
    """Register a dimension for attribute access via Dimension.name."""
    if dim.name:
        _DIMENSION_ATTRS[dim.name] = dim
    return dim


class _DimensionMeta(type):
    """Metaclass providing Dimension.length style attribute access.

    This allows both:
    - `from ucon.dimension import LENGTH` (module constant)
    - `Dimension.length` (attribute access, discoverable via IDE)
    """

    def __getattr__(cls, name: str) -> "Dimension":
        if name.startswith("_"):
            raise AttributeError(f"type object 'Dimension' has no attribute {name!r}")
        if name in _DIMENSION_ATTRS:
            return _DIMENSION_ATTRS[name]
        raise AttributeError(
            f"type object 'Dimension' has no attribute {name!r}. "
            f"Available dimensions: {', '.join(sorted(_DIMENSION_ATTRS.keys()))}"
        )

    def __dir__(cls) -> list[str]:
        # Include dimension names in dir() for IDE discoverability
        return list(super().__dir__()) + list(_DIMENSION_ATTRS.keys())


@dataclass(frozen=True)
class Dimension(metaclass=_DimensionMeta):
    """A physical dimension represented by an exponent vector over a basis.

    Parameters
    ----------
    vector : Vector
        The dimensional exponent vector.
    name : str | None
        Optional human-readable name (e.g., "length", "velocity").
    symbol : str | None
        Optional short symbol (e.g., "L", "T").
    tag : str | None
        Tag for pseudo-dimensions. Pseudo-dimensions share the zero vector
        but are semantically isolated (e.g., "angle", "ratio", "count").

    Examples
    --------
    >>> from ucon.dimension import LENGTH, TIME
    >>> velocity = LENGTH / TIME
    >>> velocity == VELOCITY
    True
    """

    vector: Vector
    name: str | None = None
    symbol: str | None = None
    tag: str | None = None

    def __post_init__(self):
        object.__setattr__(self, '_hash_cache', hash((self.vector, self.tag)))

    @classmethod
    def from_components(
        cls,
        basis: Basis = None,
        *,
        name: str | None = None,
        symbol: str | None = None,
        **components: int | float | Fraction,
    ) -> "Dimension":
        """Create a dimension from named component exponents.

        Parameters
        ----------
        basis : Basis
            The basis to use. Defaults to SI.
        name : str | None
            Optional name for the dimension.
        symbol : str | None
            Optional symbol for the dimension.
        **components
            Named exponents (e.g., L=1, T=-1 for velocity).

        Returns
        -------
        Dimension
            A new dimension with the specified components.

        Examples
        --------
        >>> velocity = Dimension.from_components(L=1, T=-1, name="velocity")
        >>> velocity == LENGTH / TIME
        True
        """
        if basis is None:
            basis = get_default_basis()

        # Build component tuple
        exponents = []
        for comp in basis:
            # Try name first, then symbol
            exp = components.get(comp.name, 0)
            if exp == 0 and comp.symbol is not None:
                exp = components.get(comp.symbol, 0)
            exponents.append(exp if isinstance(exp, (int, Fraction)) else Fraction(exp))

        vector = Vector(basis, tuple(exponents))
        return cls(vector=vector, name=name, symbol=symbol)

    @classmethod
    def pseudo(
        cls,
        tag: str,
        *,
        name: str | None = None,
        symbol: str | None = None,
        basis: Basis = None,
    ) -> "Dimension":
        """Create a pseudo-dimension with a semantic tag.

        Pseudo-dimensions share the zero vector (dimensionless) but are
        semantically isolated from each other and from NONE.

        Parameters
        ----------
        tag : str
            Semantic tag for isolation (e.g., "angle", "ratio", "count").
        name : str | None
            Optional name. Defaults to tag.
        symbol : str | None
            Optional symbol.
        basis : Basis
            The basis to use. Defaults to SI.

        Returns
        -------
        Dimension
            A pseudo-dimension with the specified tag.

        Examples
        --------
        >>> ANGLE = Dimension.pseudo("angle", name="angle")
        >>> ANGLE.is_pseudo
        True
        >>> ANGLE == NONE
        False
        """
        if basis is None:
            basis = get_default_basis()
        if name is None:
            name = tag

        vector = basis.zero_vector()
        return cls(vector=vector, name=name, symbol=symbol, tag=tag)

    def in_basis(self, transform: "BasisTransform") -> "Dimension":
        """Transform this dimension to a different basis.

        Parameters
        ----------
        transform : BasisTransform
            The transform to apply.

        Returns
        -------
        Dimension
            A new dimension in the target basis.

        Raises
        ------
        ValueError
            If this dimension's basis doesn't match the transform source.
        """
        new_vector = transform(self.vector)
        return resolve(new_vector)

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def basis(self) -> Basis:
        """The basis this dimension is expressed in."""
        return self.vector.basis

    @property
    def value(self) -> Vector:
        """Backward compatibility: the dimensional vector.

        This is equivalent to .vector but matches the old Enum API.
        """
        return self.vector

    @property
    def is_pseudo(self) -> bool:
        """True if this is a pseudo-dimension (tagged, dimensionless vector)."""
        return self.tag is not None

    @property
    def is_dimensionless(self) -> bool:
        """True if the underlying vector is dimensionless."""
        return self.vector.is_dimensionless()

    def is_base(self) -> bool:
        """True if this is a base dimension (single component with exponent 1)."""
        non_zero = [exp for exp in self.vector.components if exp != 0]
        return len(non_zero) == 1 and non_zero[0] == 1

    def base_expansion(self) -> dict["Dimension", Fraction]:
        """Express this dimension as a product of base dimensions.

        Returns
        -------
        dict[Dimension, Fraction]
            Mapping from base dimensions to their exponents.

        Examples
        --------
        >>> VELOCITY.base_expansion()
        {LENGTH: 1, TIME: -1}
        """
        result: dict[Dimension, Fraction] = {}

        # For pseudo-dimensions, return empty dict
        if self.is_pseudo:
            return result

        # Build map from component index to base dimension
        base_dims = basis()

        for i, exp in enumerate(self.vector.components):
            if exp != 0:
                result[base_dims[i]] = exp

        return result

    # -------------------------------------------------------------------------
    # Algebra
    # -------------------------------------------------------------------------

    def __mul__(self, other: "Dimension") -> "Dimension":
        """Multiply dimensions (add exponent vectors).

        NONE acts as identity: NONE * X = X and X * NONE = X.
        Pseudo-dimensions behave like NONE in algebraic combinations:
        - MASS * COUNT = MASS (count adds zero to the vector)
        - ANGLE * LENGTH = LENGTH
        But pseudo-dimensions preserve themselves when alone:
        - ANGLE * NONE = ANGLE
        """
        if not isinstance(other, Dimension):
            return NotImplemented

        cache_key = (id(self), id(other))
        cached = _DIM_MUL_CACHE.get(cache_key)
        if cached is not None:
            return cached

        # Identity: NONE * X = X (before basis check — NONE is universal identity)
        if self == NONE:
            result = other
        # Identity: X * NONE = X
        elif other == NONE:
            result = self
        elif self.vector.basis != other.vector.basis:
            raise ValueError(
                f"Cannot multiply dimensions from different bases: "
                f"'{self.vector.basis.name}' and '{other.vector.basis.name}'"
            )
        # Pseudo-dimension combined with pseudo-dimension
        elif self.is_pseudo and other.is_pseudo:
            # Same pseudo-dimension: return self
            if self == other:
                result = self
            else:
                # Different pseudo-dimensions can't combine
                raise TypeError(
                    f"Cannot multiply different pseudo-dimensions: {self.name} and {other.name}"
                )
        # Pseudo-dimension combined with regular dimension:
        # The pseudo-dimension acts like NONE (zero vector)
        elif self.is_pseudo:
            result = other  # ANGLE * MASS = MASS
        elif other.is_pseudo:
            result = self   # MASS * ANGLE = MASS
        else:
            new_vector = self.vector * other.vector
            result = resolve(new_vector)

        _DIM_MUL_CACHE[cache_key] = result
        return result

    def __truediv__(self, other: "Dimension") -> "Dimension":
        """Divide dimensions (subtract exponent vectors).

        NONE acts as identity: X / NONE = X.
        Pseudo-dimensions behave like NONE in algebraic combinations:
        - MASS / COUNT = MASS (count subtracts zero from the vector)
        - LENGTH / ANGLE = LENGTH
        But self-division returns NONE:
        - ANGLE / ANGLE = NONE (not ANGLE, since exponent becomes 0)
        """
        if not isinstance(other, Dimension):
            return NotImplemented

        cache_key = (id(self), id(other))
        cached = _DIM_DIV_CACHE.get(cache_key)
        if cached is not None:
            return cached

        # Identity: X / NONE = X (before basis check — NONE is universal identity)
        if other == NONE:
            result = self
        elif self.vector.basis != other.vector.basis:
            raise ValueError(
                f"Cannot divide dimensions from different bases: "
                f"'{self.vector.basis.name}' and '{other.vector.basis.name}'"
            )
        # Pseudo-dimension divided by pseudo-dimension
        elif self.is_pseudo and other.is_pseudo:
            # Same pseudo-dimension: returns NONE (0/0 case, but semantically X/X = 1)
            if self == other:
                result = NONE
            else:
                # Different pseudo-dimensions can't divide
                raise TypeError(
                    f"Cannot divide different pseudo-dimensions: {self.name} and {other.name}"
                )
        # Regular divided by pseudo: pseudo acts like NONE
        elif other.is_pseudo:
            result = self   # MASS / ANGLE = MASS
        # Pseudo divided by regular: pseudo acts like NONE
        elif self.is_pseudo:
            result = resolve(self.vector / other.vector)
        else:
            new_vector = self.vector / other.vector
            result = resolve(new_vector)

        _DIM_DIV_CACHE[cache_key] = result
        return result

    def __pow__(self, power: int | float | Fraction) -> "Dimension":
        """Raise dimension to a power (multiply exponent vector by scalar).

        Pseudo-dimensions behave like dimensionless for exponentiation:
        - ANGLE ** 2 = ANGLE (angle^2 is still angle semantically)
        - COUNT ** -1 = COUNT (per-count is still count semantically)
        """
        if power == 1:
            return self
        if power == 0:
            return NONE

        cache_key = (id(self), power)
        cached = _DIM_POW_CACHE.get(cache_key)
        if cached is not None:
            return cached

        # Pseudo-dimensions are invariant under exponentiation
        # This allows expressions like mg/ea (COUNT ** -1) to work
        if self.is_pseudo:
            result = self
        else:
            new_vector = self.vector ** power
            result = resolve(new_vector)

        _DIM_POW_CACHE[cache_key] = result
        return result

    # -------------------------------------------------------------------------
    # Comparison & Hashing
    # -------------------------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        """Compare dimensions for equality.

        Pseudo-dimensions compare by tag, not just vector.
        Regular dimensions compare by vector.
        """
        if not isinstance(other, Dimension):
            return NotImplemented

        # Different bases are never equal
        if self.vector.basis != other.vector.basis:
            return False

        # Pseudo-dimensions: compare by tag
        if self.is_pseudo or other.is_pseudo:
            return self.tag == other.tag and self.vector == other.vector

        # Regular dimensions: compare by vector
        return self.vector == other.vector

    def __hash__(self) -> int:
        """Hash based on vector and tag for pseudo-dimensions."""
        return self._hash_cache

    def __bool__(self) -> bool:
        """False for NONE (dimensionless with no tag), True otherwise."""
        return self.tag is not None or not self.is_dimensionless

    # -------------------------------------------------------------------------
    # Representation
    # -------------------------------------------------------------------------

    def __repr__(self) -> str:
        if self.name:
            return f"Dimension({self.name})"
        return f"Dimension({self.vector!r})"


# -----------------------------------------------------------------------------
# Standard Dimensions (Module Constants)
# -----------------------------------------------------------------------------


def _vec(*components: int | Fraction) -> Vector:
    """Shorthand for creating an SI vector with 8 components."""
    # Pad with zeros if needed
    padded = list(components) + [0] * (8 - len(components))
    return Vector(SI, tuple(padded))


def _dim(name: str, *components: int | Fraction, symbol: str | None = None) -> Dimension:
    """Create and register a standard dimension."""
    vec = _vec(*components)
    dim = Dimension(vector=vec, name=name, symbol=symbol)
    _register(dim)
    _register_attr(dim)
    return dim


# Dimensionless (NONE)
NONE = _dim("none")

# 8 Base dimensions (T, L, M, I, Θ, J, N, B)
TIME = _dim("time", 1, 0, 0, 0, 0, 0, 0, 0, symbol="T")
LENGTH = _dim("length", 0, 1, 0, 0, 0, 0, 0, 0, symbol="L")
MASS = _dim("mass", 0, 0, 1, 0, 0, 0, 0, 0, symbol="M")
CURRENT = _dim("current", 0, 0, 0, 1, 0, 0, 0, 0, symbol="I")
TEMPERATURE = _dim("temperature", 0, 0, 0, 0, 1, 0, 0, 0, symbol="Θ")
LUMINOUS_INTENSITY = _dim("luminous_intensity", 0, 0, 0, 0, 0, 1, 0, 0, symbol="J")
AMOUNT_OF_SUBSTANCE = _dim("amount_of_substance", 0, 0, 0, 0, 0, 0, 1, 0, symbol="N")
INFORMATION = _dim("information", 0, 0, 0, 0, 0, 0, 0, 1, symbol="B")

# 4 Pseudo-dimensions
ANGLE = _register_attr(Dimension.pseudo("angle", name="angle", symbol="θ"))
SOLID_ANGLE = _register_attr(Dimension.pseudo("solid_angle", name="solid_angle", symbol="Ω"))
RATIO = _register_attr(Dimension.pseudo("ratio", name="ratio"))
COUNT = _register_attr(Dimension.pseudo("count", name="count"))

# Derived dimensions
# Mechanics
VELOCITY = _dim("velocity", -1, 1, 0, 0, 0, 0, 0, 0)  # L/T
ACCELERATION = _dim("acceleration", -2, 1, 0, 0, 0, 0, 0, 0)  # L/T²
FORCE = _dim("force", -2, 1, 1, 0, 0, 0, 0, 0)  # M·L/T²
ENERGY = _dim("energy", -2, 2, 1, 0, 0, 0, 0, 0)  # M·L²/T²
POWER = _dim("power", -3, 2, 1, 0, 0, 0, 0, 0)  # M·L²/T³
MOMENTUM = _dim("momentum", -1, 1, 1, 0, 0, 0, 0, 0)  # M·L/T
ANGULAR_MOMENTUM = _dim("angular_momentum", -1, 2, 1, 0, 0, 0, 0, 0)  # M·L²/T
AREA = _dim("area", 0, 2, 0, 0, 0, 0, 0, 0)  # L²
VOLUME = _dim("volume", 0, 3, 0, 0, 0, 0, 0, 0)  # L³
DENSITY = _dim("density", 0, -3, 1, 0, 0, 0, 0, 0)  # M/L³
LINEAR_DENSITY = _dim("linear_density", 0, -1, 1, 0, 0, 0, 0, 0)  # M/L
PRESSURE = _dim("pressure", -2, -1, 1, 0, 0, 0, 0, 0)  # M/(L·T²)
FREQUENCY = _dim("frequency", -1, 0, 0, 0, 0, 0, 0, 0)  # 1/T
DYNAMIC_VISCOSITY = _dim("dynamic_viscosity", -1, -1, 1, 0, 0, 0, 0, 0)  # M/(L·T)
KINEMATIC_VISCOSITY = _dim("kinematic_viscosity", -1, 2, 0, 0, 0, 0, 0, 0)  # L²/T
GRAVITATION = _dim("gravitation", -2, 3, -1, 0, 0, 0, 0, 0)  # L³/(M·T²)

# Electromagnetism
CHARGE = _dim("charge", 1, 0, 0, 1, 0, 0, 0, 0)  # I·T
VOLTAGE = _dim("voltage", -3, 2, 1, -1, 0, 0, 0, 0)  # M·L²/(T³·I)
RESISTANCE = _dim("resistance", -3, 2, 1, -2, 0, 0, 0, 0)  # M·L²/(T³·I²)
RESISTIVITY = _dim("resistivity", -3, 3, 1, -2, 0, 0, 0, 0)  # M·L³/(T³·I²)
CONDUCTANCE = _dim("conductance", 3, -2, -1, 2, 0, 0, 0, 0)  # T³·I²/(M·L²)
CONDUCTIVITY = _dim("conductivity", 3, -3, -1, 2, 0, 0, 0, 0)  # T³·I²/(M·L³)
CAPACITANCE = _dim("capacitance", 4, -2, -1, 2, 0, 0, 0, 0)  # T⁴·I²/(M·L²)
INDUCTANCE = _dim("inductance", -2, 2, 1, -2, 0, 0, 0, 0)  # M·L²/(T²·I²)
MAGNETIC_FLUX = _dim("magnetic_flux", -2, 2, 1, -1, 0, 0, 0, 0)  # M·L²/(T²·I)
MAGNETIC_FLUX_DENSITY = _dim("magnetic_flux_density", -2, 0, 1, -1, 0, 0, 0, 0)  # M/(T²·I)
MAGNETIC_PERMEABILITY = _dim("magnetic_permeability", -2, 1, 1, -2, 0, 0, 0, 0)  # M·L/(T²·I²)
PERMITTIVITY = _dim("permittivity", 4, -3, -1, 2, 0, 0, 0, 0)  # T⁴·I²/(M·L³)
ELECTRIC_FIELD_STRENGTH = _dim("electric_field_strength", -3, 1, 1, -1, 0, 0, 0, 0)  # M·L/(T³·I)
MAGNETIC_FIELD_STRENGTH = _dim("magnetic_field_strength", 0, -1, 0, 1, 0, 0, 0, 0)  # I/L

# Thermodynamics
ENTROPY = _dim("entropy", -2, 2, 1, 0, -1, 0, 0, 0)  # M·L²/(T²·Θ)
SPECIFIC_HEAT_CAPACITY = _dim("specific_heat_capacity", -2, 2, 0, 0, -1, 0, 0, 0)  # L²/(T²·Θ)
THERMAL_CONDUCTIVITY = _dim("thermal_conductivity", -3, 1, 1, 0, -1, 0, 0, 0)  # M·L/(T³·Θ)

# Photometry
ILLUMINANCE = _dim("illuminance", 0, -2, 0, 0, 0, 1, 0, 0)  # J/L²

# Chemistry
CATALYTIC_ACTIVITY = _dim("catalytic_activity", -1, 0, 0, 0, 0, 0, 1, 0)  # N/T
MOLAR_MASS = _dim("molar_mass", 0, 0, 1, 0, 0, 0, -1, 0)  # M/N
MOLAR_VOLUME = _dim("molar_volume", 0, 3, 0, 0, 0, 0, -1, 0)  # L³/N
CONCENTRATION = _dim("concentration", 0, -3, 0, 0, 0, 0, 1, 0)  # N/L³

# Spectroscopy / Radiation
WAVENUMBER = _dim("wavenumber", 0, -1, 0, 0, 0, 0, 0, 0)  # 1/L
RADIANT_EXPOSURE = _dim("radiant_exposure", -2, 0, 1, 0, 0, 0, 0, 0)  # M/T²
EXPOSURE = _dim("exposure", 1, 0, -1, 1, 0, 0, 0, 0)  # I·T/M (radiation exposure, C/kg)

# Electromagnetism (derived)
ELECTRIC_DIPOLE_MOMENT = _dim("electric_dipole_moment", 1, 1, 0, 1, 0, 0, 0, 0)  # I·T·L


# -----------------------------------------------------------------------------
# CGS Dimensions (Centimetre-Gram-Second)
# -----------------------------------------------------------------------------

from ucon.basis.builtin import CGS  # noqa: E402


def _cgs_vec(*components: int | Fraction) -> Vector:
    """Shorthand for creating a CGS vector with 3 components (L, M, T)."""
    padded = list(components) + [0] * (3 - len(components))
    return Vector(CGS, tuple(padded))


def _cgs_dim(name: str, *components: int | Fraction, symbol: str | None = None) -> Dimension:
    """Create and register a standard CGS dimension."""
    vec = _cgs_vec(*components)
    dim = Dimension(vector=vec, name=name, symbol=symbol)
    _register(dim)
    _register_attr(dim)
    return dim


# CGS base dimensions
CGS_NONE = _cgs_dim("cgs_none")
CGS_LENGTH = _cgs_dim("cgs_length", 1, 0, 0)
CGS_MASS = _cgs_dim("cgs_mass", 0, 1, 0)
CGS_TIME = _cgs_dim("cgs_time", 0, 0, 1)

# CGS derived dimensions
CGS_VELOCITY = _cgs_dim("cgs_velocity", 1, 0, -1)  # L/T
CGS_FORCE = _cgs_dim("cgs_force", 1, 1, -2)  # M·L/T² (dyne)
CGS_ENERGY = _cgs_dim("cgs_energy", 2, 1, -2)  # M·L²/T² (erg)
CGS_PRESSURE = _cgs_dim("cgs_pressure", -1, 1, -2)  # M/(L·T²) (barye)
CGS_DYNAMIC_VISCOSITY = _cgs_dim("cgs_dynamic_viscosity", -1, 1, -1)  # M/(L·T) (poise)
CGS_KINEMATIC_VISCOSITY = _cgs_dim("cgs_kinematic_viscosity", 2, 0, -1)  # L²/T (stokes)
CGS_ACCELERATION = _cgs_dim("cgs_acceleration", 1, 0, -2)  # L/T² (galileo)
CGS_WAVENUMBER = _cgs_dim("cgs_wavenumber", -1, 0, 0)  # 1/L (kayser)
CGS_RADIANT_EXPOSURE = _cgs_dim("cgs_radiant_exposure", 0, 1, -2)  # M/T² (langley)


# -----------------------------------------------------------------------------
# CGS-ESU Dimensions (Electrostatic Units)
# -----------------------------------------------------------------------------

from ucon.basis.builtin import CGS_ESU  # noqa: E402


def _cgs_esu_vec(*components: int | Fraction) -> Vector:
    """Shorthand for creating a CGS-ESU vector with 4 components (L, M, T, Q)."""
    padded = list(components) + [0] * (4 - len(components))
    return Vector(CGS_ESU, tuple(padded))


def _cgs_esu_dim(name: str, *components: int | Fraction, symbol: str | None = None) -> Dimension:
    """Create and register a standard CGS-ESU dimension."""
    vec = _cgs_esu_vec(*components)
    dim = Dimension(vector=vec, name=name, symbol=symbol)
    _register(dim)
    _register_attr(dim)
    return dim


# CGS-ESU electromagnetic dimensions
# In CGS-ESU, charge is derived: [q] = M^(1/2)·L^(3/2)·T^(-1) (from Coulomb's law with k=1)
CGS_ESU_CHARGE = _cgs_esu_dim(
    "cgs_esu_charge",
    Fraction(3, 2), Fraction(1, 2), Fraction(-1), Fraction(0),
)  # statcoulomb
CGS_ESU_CURRENT = _cgs_esu_dim(
    "cgs_esu_current",
    Fraction(3, 2), Fraction(1, 2), Fraction(-2), Fraction(0),
)  # statampere = charge/time
CGS_ESU_VOLTAGE = _cgs_esu_dim(
    "cgs_esu_voltage",
    Fraction(1, 2), Fraction(1, 2), Fraction(-1), Fraction(0),
)  # statvolt = erg/statcoulomb
CGS_ESU_RESISTANCE = _cgs_esu_dim(
    "cgs_esu_resistance",
    Fraction(-1), Fraction(0), Fraction(1), Fraction(0),
)  # statohm = s/cm
CGS_ESU_CAPACITANCE = _cgs_esu_dim(
    "cgs_esu_capacitance",
    Fraction(1), Fraction(0), Fraction(0), Fraction(0),
)  # statfarad = cm
CGS_ESU_MAGNETIC_FLUX_DENSITY = _cgs_esu_dim(
    "cgs_esu_magnetic_flux_density",
    Fraction(-3, 2), Fraction(1, 2), Fraction(0), Fraction(0),
)  # gauss: L^(-3/2)·M^(1/2) (from SI_TO_CGS_ESU applied to M/(T²·I))
CGS_ESU_MAGNETIC_FLUX = _cgs_esu_dim(
    "cgs_esu_magnetic_flux",
    Fraction(1, 2), Fraction(1, 2), Fraction(0), Fraction(0),
)  # maxwell: L^(1/2)·M^(1/2) (from SI_TO_CGS_ESU applied to M·L²/(T²·I))
CGS_ESU_MAGNETIC_FIELD_STRENGTH = _cgs_esu_dim(
    "cgs_esu_magnetic_field_strength",
    Fraction(1, 2), Fraction(1, 2), Fraction(-2), Fraction(0),
)  # oersted: L^(1/2)·M^(1/2)·T^(-2) (from SI_TO_CGS_ESU applied to I/L)
CGS_ESU_ELECTRIC_DIPOLE_MOMENT = _cgs_esu_dim(
    "cgs_esu_electric_dipole_moment",
    Fraction(5, 2), Fraction(1, 2), Fraction(-1), Fraction(0),
)  # debye: charge·length = L^(5/2)·M^(1/2)·T^(-1)


# -----------------------------------------------------------------------------
# CGS-EMU Dimensions (Electromagnetic Units, using CGS basis with fractional exponents)
# -----------------------------------------------------------------------------
# CGS-EMU differs from CGS-ESU in how current maps from SI:
#   CGS-ESU: I → L^(3/2)·M^(1/2)·T^(-2)
#   CGS-EMU: I → L^(1/2)·M^(1/2)·T^(-1)
# CGS-EMU dimensions share the CGS basis (L, M, T) but with fractional exponents
# for electromagnetic quantities. Some vectors collide with CGS mechanical dims
# (e.g., CGS_EMU_RESISTANCE = L·T^(-1) = CGS_VELOCITY), so we skip _register()
# to avoid overwriting the vector registry.


def _cgs_emu_dim(name: str, *components: int | Fraction, symbol: str | None = None) -> Dimension:
    """Create a CGS-EMU dimension. Skips _register() to avoid vector collisions
    with CGS mechanical dimensions that share the same vector (KOQ collision)."""
    vec = _cgs_vec(*components)
    dim = Dimension(vector=vec, name=name, symbol=symbol)
    # Skip _register(dim) — CGS-EMU electromagnetic dims share vectors
    # with CGS mechanical dims. Only register for attribute access.
    _register_attr(dim)
    return dim


CGS_EMU_CURRENT = _cgs_emu_dim(
    "cgs_emu_current",
    Fraction(1, 2), Fraction(1, 2), Fraction(-1),
)  # biot/abampere: L^(1/2)·M^(1/2)·T^(-1)
CGS_EMU_CHARGE = _cgs_emu_dim(
    "cgs_emu_charge",
    Fraction(1, 2), Fraction(1, 2), Fraction(0),
)  # abcoulomb: L^(1/2)·M^(1/2)
CGS_EMU_VOLTAGE = _cgs_emu_dim(
    "cgs_emu_voltage",
    Fraction(3, 2), Fraction(1, 2), Fraction(-2),
)  # abvolt: L^(3/2)·M^(1/2)·T^(-2)
CGS_EMU_RESISTANCE = _cgs_emu_dim(
    "cgs_emu_resistance",
    Fraction(1), Fraction(0), Fraction(-1),
)  # abohm: L·T^(-1)
CGS_EMU_CAPACITANCE = _cgs_emu_dim(
    "cgs_emu_capacitance",
    Fraction(-1), Fraction(0), Fraction(2),
)  # abfarad: T^2/L
CGS_EMU_INDUCTANCE = _cgs_emu_dim(
    "cgs_emu_inductance",
    Fraction(1), Fraction(0), Fraction(0),
)  # abhenry: L


# -----------------------------------------------------------------------------
# Natural-unit dimensions (1D basis: energy)
# -----------------------------------------------------------------------------

from ucon.basis.builtin import NATURAL  # noqa: E402


def _natural_vec(*components: int | Fraction) -> Vector:
    padded = list(components) + [0] * (1 - len(components))
    return Vector(NATURAL, tuple(padded))


def _natural_dim(name: str, *components: int | Fraction, symbol: str | None = None) -> Dimension:
    vec = _natural_vec(*components)
    dim = Dimension(vector=vec, name=name, symbol=symbol)
    _register(dim)
    _register_attr(dim)
    return dim


NATURAL_ENERGY = _natural_dim("natural_energy", 1)


def basis() -> tuple[Dimension, ...]:
    """Return the 8 SI base dimensions in canonical order."""
    return (
        TIME,
        LENGTH,
        MASS,
        CURRENT,
        TEMPERATURE,
        LUMINOUS_INTENSITY,
        AMOUNT_OF_SUBSTANCE,
        INFORMATION,
    )


def all_dimensions() -> tuple[Dimension, ...]:
    """Return all standard dimensions (base, derived, and pseudo).

    This is useful for iteration when you need to list all known dimensions.
    """
    return (
        # Dimensionless
        NONE,
        # Base
        TIME,
        LENGTH,
        MASS,
        CURRENT,
        TEMPERATURE,
        LUMINOUS_INTENSITY,
        AMOUNT_OF_SUBSTANCE,
        INFORMATION,
        # Pseudo
        ANGLE,
        SOLID_ANGLE,
        RATIO,
        COUNT,
        # Derived - Mechanics
        VELOCITY,
        ACCELERATION,
        FORCE,
        ENERGY,
        POWER,
        MOMENTUM,
        ANGULAR_MOMENTUM,
        AREA,
        VOLUME,
        DENSITY,
        LINEAR_DENSITY,
        PRESSURE,
        FREQUENCY,
        DYNAMIC_VISCOSITY,
        KINEMATIC_VISCOSITY,
        GRAVITATION,
        # Derived - Electromagnetism
        CHARGE,
        VOLTAGE,
        RESISTANCE,
        RESISTIVITY,
        CONDUCTANCE,
        CONDUCTIVITY,
        CAPACITANCE,
        INDUCTANCE,
        MAGNETIC_FLUX,
        MAGNETIC_FLUX_DENSITY,
        MAGNETIC_PERMEABILITY,
        PERMITTIVITY,
        ELECTRIC_FIELD_STRENGTH,
        MAGNETIC_FIELD_STRENGTH,
        # Derived - Thermodynamics
        ENTROPY,
        SPECIFIC_HEAT_CAPACITY,
        THERMAL_CONDUCTIVITY,
        # Derived - Photometry
        ILLUMINANCE,
        # Derived - Chemistry
        CATALYTIC_ACTIVITY,
        MOLAR_MASS,
        MOLAR_VOLUME,
        CONCENTRATION,
        # Derived - Spectroscopy / Radiation
        WAVENUMBER,
        RADIANT_EXPOSURE,
        EXPOSURE,
        # Derived - Electromagnetism (additional)
        ELECTRIC_DIPOLE_MOMENT,
        # CGS dimensions
        CGS_NONE,
        CGS_LENGTH,
        CGS_MASS,
        CGS_TIME,
        CGS_VELOCITY,
        CGS_FORCE,
        CGS_ENERGY,
        CGS_PRESSURE,
        CGS_DYNAMIC_VISCOSITY,
        CGS_KINEMATIC_VISCOSITY,
        CGS_ACCELERATION,
        CGS_WAVENUMBER,
        CGS_RADIANT_EXPOSURE,
        # CGS-ESU dimensions
        CGS_ESU_CHARGE,
        CGS_ESU_CURRENT,
        CGS_ESU_VOLTAGE,
        CGS_ESU_RESISTANCE,
        CGS_ESU_CAPACITANCE,
        CGS_ESU_MAGNETIC_FLUX_DENSITY,
        CGS_ESU_MAGNETIC_FLUX,
        CGS_ESU_MAGNETIC_FIELD_STRENGTH,
        CGS_ESU_ELECTRIC_DIPOLE_MOMENT,
        # CGS-EMU dimensions
        CGS_EMU_CURRENT,
        CGS_EMU_CHARGE,
        CGS_EMU_VOLTAGE,
        CGS_EMU_RESISTANCE,
        CGS_EMU_CAPACITANCE,
        CGS_EMU_INDUCTANCE,
        # Natural-unit dimensions
        NATURAL_ENERGY,
    )


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------

__all__ = [
    # Core class
    "Dimension",
    # Functions
    "resolve",
    "basis",
    "all_dimensions",
    # Standard basis
    "SI",
    # Dimensionless
    "NONE",
    # Base dimensions
    "TIME",
    "LENGTH",
    "MASS",
    "CURRENT",
    "TEMPERATURE",
    "LUMINOUS_INTENSITY",
    "AMOUNT_OF_SUBSTANCE",
    "INFORMATION",
    # Pseudo-dimensions
    "ANGLE",
    "SOLID_ANGLE",
    "RATIO",
    "COUNT",
    # Derived dimensions - Mechanics
    "VELOCITY",
    "ACCELERATION",
    "FORCE",
    "ENERGY",
    "POWER",
    "MOMENTUM",
    "ANGULAR_MOMENTUM",
    "AREA",
    "VOLUME",
    "DENSITY",
    "LINEAR_DENSITY",
    "PRESSURE",
    "FREQUENCY",
    "DYNAMIC_VISCOSITY",
    "KINEMATIC_VISCOSITY",
    "GRAVITATION",
    # Derived dimensions - Electromagnetism
    "CHARGE",
    "VOLTAGE",
    "RESISTANCE",
    "RESISTIVITY",
    "CONDUCTANCE",
    "CONDUCTIVITY",
    "CAPACITANCE",
    "INDUCTANCE",
    "MAGNETIC_FLUX",
    "MAGNETIC_FLUX_DENSITY",
    "MAGNETIC_PERMEABILITY",
    "PERMITTIVITY",
    "ELECTRIC_FIELD_STRENGTH",
    "MAGNETIC_FIELD_STRENGTH",
    # Derived dimensions - Thermodynamics
    "ENTROPY",
    "SPECIFIC_HEAT_CAPACITY",
    "THERMAL_CONDUCTIVITY",
    # Derived dimensions - Photometry
    "ILLUMINANCE",
    # Derived dimensions - Chemistry
    "CATALYTIC_ACTIVITY",
    "MOLAR_MASS",
    "MOLAR_VOLUME",
    "CONCENTRATION",
    # Derived dimensions - Spectroscopy / Radiation
    "WAVENUMBER",
    "RADIANT_EXPOSURE",
    "EXPOSURE",
    # Derived dimensions - Electromagnetism (additional)
    "ELECTRIC_DIPOLE_MOMENT",
    # CGS dimensions
    "CGS_NONE",
    "CGS_LENGTH",
    "CGS_MASS",
    "CGS_TIME",
    "CGS_VELOCITY",
    "CGS_FORCE",
    "CGS_ENERGY",
    "CGS_PRESSURE",
    "CGS_DYNAMIC_VISCOSITY",
    "CGS_KINEMATIC_VISCOSITY",
    "CGS_ACCELERATION",
    "CGS_WAVENUMBER",
    "CGS_RADIANT_EXPOSURE",
    # CGS-ESU dimensions
    "CGS_ESU_CHARGE",
    "CGS_ESU_CURRENT",
    "CGS_ESU_VOLTAGE",
    "CGS_ESU_RESISTANCE",
    "CGS_ESU_CAPACITANCE",
    "CGS_ESU_MAGNETIC_FLUX_DENSITY",
    "CGS_ESU_MAGNETIC_FLUX",
    "CGS_ESU_MAGNETIC_FIELD_STRENGTH",
    "CGS_ESU_ELECTRIC_DIPOLE_MOMENT",
    # CGS-EMU dimensions
    "CGS_EMU_CURRENT",
    "CGS_EMU_CHARGE",
    "CGS_EMU_VOLTAGE",
    "CGS_EMU_RESISTANCE",
    "CGS_EMU_CAPACITANCE",
    "CGS_EMU_INDUCTANCE",
    # Natural-unit dimensions
    "NATURAL_ENERGY",
]
