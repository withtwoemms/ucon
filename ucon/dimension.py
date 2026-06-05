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

from ucon.basis import Basis, BasisComponent, Vector
from ucon.basis.builtin import ATOMIC, CGS, CGS_EMU, CGS_ESU, NATURAL, PLANCK, SI
from ucon.basis.ops import divide_via, multiply_via
from ucon._active import resolve_basis
from ucon._algebra_cache import _get_active_cache

if TYPE_CHECKING:
    from ucon.basis import BasisTransform


# -----------------------------------------------------------------------------
# Registry for dimension resolution
# -----------------------------------------------------------------------------

_REGISTRY: dict[Vector, "Dimension"] = {}


def _algebra_cache():
    """Resolve the per-system :class:`AlgebraCache` for dimension algebra."""
    return _get_active_cache()


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
            basis = resolve_basis(fallback=SI)

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
            basis = resolve_basis(fallback=SI)
        if name is None:
            name = tag

        vector = Vector.zero(basis)
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

        cache = _algebra_cache().mul
        cache_key = (self, other)
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        # Identity: NONE * X = X (before basis check — NONE is universal identity)
        if self == NONE:
            result = other
        # Identity: X * NONE = X
        elif other == NONE:
            result = self
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
            # ``Vector`` arithmetic is strict same-basis (raises
            # ``BasisMismatch``). ``ops.multiply_via`` short-circuits to that
            # path when both vectors share a basis and otherwise consults
            # the active ``BasisGraph`` for a clean (non-lossy) projection.
            new_vector = multiply_via(self.vector, other.vector)
            result = resolve(new_vector)

        cache[cache_key] = result
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

        cache = _algebra_cache().div
        cache_key = (self, other)
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        # Identity: X / NONE = X (before basis check — NONE is universal identity)
        if other == NONE:
            result = self
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
            result = resolve(divide_via(self.vector, other.vector))
        else:
            # See ``__mul__`` for the rationale on routing through ``ops``.
            new_vector = divide_via(self.vector, other.vector)
            result = resolve(new_vector)

        cache[cache_key] = result
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

        cache = _algebra_cache().pow
        cache_key = (self, power)
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        # Pseudo-dimensions are invariant under exponentiation
        # This allows expressions like mg/ea (COUNT ** -1) to work
        if self.is_pseudo:
            result = self
        else:
            new_vector = self.vector ** power
            result = resolve(new_vector)

        cache[cache_key] = result
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


def _build_standard_dimensions() -> tuple[
    dict[str, "Dimension"],
    dict[Vector, "Dimension"],
]:
    """Construct the full catalog of standard named ``Dimension`` objects.

    Returns
    -------
    (attrs, registry)
        ``attrs`` maps name -> Dimension (powers ``Dimension.length`` access
        and ``_DIMENSION_ATTRS`` lookup). ``registry`` maps vector -> Dimension
        (powers ``resolve(vector)``). Pseudo-dimensions land in ``attrs`` but
        not in ``registry`` (they share the zero vector and are tag-isolated).

    Notes
    -----
    This function is pure: it neither reads from nor writes to module-level
    state. The caller is responsible for seeding ``_REGISTRY`` and
    ``_DIMENSION_ATTRS`` from the returned dicts. The returned catalog is
    also the canonical source for the module-level ``LENGTH``/``MASS``/...
    constants below.
    """
    attrs: dict[str, "Dimension"] = {}
    registry: dict[Vector, "Dimension"] = {}

    def _make(
        basis_obj: Basis,
        dim_count: int,
        name: str,
        *components: int | Fraction,
        symbol: str | None = None,
    ) -> "Dimension":
        padded = list(components) + [0] * (dim_count - len(components))
        vec = Vector(basis_obj, tuple(padded))
        dim = Dimension(vector=vec, name=name, symbol=symbol)
        attrs[name] = dim
        registry[vec] = dim
        return dim

    def _pseudo(
        tag: str,
        *,
        name: str,
        symbol: str | None = None,
    ) -> "Dimension":
        dim = Dimension.pseudo(tag, name=name, symbol=symbol)
        attrs[name] = dim
        return dim

    # SI: dimensionless
    _make(SI, 8, "none")

    # SI: 8 base dimensions (T, L, M, I, Θ, J, N, B)
    _make(SI, 8, "time", 1, 0, 0, 0, 0, 0, 0, 0, symbol="T")
    _make(SI, 8, "length", 0, 1, 0, 0, 0, 0, 0, 0, symbol="L")
    _make(SI, 8, "mass", 0, 0, 1, 0, 0, 0, 0, 0, symbol="M")
    _make(SI, 8, "current", 0, 0, 0, 1, 0, 0, 0, 0, symbol="I")
    _make(SI, 8, "temperature", 0, 0, 0, 0, 1, 0, 0, 0, symbol="Θ")
    _make(SI, 8, "luminous_intensity", 0, 0, 0, 0, 0, 1, 0, 0, symbol="J")
    _make(SI, 8, "amount_of_substance", 0, 0, 0, 0, 0, 0, 1, 0, symbol="N")
    _make(SI, 8, "information", 0, 0, 0, 0, 0, 0, 0, 1, symbol="B")

    # SI: 4 pseudo-dimensions
    _pseudo("angle", name="angle", symbol="θ")
    _pseudo("solid_angle", name="solid_angle", symbol="Ω")
    _pseudo("ratio", name="ratio")
    _pseudo("count", name="count")

    # SI: derived - mechanics
    _make(SI, 8, "velocity", -1, 1, 0, 0, 0, 0, 0, 0)
    _make(SI, 8, "acceleration", -2, 1, 0, 0, 0, 0, 0, 0)
    _make(SI, 8, "force", -2, 1, 1, 0, 0, 0, 0, 0)
    _make(SI, 8, "energy", -2, 2, 1, 0, 0, 0, 0, 0)
    _make(SI, 8, "power", -3, 2, 1, 0, 0, 0, 0, 0)
    _make(SI, 8, "momentum", -1, 1, 1, 0, 0, 0, 0, 0)
    _make(SI, 8, "angular_momentum", -1, 2, 1, 0, 0, 0, 0, 0)
    _make(SI, 8, "area", 0, 2, 0, 0, 0, 0, 0, 0)
    _make(SI, 8, "volume", 0, 3, 0, 0, 0, 0, 0, 0)
    _make(SI, 8, "density", 0, -3, 1, 0, 0, 0, 0, 0)
    _make(SI, 8, "linear_density", 0, -1, 1, 0, 0, 0, 0, 0)
    _make(SI, 8, "pressure", -2, -1, 1, 0, 0, 0, 0, 0)
    _make(SI, 8, "frequency", -1, 0, 0, 0, 0, 0, 0, 0)
    _make(SI, 8, "dynamic_viscosity", -1, -1, 1, 0, 0, 0, 0, 0)
    _make(SI, 8, "kinematic_viscosity", -1, 2, 0, 0, 0, 0, 0, 0)
    _make(SI, 8, "gravitation", -2, 3, -1, 0, 0, 0, 0, 0)

    # SI: derived - electromagnetism
    _make(SI, 8, "charge", 1, 0, 0, 1, 0, 0, 0, 0)
    _make(SI, 8, "voltage", -3, 2, 1, -1, 0, 0, 0, 0)
    _make(SI, 8, "resistance", -3, 2, 1, -2, 0, 0, 0, 0)
    _make(SI, 8, "resistivity", -3, 3, 1, -2, 0, 0, 0, 0)
    _make(SI, 8, "conductance", 3, -2, -1, 2, 0, 0, 0, 0)
    _make(SI, 8, "conductivity", 3, -3, -1, 2, 0, 0, 0, 0)
    _make(SI, 8, "capacitance", 4, -2, -1, 2, 0, 0, 0, 0)
    _make(SI, 8, "inductance", -2, 2, 1, -2, 0, 0, 0, 0)
    _make(SI, 8, "magnetic_flux", -2, 2, 1, -1, 0, 0, 0, 0)
    _make(SI, 8, "magnetic_flux_density", -2, 0, 1, -1, 0, 0, 0, 0)
    _make(SI, 8, "magnetic_permeability", -2, 1, 1, -2, 0, 0, 0, 0)
    _make(SI, 8, "permittivity", 4, -3, -1, 2, 0, 0, 0, 0)
    _make(SI, 8, "electric_field_strength", -3, 1, 1, -1, 0, 0, 0, 0)
    _make(SI, 8, "magnetic_field_strength", 0, -1, 0, 1, 0, 0, 0, 0)

    # SI: derived - thermodynamics
    _make(SI, 8, "entropy", -2, 2, 1, 0, -1, 0, 0, 0)
    _make(SI, 8, "specific_heat_capacity", -2, 2, 0, 0, -1, 0, 0, 0)
    _make(SI, 8, "thermal_conductivity", -3, 1, 1, 0, -1, 0, 0, 0)

    # SI: derived - photometry
    _make(SI, 8, "illuminance", 0, -2, 0, 0, 0, 1, 0, 0)
    _make(SI, 8, "luminous_efficacy", 3, -2, -1, 0, 0, 1, 0, 0)

    # SI: derived - chemistry
    _make(SI, 8, "catalytic_activity", -1, 0, 0, 0, 0, 0, 1, 0)
    _make(SI, 8, "molar_mass", 0, 0, 1, 0, 0, 0, -1, 0)
    _make(SI, 8, "molar_volume", 0, 3, 0, 0, 0, 0, -1, 0)
    _make(SI, 8, "molar_energy", -2, 2, 1, 0, 0, 0, -1, 0)
    _make(SI, 8, "molar_entropy", -2, 2, 1, 0, -1, 0, -1, 0)
    _make(SI, 8, "concentration", 0, -3, 0, 0, 0, 0, 1, 0)

    # SI: derived - specific quantities (per-mass)
    _make(SI, 8, "specific_energy", -2, 2, 0, 0, 0, 0, 0, 0)

    # SI: derived - spectroscopy / radiation
    _make(SI, 8, "wavenumber", 0, -1, 0, 0, 0, 0, 0, 0)
    _make(SI, 8, "radiant_exposure", -2, 0, 1, 0, 0, 0, 0, 0)
    _make(SI, 8, "exposure", 1, 0, -1, 1, 0, 0, 0, 0)

    # SI: derived - electromagnetism (additional)
    _make(SI, 8, "electric_dipole_moment", 1, 1, 0, 1, 0, 0, 0, 0)

    # CGS: base (3 components: L, M, T)
    _make(CGS, 3, "cgs_none")
    _make(CGS, 3, "cgs_length", 1, 0, 0)
    _make(CGS, 3, "cgs_mass", 0, 1, 0)
    _make(CGS, 3, "cgs_time", 0, 0, 1)

    # CGS: derived
    _make(CGS, 3, "cgs_velocity", 1, 0, -1)
    _make(CGS, 3, "cgs_force", 1, 1, -2)
    _make(CGS, 3, "cgs_energy", 2, 1, -2)
    _make(CGS, 3, "cgs_pressure", -1, 1, -2)
    _make(CGS, 3, "cgs_dynamic_viscosity", -1, 1, -1)
    _make(CGS, 3, "cgs_kinematic_viscosity", 2, 0, -1)
    _make(CGS, 3, "cgs_acceleration", 1, 0, -2)
    _make(CGS, 3, "cgs_wavenumber", -1, 0, 0)
    _make(CGS, 3, "cgs_radiant_exposure", 0, 1, -2)

    # CGS-ESU (4 components: L, M, T, Q)
    _make(CGS_ESU, 4, "cgs_esu_charge", 0, 0, 0, 1)
    _make(CGS_ESU, 4, "cgs_esu_current", 0, 0, -1, 1)
    _make(CGS_ESU, 4, "cgs_esu_voltage", 2, 1, -2, -1)
    _make(CGS_ESU, 4, "cgs_esu_resistance", 2, 1, -1, -2)
    _make(CGS_ESU, 4, "cgs_esu_capacitance", -2, -1, 2, 2)
    _make(CGS_ESU, 4, "cgs_esu_magnetic_flux_density", 0, 1, -1, -1)
    _make(CGS_ESU, 4, "cgs_esu_magnetic_flux", 2, 1, -1, -1)
    _make(CGS_ESU, 4, "cgs_esu_magnetic_field_strength", -1, 0, -1, 1)
    _make(CGS_ESU, 4, "cgs_esu_electric_dipole_moment", 1, 0, 0, 1)

    # CGS-EMU (4 components: L, M, T, Φ)
    _make(CGS_EMU, 4, "cgs_emu_current", 0, 0, 0, 1)
    _make(CGS_EMU, 4, "cgs_emu_charge", 0, 0, 1, 1)
    _make(CGS_EMU, 4, "cgs_emu_voltage", 2, 1, -3, -1)
    _make(CGS_EMU, 4, "cgs_emu_resistance", 2, 1, -3, -2)
    _make(CGS_EMU, 4, "cgs_emu_capacitance", -2, -1, 4, 2)
    _make(CGS_EMU, 4, "cgs_emu_inductance", 2, 1, -2, -2)

    # Natural (1 component: E)
    _make(NATURAL, 1, "natural_energy", 1)

    # Planck (1 component: E — energy ≡ mass ≡ temperature; length ≡ time)
    _make(PLANCK, 1, "planck_energy", 1)
    _make(PLANCK, 1, "planck_length", -1)

    # Atomic (1 component: E — energy ≡ mass; length ≡ time)
    _make(ATOMIC, 1, "atomic_energy", 1)
    _make(ATOMIC, 1, "atomic_length", -1)

    return attrs, registry


_STANDARD_ATTRS, _STANDARD_REGISTRY = _build_standard_dimensions()
_REGISTRY.update(_STANDARD_REGISTRY)
_DIMENSION_ATTRS.update(_STANDARD_ATTRS)


# Module-level constants resolved from the catalog. The .pyi stub mirrors
# these declarations so static analysis sees them; runtime values come from
# the builder's output dict.

# Dimensionless
NONE = _STANDARD_ATTRS["none"]

# 8 base dimensions
TIME = _STANDARD_ATTRS["time"]
LENGTH = _STANDARD_ATTRS["length"]
MASS = _STANDARD_ATTRS["mass"]
CURRENT = _STANDARD_ATTRS["current"]
TEMPERATURE = _STANDARD_ATTRS["temperature"]
LUMINOUS_INTENSITY = _STANDARD_ATTRS["luminous_intensity"]
AMOUNT_OF_SUBSTANCE = _STANDARD_ATTRS["amount_of_substance"]
INFORMATION = _STANDARD_ATTRS["information"]

# 4 pseudo-dimensions
ANGLE = _STANDARD_ATTRS["angle"]
SOLID_ANGLE = _STANDARD_ATTRS["solid_angle"]
RATIO = _STANDARD_ATTRS["ratio"]
COUNT = _STANDARD_ATTRS["count"]

# Derived: mechanics
VELOCITY = _STANDARD_ATTRS["velocity"]
ACCELERATION = _STANDARD_ATTRS["acceleration"]
FORCE = _STANDARD_ATTRS["force"]
ENERGY = _STANDARD_ATTRS["energy"]
POWER = _STANDARD_ATTRS["power"]
MOMENTUM = _STANDARD_ATTRS["momentum"]
ANGULAR_MOMENTUM = _STANDARD_ATTRS["angular_momentum"]
AREA = _STANDARD_ATTRS["area"]
VOLUME = _STANDARD_ATTRS["volume"]
DENSITY = _STANDARD_ATTRS["density"]
LINEAR_DENSITY = _STANDARD_ATTRS["linear_density"]
PRESSURE = _STANDARD_ATTRS["pressure"]
FREQUENCY = _STANDARD_ATTRS["frequency"]
DYNAMIC_VISCOSITY = _STANDARD_ATTRS["dynamic_viscosity"]
KINEMATIC_VISCOSITY = _STANDARD_ATTRS["kinematic_viscosity"]
GRAVITATION = _STANDARD_ATTRS["gravitation"]

# Derived: electromagnetism
CHARGE = _STANDARD_ATTRS["charge"]
VOLTAGE = _STANDARD_ATTRS["voltage"]
RESISTANCE = _STANDARD_ATTRS["resistance"]
RESISTIVITY = _STANDARD_ATTRS["resistivity"]
CONDUCTANCE = _STANDARD_ATTRS["conductance"]
CONDUCTIVITY = _STANDARD_ATTRS["conductivity"]
CAPACITANCE = _STANDARD_ATTRS["capacitance"]
INDUCTANCE = _STANDARD_ATTRS["inductance"]
MAGNETIC_FLUX = _STANDARD_ATTRS["magnetic_flux"]
MAGNETIC_FLUX_DENSITY = _STANDARD_ATTRS["magnetic_flux_density"]
MAGNETIC_PERMEABILITY = _STANDARD_ATTRS["magnetic_permeability"]
PERMITTIVITY = _STANDARD_ATTRS["permittivity"]
ELECTRIC_FIELD_STRENGTH = _STANDARD_ATTRS["electric_field_strength"]
MAGNETIC_FIELD_STRENGTH = _STANDARD_ATTRS["magnetic_field_strength"]

# Derived: thermodynamics
ENTROPY = _STANDARD_ATTRS["entropy"]
SPECIFIC_HEAT_CAPACITY = _STANDARD_ATTRS["specific_heat_capacity"]
THERMAL_CONDUCTIVITY = _STANDARD_ATTRS["thermal_conductivity"]

# Derived: photometry
ILLUMINANCE = _STANDARD_ATTRS["illuminance"]
LUMINOUS_EFFICACY = _STANDARD_ATTRS["luminous_efficacy"]

# Derived: chemistry
CATALYTIC_ACTIVITY = _STANDARD_ATTRS["catalytic_activity"]
MOLAR_MASS = _STANDARD_ATTRS["molar_mass"]
MOLAR_VOLUME = _STANDARD_ATTRS["molar_volume"]
MOLAR_ENERGY = _STANDARD_ATTRS["molar_energy"]
MOLAR_ENTROPY = _STANDARD_ATTRS["molar_entropy"]
CONCENTRATION = _STANDARD_ATTRS["concentration"]

# Derived: specific quantities (per-mass)
SPECIFIC_ENERGY = _STANDARD_ATTRS["specific_energy"]

# Derived: spectroscopy / radiation
WAVENUMBER = _STANDARD_ATTRS["wavenumber"]
RADIANT_EXPOSURE = _STANDARD_ATTRS["radiant_exposure"]
EXPOSURE = _STANDARD_ATTRS["exposure"]

# Derived: electromagnetism (additional)
ELECTRIC_DIPOLE_MOMENT = _STANDARD_ATTRS["electric_dipole_moment"]

# CGS base + derived
CGS_NONE = _STANDARD_ATTRS["cgs_none"]
CGS_LENGTH = _STANDARD_ATTRS["cgs_length"]
CGS_MASS = _STANDARD_ATTRS["cgs_mass"]
CGS_TIME = _STANDARD_ATTRS["cgs_time"]
CGS_VELOCITY = _STANDARD_ATTRS["cgs_velocity"]
CGS_FORCE = _STANDARD_ATTRS["cgs_force"]
CGS_ENERGY = _STANDARD_ATTRS["cgs_energy"]
CGS_PRESSURE = _STANDARD_ATTRS["cgs_pressure"]
CGS_DYNAMIC_VISCOSITY = _STANDARD_ATTRS["cgs_dynamic_viscosity"]
CGS_KINEMATIC_VISCOSITY = _STANDARD_ATTRS["cgs_kinematic_viscosity"]
CGS_ACCELERATION = _STANDARD_ATTRS["cgs_acceleration"]
CGS_WAVENUMBER = _STANDARD_ATTRS["cgs_wavenumber"]
CGS_RADIANT_EXPOSURE = _STANDARD_ATTRS["cgs_radiant_exposure"]

# CGS-ESU
CGS_ESU_CHARGE = _STANDARD_ATTRS["cgs_esu_charge"]
CGS_ESU_CURRENT = _STANDARD_ATTRS["cgs_esu_current"]
CGS_ESU_VOLTAGE = _STANDARD_ATTRS["cgs_esu_voltage"]
CGS_ESU_RESISTANCE = _STANDARD_ATTRS["cgs_esu_resistance"]
CGS_ESU_CAPACITANCE = _STANDARD_ATTRS["cgs_esu_capacitance"]
CGS_ESU_MAGNETIC_FLUX_DENSITY = _STANDARD_ATTRS["cgs_esu_magnetic_flux_density"]
CGS_ESU_MAGNETIC_FLUX = _STANDARD_ATTRS["cgs_esu_magnetic_flux"]
CGS_ESU_MAGNETIC_FIELD_STRENGTH = _STANDARD_ATTRS["cgs_esu_magnetic_field_strength"]
CGS_ESU_ELECTRIC_DIPOLE_MOMENT = _STANDARD_ATTRS["cgs_esu_electric_dipole_moment"]

# CGS-EMU
CGS_EMU_CURRENT = _STANDARD_ATTRS["cgs_emu_current"]
CGS_EMU_CHARGE = _STANDARD_ATTRS["cgs_emu_charge"]
CGS_EMU_VOLTAGE = _STANDARD_ATTRS["cgs_emu_voltage"]
CGS_EMU_RESISTANCE = _STANDARD_ATTRS["cgs_emu_resistance"]
CGS_EMU_CAPACITANCE = _STANDARD_ATTRS["cgs_emu_capacitance"]
CGS_EMU_INDUCTANCE = _STANDARD_ATTRS["cgs_emu_inductance"]

# Natural / Planck / Atomic
NATURAL_ENERGY = _STANDARD_ATTRS["natural_energy"]
PLANCK_ENERGY = _STANDARD_ATTRS["planck_energy"]
PLANCK_LENGTH = _STANDARD_ATTRS["planck_length"]
ATOMIC_ENERGY = _STANDARD_ATTRS["atomic_energy"]
ATOMIC_LENGTH = _STANDARD_ATTRS["atomic_length"]


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
        LUMINOUS_EFFICACY,
        # Derived - Chemistry
        CATALYTIC_ACTIVITY,
        MOLAR_MASS,
        MOLAR_VOLUME,
        MOLAR_ENERGY,
        MOLAR_ENTROPY,
        CONCENTRATION,
        # Derived - Specific quantities (per-mass)
        SPECIFIC_ENERGY,
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
        # Planck-unit dimensions
        PLANCK_ENERGY,
        PLANCK_LENGTH,
        # Atomic-unit dimensions
        ATOMIC_ENERGY,
        ATOMIC_LENGTH,
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
    "LUMINOUS_EFFICACY",
    # Derived dimensions - Chemistry
    "CATALYTIC_ACTIVITY",
    "MOLAR_MASS",
    "MOLAR_VOLUME",
    "MOLAR_ENERGY",
    "MOLAR_ENTROPY",
    "CONCENTRATION",
    # Derived dimensions - Specific quantities (per-mass)
    "SPECIFIC_ENERGY",
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
    # Planck-unit dimensions
    "PLANCK_ENERGY",
    "PLANCK_LENGTH",
    # Atomic-unit dimensions
    "ATOMIC_ENERGY",
    "ATOMIC_LENGTH",
]
