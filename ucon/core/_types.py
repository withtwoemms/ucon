# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
ucon.core._types
================

Colocated core types for the ucon unit system.

This module contains all core types that previously lived in separate
submodules (``scale``, ``unit``, ``product``, ``quantity``). Colocation
eliminates 11 deferred (function-body) imports that existed solely to
break circular import cycles between these tightly coupled classes.

Class definition order follows the dependency DAG::

    Exponent → _ScaleDescriptor → Scale
      → BaseForm → Unit → RebasedUnit → UnitFactor
        → UnitProduct
          → DimensionConstraint → Number → Ratio
            → NumberArray

External consumers should import from :mod:`ucon.core` (the re-export
facade) rather than from this private module directly.
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache, reduce, total_ordering
from typing import TYPE_CHECKING, Dict, Iterator, Tuple, Union, Any

if sys.version_info >= (3, 9):
    from typing import Annotated
else:
    from typing_extensions import Annotated  # type: ignore[assignment]

from ucon._active import _active as _sys_active_var
from ucon.basis import Basis, BasisGraph
from ucon.core._parsing_graph import _parsing_graph
from ucon.core.exceptions import KindDimensionMismatch, UnitDefinitionMismatch
from ucon.dimension import Dimension, NONE
from ucon.kinds.types import Kind

if TYPE_CHECKING:
    from ucon.graph import ConversionGraph
    from ucon.system import UnitSystem

# --- soft numpy dependency ---
try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    np = None  # type: ignore[assignment]
    _HAS_NUMPY = False

if TYPE_CHECKING:
    import numpy as np  # noqa: F811
    from numpy.typing import ArrayLike, NDArray


# =====================================================================
# Exponent
# =====================================================================

@total_ordering
class Exponent:
    """
    Represents a **base–exponent pair** (e.g., 10³ or 2¹⁰).

    Provides comparison and division semantics used internally to represent
    magnitude prefixes (e.g., kilo, mega, micro).
    """
    bases = {2: math.log2, 10: math.log10}

    __slots__ = ("base", "power")

    def __init__(self, base: int, power: Union[int, float]):
        if base not in self.bases.keys():
            raise ValueError(f'Only the following bases are supported: {reduce(lambda a,b: f"{a}, {b}", self.bases.keys())}')
        self.base = base
        self.power = power

    @property
    def evaluated(self) -> float:
        """Return the numeric value of base ** power."""
        return self.base ** self.power

    def parts(self) -> Tuple[int, Union[int, float]]:
        """Return (base, power) tuple, used for Scale lookups."""
        return self.base, self.power

    def __eq__(self, other: 'Exponent'):
        if not isinstance(other, Exponent):
            raise TypeError(f'Cannot compare Exponent to non-Exponent type: {type(other)}')
        return self.evaluated == other.evaluated

    def __lt__(self, other: 'Exponent'):
        if not isinstance(other, Exponent):
            return NotImplemented
        return self.evaluated < other.evaluated

    def __hash__(self):
        # Hash by rounded numeric equivalence to maintain cross-base consistency
        return hash(round(self.evaluated, 15))

    # ---------- Arithmetic Semantics ----------

    def __truediv__(self, other: 'Exponent'):
        """
        Divide two Exponents.
        - If bases match, returns a relative Exponent.
        - If bases differ, returns a numeric ratio (float).
        """
        if not isinstance(other, Exponent):
            return NotImplemented
        if self.base == other.base:
            return Exponent(self.base, self.power - other.power)
        return self.evaluated / other.evaluated

    def __mul__(self, other: 'Exponent'):
        if not isinstance(other, Exponent):
            return NotImplemented
        if self.base == other.base:
            return Exponent(self.base, self.power + other.power)
        return float(self.evaluated * other.evaluated)

    def __pow__(self, exponent: Union[int, float]) -> "Exponent":
        """
        Raise this Exponent to a numeric power.

        Example:
            Exponent(10, 3) ** 2
            # → Exponent(base=10, power=6)
        """
        return Exponent(self.base, self.power * exponent)

    # ---------- Conversion Utilities ----------

    def to_base(self, new_base: int) -> "Exponent":
        """
        Convert this Exponent to another base representation.

        Example:
            Exponent(2, 10).to_base(10)
            # → Exponent(base=10, power=3.010299956639812)
        """
        if new_base not in self.bases:
            supported = ", ".join(map(str, self.bases))
            raise ValueError(f"Unsupported base {new_base!r}. Supported bases: {supported}")
        new_power = self.bases[new_base](self.evaluated)
        return Exponent(new_base, new_power)

    # ---------- Numeric Interop ----------

    def __float__(self) -> float:
        return float(self.evaluated)

    def __int__(self) -> int:
        return int(self.evaluated)

    # ---------- Representation ----------

    def __repr__(self) -> str:
        return f"Exponent(base={self.base}, power={self.power})"

    def __str__(self) -> str:
        return f"{self.base}^{self.power}"


# =====================================================================
# Scale (with descriptor)
# =====================================================================

@dataclass(frozen=True)
class _ScaleDescriptor:
    exponent: Exponent
    shorthand: str
    alias: str

    @property
    def evaluated(self) -> float:
        return self.exponent.evaluated

    @property
    def base(self) -> int:
        return self.exponent.base

    @property
    def power(self) -> Union[int, float]:
        return self.exponent.power

    def parts(self) -> Tuple[int, Union[int, float]]:
        return (self.base, self.power)

    def __repr__(self):
        tag = self.alias or self.shorthand or "1"
        return f"<_ScaleDescriptor {tag}: {self.base}^{self.power}>"


@total_ordering
class Scale(Enum):
    # Binary
    exbi  = _ScaleDescriptor(Exponent(2, 60), "Ei", "exbi")
    pebi  = _ScaleDescriptor(Exponent(2, 50), "Pi", "pebi")
    tebi  = _ScaleDescriptor(Exponent(2, 40), "Ti", "tebi")
    gibi  = _ScaleDescriptor(Exponent(2, 30), "Gi", "gibi")
    mebi  = _ScaleDescriptor(Exponent(2, 20), "Mi", "mebi")
    kibi  = _ScaleDescriptor(Exponent(2, 10), "Ki", "kibi")

    # Decimal
    peta  = _ScaleDescriptor(Exponent(10, 15), "P", "peta")
    tera  = _ScaleDescriptor(Exponent(10, 12), "T", "tera")
    giga  = _ScaleDescriptor(Exponent(10, 9),  "G", "giga")
    mega  = _ScaleDescriptor(Exponent(10, 6),  "M", "mega")
    kilo  = _ScaleDescriptor(Exponent(10, 3),  "k", "kilo")
    hecto = _ScaleDescriptor(Exponent(10, 2),  "h", "hecto")
    deca  = _ScaleDescriptor(Exponent(10, 1),  "da", "deca")
    one   = _ScaleDescriptor(Exponent(10, 0),  "",  "")
    deci  = _ScaleDescriptor(Exponent(10,-1),  "d", "deci")
    centi = _ScaleDescriptor(Exponent(10,-2),  "c", "centi")
    milli = _ScaleDescriptor(Exponent(10,-3),  "m", "milli")
    micro = _ScaleDescriptor(Exponent(10,-6),  "µ", "micro")
    nano  = _ScaleDescriptor(Exponent(10,-9),  "n", "nano")
    pico  = _ScaleDescriptor(Exponent(10,-12), "p", "pico")
    femto = _ScaleDescriptor(Exponent(10,-15), "f", "femto")

    @property
    def descriptor(self) -> _ScaleDescriptor:
        return self.value

    @property
    def shorthand(self) -> str:
        return self.value.shorthand

    @property
    def alias(self) -> str:
        return self.value.alias

    @staticmethod
    @lru_cache(maxsize=1)
    def all() -> Dict[Tuple[int, int], str]:
        return {(s.value.base, s.value.power): s.name for s in Scale}

    @classmethod
    @lru_cache(maxsize=1)
    def _decimal_scales(cls):
        return [s for s in cls if s.value.base == 10]

    @classmethod
    @lru_cache(maxsize=1)
    def _binary_scales(cls):
        return [s for s in cls if s.value.base == 2]

    @staticmethod
    @lru_cache(maxsize=1)
    def by_value() -> Dict[float, str]:
        """
        Return a map from evaluated numeric value → Scale name.
        Cached after first access.
        """
        return {round(s.value.exponent.evaluated, 15): s.name for s in Scale}

    @classmethod
    def nearest(cls, value: float, include_binary: bool = False, undershoot_bias: float = 0.75) -> "Scale":
        if value == 0:
            return Scale.one
        abs_val = abs(value)
        candidates = list(cls) if include_binary else cls._decimal_scales()

        def distance(scale: "Scale") -> float:
            ratio = abs_val / scale.value.evaluated
            diff = math.log10(ratio)
            if ratio < 1:
                diff /= undershoot_bias
            return abs(diff)

        return min(candidates, key=distance)

    def __eq__(self, other: 'Scale'):
        return self.value.exponent == other.value.exponent

    def __gt__(self, other: 'Scale'):
        return self.value.exponent > other.value.exponent

    def __hash__(self):
        e = self.value.exponent
        return hash((e.base, round(e.power, 12)))

    def __mul__(self, other):
        # --- Case 1: applying Scale to simple Unit --------------------
        if isinstance(other, Unit):
            return UnitProduct({UnitFactor(unit=other, scale=self): 1})

        # --- Case 2: other cases are NOT handled here -----------------
        # UnitProduct scaling is handled solely by UnitProduct.__rmul__
        if isinstance(other, UnitProduct):
            return NotImplemented

        # --- Case 3: Scale * Scale algebra ----------------------------
        if isinstance(other, Scale):
            if self is Scale.one:
                return other
            if other is Scale.one:
                return self

            result = self.value.exponent * other.value.exponent
            include_binary = 2 in {self.value.base, other.value.base}

            if isinstance(result, Exponent):
                match = Scale.all().get(result.parts())
                if match:
                    return Scale[match]

            return Scale.nearest(float(result), include_binary=include_binary)

        return NotImplemented

    def __truediv__(self, other):
        if not isinstance(other, Scale):
            return NotImplemented
        if self == other:
            return Scale.one
        result = self.value.exponent / other.value.exponent
        if isinstance(result, Exponent):
            match = Scale.all().get(result.parts())
            if match:
                return Scale[match]
        include_binary = 2 in {self.value.base, other.value.base}
        return Scale.nearest(float(result), include_binary=include_binary)

    def __pow__(self, power):
        result = self.value.exponent ** power
        if isinstance(result, Exponent):
            match = Scale.all().get(result.parts())
            if match:
                return Scale[match]
        include_binary = self.value.base == 2
        return Scale.nearest(float(result), include_binary=include_binary)


# =====================================================================
# BaseForm
# =====================================================================

@dataclass(frozen=True)
class BaseForm:
    """Definitional decomposition of a unit into canonical base units of its basis.

    A unit's ``base_form`` answers: "in terms of the basis's canonical base units,
    what does 1 of this unit equal?" Mathematically:

        1 U  ≡  prefactor × b₁^e₁ × b₂^e₂ × ... × bₙ^eₙ

    Examples (SI basis):
        kilogram: BaseForm(prefactor=1.0, factors=((kilogram, 1.0),))
        gram:     BaseForm(prefactor=0.001, factors=((kilogram, 1.0),))
        newton:   BaseForm(prefactor=1.0,
                           factors=((kilogram, 1.0), (meter, 1.0), (second, -2.0)))
        bar:      BaseForm(prefactor=100000.0,
                           factors=((kilogram, 1.0), (meter, -1.0), (second, -2.0)))
        foot:     BaseForm(prefactor=0.3048, factors=((meter, 1.0),))

    Invariants:
        - ``prefactor`` is positive and finite
        - ``factors`` references only base units of the unit's own basis
        - dimensionally consistent with the parent Unit's ``dimension``
        - immutable; set at Unit construction; never mutated

    Affine units (kelvin/celsius/fahrenheit) and logarithmic units (dB, Np)
    cannot be represented as a single (prefactor, factors) pair and have
    ``base_form = None``.
    """
    factors: tuple  # tuple[tuple[Unit, float], ...]
    prefactor: float = 1.0


# =====================================================================
# Unit
# =====================================================================

@dataclass(frozen=True)
class Unit:
    """
    Represents a **unit of measure** associated with a :class:`Dimension`.

    A Unit is an atomic symbol with no scale information. Scale is handled
    separately by UnitFactor, which pairs a Unit with a Scale.

    Parameters
    ----------
    name : str
        Canonical name of the unit (e.g., "meter").
    dimension : Dimension
        The physical dimension this unit represents.
    aliases : tuple[str, ...]
        Optional shorthand symbols (e.g., ("m", "M")).
    scalable : bool
        Whether SI scale prefixes (k, M, G, …) may be applied to this unit
        at parse time. Defaults to ``True``. Set to ``False`` for units that
        do not compose with prefixes (e.g. affine temperature scales like
        ``celsius``, or domain conventions like ``radian`` where prefixed
        forms are not idiomatic). When ``False``, parsing ``"Pflop"`` for a
        non-scalable ``"flop"`` raises :class:`NonScalableError` rather than
        a generic :class:`UnknownUnitError`, giving callers a precise signal
        that the base is registered but does not accept prefix decomposition.

        Like :attr:`base_form`, ``scalable`` is metadata about parsing
        behavior, not an identity attribute — two Units that differ only in
        ``scalable`` compare equal and hash identically. This keeps the
        registry consistent if the flag is flipped on an existing unit.
    """
    name: str = ""
    dimension: Dimension = field(default=NONE)
    aliases: tuple[str, ...] = ()
    base_form: 'BaseForm | None' = field(default=None, repr=False, compare=False, hash=False)
    scalable: bool = field(default=True, compare=False, hash=False)

    def __post_init__(self):
        object.__setattr__(
            self, '_hash_cache',
            hash((self.name, self._norm(self.aliases), self.dimension)),
        )

    # ----------------- base_form mutation contract -----------------

    def _set_base_form(self, bf: 'BaseForm') -> None:
        """Install ``base_form`` on a Unit whose constructor could not supply it.

        This is the **single sanctioned mutation** of ``base_form`` after
        construction. Two legitimate callers exist:

        1. ``ucon.units`` SI bootstrap, where a coherent base unit's
           ``base_form`` is self-referential (1 kg ≡ 1 × kg) and cannot be
           expressed as a constructor literal because the Unit being
           constructed is itself the factor.
        2. ``ucon.serialization`` TOML loader, where forward references to
           other units in ``factors`` require a two-pass resolve.

        ``base_form`` is declared on a frozen dataclass with
        ``compare=False, hash=False`` so this late set does not violate the
        dataclass's equality or hashing guarantees. The idempotency guard
        below ensures no unit ever has its ``base_form`` overwritten after
        its first assignment.

        Raises
        ------
        ValueError
            If the Unit already has a non-None ``base_form``.
        TypeError
            If ``bf`` is not a BaseForm instance.
        """
        if not isinstance(bf, BaseForm):
            raise TypeError(
                f"_set_base_form expects a BaseForm, got {type(bf).__name__}"
            )
        if self.base_form is not None:
            raise ValueError(
                f"base_form already set on {self!r}; refusing to overwrite"
            )
        object.__setattr__(self, 'base_form', bf)

    # ----------------- symbolic helpers -----------------

    @staticmethod
    def _norm(aliases: tuple[str, ...]) -> tuple[str, ...]:
        """Normalize alias bag: drop empty/whitespace-only aliases."""
        return tuple(a for a in aliases if a.strip())

    @property
    def shorthand(self) -> str:
        """
        Symbol used in expressions (e.g., 'm', 's').
        For dimensionless units, returns ''.

        Note: Scale prefixes are handled by UnitFactor.shorthand, not here.
        """
        if self.dimension == NONE:
            return ""
        base = (self.aliases[0] if self.aliases else self.name) or ""
        return base.strip()

    @property
    def basis(self) -> Basis:
        """The dimensional basis this unit belongs to."""
        return self.dimension.vector.basis

    @property
    def base_signature(self) -> tuple:
        """Hashable, sorted projection of this unit's ``base_form`` to base-unit names.

        Returns a tuple of ``(base_unit_name, exponent)`` pairs, sorted by
        name. The prefactor from :attr:`base_form` is intentionally dropped —
        ``base_signature`` identifies the *shape* of the decomposition (which
        base units participate and with what exponents), not its scale.

        Units without a ``base_form`` (e.g., affine temperature, logarithmic,
        or graph-only units) report themselves as a self-leaf, so
        ``base_signature`` is always defined and the identity
        ``n.to_base().unit.base_signature == n.unit.base_signature`` holds
        for every ``Number n``.

        Intended uses
        -------------
        * Formula pre-validation: group inputs by ``base_signature`` to
          check they are all the same kind of thing before a calculation.
        * Dispatch keys: a hashable, basis-locked fingerprint suitable for
          ``dict`` / ``set`` lookups (e.g., memoizing formulas by input kind).
        * Round-trip equivalence checks in serialization / drift detection.

        ``base_signature`` is basis-locked (compares CGS and SI forms on
        their own base-unit vocabularies) and does **not** disambiguate
        kinds of quantity that share dimensions (e.g., energy vs torque).

        Examples
        --------
        >>> from ucon import units
        >>> units.meter.base_signature
        (('meter', 1.0),)
        >>> units.joule.base_signature
        (('kilogram', 1.0), ('meter', 2.0), ('second', -2.0))
        """
        if self.base_form is None:
            return ((self.name, 1.0),)
        return tuple(sorted(
            (u.name, exp) for u, exp in self.base_form.factors
        ))

    def is_compatible(
        self,
        other: 'Unit',
        basis_graph: 'BasisGraph | None' = None,
    ) -> bool:
        """Check if this unit is compatible with another for conversion.

        Two units are compatible if:
        1. They have the same dimension, OR
        2. Their bases are connected via the BasisGraph (cross-basis conversion)

        Parameters
        ----------
        other : Unit
            The other unit to check compatibility with.
        basis_graph : BasisGraph, optional
            The basis graph to use for cross-basis compatibility checks.
            If None, only same-dimension compatibility is checked.

        Returns
        -------
        bool
            True if the units can be converted between each other.

        Examples
        --------
        >>> from ucon import units, BasisGraph
        >>> units.meter.is_compatible(units.foot)
        True
        >>> units.meter.is_compatible(units.second)
        False
        """
        # Same dimension is always compatible
        if self.dimension == other.dimension:
            return True

        # Without a BasisGraph, different dimensions are incompatible
        if basis_graph is None:
            return False

        # Check if bases are connected via BasisGraph
        src_basis = self.basis
        dst_basis = other.basis

        if src_basis == dst_basis:
            # Same basis but different dimensions - incompatible
            return False

        # Cross-basis: check if bases are connected
        return basis_graph.are_connected(src_basis, dst_basis)

    # ----------------- algebra -----------------

    def __mul__(self, other):
        """
        Unit * Unit -> UnitProduct
        Unit * UnitProduct -> UnitProduct
        """
        if isinstance(other, UnitProduct):
            # let UnitProduct handle merging
            return other.__rmul__(self)

        if isinstance(other, Unit):
            if self == other:
                return UnitProduct({self: 2})
            return UnitProduct({self: 1, other: 1})

        return NotImplemented

    def __truediv__(self, other):
        """
        Unit / Unit or Unit / UnitProduct => UnitProduct
        """
        if isinstance(other, UnitProduct):
            combined = {self: 1.0}
            for u, exp in other.factors.items():
                combined[u] = combined.get(u, 0.0) - exp
            return UnitProduct(combined)

        if not isinstance(other, Unit):
            return NotImplemented

        # same physical unit → cancel to dimensionless
        if (
            self.dimension == other.dimension
            and self.name == other.name
            and self._norm(self.aliases) == self._norm(other.aliases)
        ):
            return Unit()  # dimensionless (matches units.none)

        # dividing by dimensionless → no change
        if other.dimension == NONE:
            return self

        # general case: form composite (self^1 * other^-1)
        return UnitProduct({self: 1, other: -1})

    def __pow__(self, power):
        """
        Unit ** n => UnitProduct with that exponent.
        """
        return UnitProduct({self: power})

    # ----------------- equality & hashing -----------------

    def __eq__(self, other):
        if isinstance(other, UnitProduct):
            return other.__eq__(self)
        if not isinstance(other, Unit):
            return NotImplemented
        return (
            self.dimension == other.dimension
            and self.name == other.name
            and self._norm(self.aliases) == self._norm(other.aliases)
        )

    def __hash__(self):
        return self._hash_cache

    # ----------------- representation -----------------

    def __repr__(self):
        """
        <Unit m>, <Unit kg>, <Unit>, <Unit | velocity>, etc.
        """
        if self.shorthand:
            return f"<Unit {self.shorthand}>"
        if self.dimension == NONE:
            return "<Unit>"
        return f"<Unit | {self.dimension.name}>"

    # ----------------- callable (creates Number) -----------------

    def __call__(self, quantity, uncertainty=None):
        """Create a Number or NumberArray with this unit.

        Parameters
        ----------
        quantity : int, float, list, tuple, or numpy.ndarray
            The numeric value(s). If array-like, returns NumberArray.
        uncertainty : float, array-like, or None
            The measurement uncertainty.

        Returns
        -------
        Number or NumberArray
            Number for scalar inputs, NumberArray for array inputs.

        Example
        -------
        >>> meter(5)
        <5 m>
        >>> meter(1.234, uncertainty=0.005)
        <1.234 ± 0.005 m>
        >>> meter([1, 2, 3])  # requires numpy
        <NumberArray [1. 2. 3.] m>
        """
        # Check for array-like inputs
        if _HAS_NUMPY and (
            isinstance(quantity, np.ndarray)
            or (isinstance(quantity, (list, tuple)) and len(quantity) > 0)
        ):
            return NumberArray(quantities=quantity, unit=self, uncertainty=uncertainty)

        return Number(quantity=quantity, unit=UnitProduct.from_unit(self), uncertainty=uncertainty)


# =====================================================================
# RebasedUnit
# =====================================================================

@dataclass(frozen=True)
class RebasedUnit:
    """
    A unit whose dimension was transformed by a BasisTransform.

    Lives in the destination partition but preserves provenance to the
    original unit and the transform that created it.

    Parameters
    ----------
    original : Unit
        The original unit before transformation.
    rebased_dimension : Dimension
        The dimension in the destination system.
    basis_transform : ucon.basis.BasisTransform or ucon.basis.transforms.ConstantBoundBasisTransform
        The transform that rebased this unit (from ucon.basis module).

    Examples
    --------
    >>> rebased = RebasedUnit(
    ...     original=statcoulomb,
    ...     rebased_dimension=Dimension.charge,
    ...     basis_transform=esu_to_si,
    ... )
    >>> rebased.dimension
    <Dimension.charge>
    >>> rebased.name
    'statcoulomb'
    """
    original: 'Unit'
    rebased_dimension: Dimension
    basis_transform: 'ucon.basis.BasisTransform | ucon.basis.transforms.ConstantBoundBasisTransform'

    @property
    def dimension(self) -> Dimension:
        """Return the rebased dimension (in the destination system)."""
        return self.rebased_dimension

    @property
    def name(self) -> str:
        """Return the name of the original unit."""
        return self.original.name


# =====================================================================
# UnitFactor
# =====================================================================

@dataclass(frozen=True)
class UnitFactor:
    """
    A structural pair (unit, scale) used as the *key* inside UnitProduct.

    - `unit` is a plain Unit (no extra meaning beyond dimension + aliases + name).
    - `scale` is the *expression-level* Scale attached by the user (e.g. milli in mL).

    Two UnitFactors are equal iff both `unit` and `scale` are equal, so components
    with the same base unit and same scale truly merge.

    NOTE: We also implement equality / hashing in a way that allows lookups
    by the underlying Unit to keep working:

        m in product.factors
        product.factors[m]

    still work even though the actual keys are UnitFactor instances.
    """

    unit: "Unit"
    scale: "Scale"

    def __post_init__(self):
        object.__setattr__(self, '_hash_cache', hash(self.unit))

    # ------------- Projections (Unit-like surface) -------------------------

    @property
    def dimension(self):
        return self.unit.dimension

    @property
    def aliases(self):
        return getattr(self.unit, "aliases", ())

    @property
    def name(self):
        return getattr(self.unit, "name", "")

    @property
    def shorthand(self) -> str:
        """
        Render something like 'mg' for UnitFactor(gram, milli),
        or 'L' for UnitFactor(liter, one).
        """
        base = ""
        if self.aliases:
            base = self.aliases[0]
        elif self.name:
            base = self.name

        prefix = "" if self.scale is Scale.one else self.scale.shorthand
        return f"{prefix}{base}".strip()

    # ------------- Identity & hashing -------------------------------------

    def __repr__(self) -> str:
        return f"UnitFactor(unit={self.unit!r}, scale={self.scale!r})"

    def __hash__(self) -> int:
        # Important: share hash space with the underlying Unit so that
        # lookups by Unit (e.g., factors[unit]) work against UnitFactor keys.
        return self._hash_cache

    def __eq__(self, other):
        # UnitFactor vs UnitFactor → structural equality
        if isinstance(other, UnitFactor):
            return (self.unit == other.unit) and (self.scale == other.scale)

        # UnitFactor vs Unit → equal iff underlying unit matches AND
        # this UnitFactor has Scale.one (since Unit has no scale).
        # This lets `unit in factors` work when `factors` is keyed by UnitFactor.
        if isinstance(other, Unit):
            return self.unit == other and self.scale is Scale.one

        return NotImplemented


# =====================================================================
# UnitProduct
# =====================================================================

class UnitProduct:
    """
    Represents a product or quotient of Units.

    Key properties:
    - factors is a dict[UnitFactor, float] mapping (unit, scale) pairs to exponents.
    - Nested UnitProduct instances are flattened.
    - Identical UnitFactors (same underlying unit and same scale) merge exponents.
    - Units with net exponent ~0 are dropped.
    - Dimensionless units (NONE) are dropped.
    - Scaled variants of the same base unit (e.g. L and mL) are grouped by
      (name, dimension, aliases) and their exponents combined; if the net exponent
      is ~0, the whole group is cancelled.
    """

    _SUPERSCRIPTS = str.maketrans("0123456789-.", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻·")

    def __init__(self, factors: dict[Unit, float]):
        """
        Build a UnitProduct with UnitFactor keys, preserving user-provided scales.

        Key principles:
        - Never canonicalize scale (no implicit preference for Scale.one).
        - Only collapse scaled variants of the same base unit when total exponent == 0.
        - If only one scale variant exists in a group, preserve it exactly.
        - If multiple variants exist and the group exponent != 0, preserve the FIRST
        encountered UnitFactor (keeps user-intent scale).
        """

        self.name = ""
        self.aliases = ()

        # --- Fast path: single factor, no nesting ---
        if len(factors) == 1:
            key, exp = next(iter(factors.items()))
            if not isinstance(key, UnitProduct):
                if isinstance(key, Unit) and not isinstance(key, UnitFactor):
                    key = UnitFactor(key, Scale.one)
                if isinstance(key, UnitFactor) and key.dimension != NONE and abs(exp) > 1e-12:
                    self.factors = {key: exp}
                    self._residual_scale_factor = 1.0
                    self.dimension = key.dimension ** exp
                    return

        # --- Fast path: two factors, no nesting, no cancellation ---
        if len(factors) == 2:
            items = list(factors.items())
            k0, e0 = items[0]
            k1, e1 = items[1]
            if not isinstance(k0, UnitProduct) and not isinstance(k1, UnitProduct):
                if isinstance(k0, Unit) and not isinstance(k0, UnitFactor):
                    k0 = UnitFactor(k0, Scale.one)
                if isinstance(k1, Unit) and not isinstance(k1, UnitFactor):
                    k1 = UnitFactor(k1, Scale.one)
                if (isinstance(k0, UnitFactor) and isinstance(k1, UnitFactor)
                        and k0.dimension != NONE and k1.dimension != NONE
                        and abs(e0) > 1e-12 and abs(e1) > 1e-12
                        and k0 != k1):
                    self.factors = {k0: e0, k1: e1}
                    self._residual_scale_factor = 1.0
                    self.dimension = (k0.dimension ** e0) * (k1.dimension ** e1)
                    return

        merged: dict[UnitFactor, float] = {}

        # -----------------------------------------------------
        # Helper: normalize Units or UnitFactors to UnitFactor
        # -----------------------------------------------------
        def to_factored(unit_or_fu):
            if isinstance(unit_or_fu, UnitFactor):
                return unit_or_fu
            # Plain Unit has no scale - wrap with Scale.one
            return UnitFactor(unit_or_fu, Scale.one)

        # -----------------------------------------------------
        # Helper: merge UnitFactors by full (unit, scale) identity
        # -----------------------------------------------------
        def merge_fu(fu: UnitFactor, exponent: float):
            for existing in merged:
                if existing == fu:     # UnitFactor.__eq__ handles scale & unit compare
                    merged[existing] += exponent
                    return
            merged[fu] = merged.get(fu, 0.0) + exponent

        # Track residual scale from nested UnitProducts that get flattened.
        # This captures scale from previously-cancelled units.
        inherited_residual: float = 1.0

        # -----------------------------------------------------
        # Step 1 — Flatten sources into UnitFactors
        # -----------------------------------------------------
        for key, exp in factors.items():
            if isinstance(key, UnitProduct):
                # Flatten nested UnitProducts
                for inner_fu, inner_exp in key.factors.items():
                    merge_fu(inner_fu, inner_exp * exp)
                # Capture residual scale from the nested product
                # (e.g., from mg/kg cancellation)
                inner_residual = getattr(key, '_residual_scale_factor', 1.0)
                if inner_residual != 1.0:
                    inherited_residual *= inner_residual ** exp
            else:
                merge_fu(to_factored(key), exp)

        # -----------------------------------------------------
        # Step 2 — Remove exponent-zero & dimensionless UnitFactors
        # -----------------------------------------------------
        simplified: dict[UnitFactor, float] = {}
        for fu, exp in merged.items():
            if abs(exp) < 1e-12:
                continue
            if fu.dimension == NONE:
                continue
            simplified[fu] = exp

        # -----------------------------------------------------
        # Step 3 — Group by full unit identity (including scale)
        # -----------------------------------------------------
        # NOTE: We include scale in the group key so that differently-scaled
        # variants of the same base unit (e.g., mg and kg) remain separate.
        # This preserves user intent in expressions like mg/kg, allowing
        # the mg to survive when later multiplied by kg (e.g., mg/kg * kg = mg).
        groups: dict[tuple, dict[UnitFactor, float]] = {}

        for fu, exp in simplified.items():
            alias_key = tuple(sorted(a for a in fu.aliases if a))
            group_key = (fu.name, fu.dimension, alias_key, fu.scale)
            groups.setdefault(group_key, {})
            groups[group_key][fu] = groups[group_key].get(fu, 0.0) + exp

        # -----------------------------------------------------
        # Step 4 — Resolve groups while preserving user scale
        # -----------------------------------------------------
        final: dict[UnitFactor, float] = {}

        # Track residual scale NUMERICALLY from cancelled units.
        # This accumulates scale factors when units cancel dimensionally
        # but have different scales (e.g., gram / decagram = factor of 0.1).
        # We use a numeric value rather than Scale to preserve precision
        # for arbitrary combinations (especially binary scales like kibi).
        residual_scale_factor: float = 1.0

        for group_key, bucket in groups.items():
            total_exp = sum(bucket.values())

            # 4A — Full cancellation (dimensionally)
            # BUT: we must preserve the NET SCALE from the cancelled units!
            if abs(total_exp) < 1e-12:
                # Compute the scale contribution from this cancelled group
                # Each factor contributes: factor.scale.value.evaluated ** exponent
                for fu, exp in bucket.items():
                    residual_scale_factor *= fu.scale.value.evaluated ** exp
                continue

            # 4B — Only one scale variant → preserve exactly
            if len(bucket) == 1:
                fu, exp = next(iter(bucket.items()))
                final[fu] = exp
                continue

            # 4C — Multiple scale variants, exponent != 0:
            #      preserve FIRST encountered UnitFactor.
            #      This ensures user scale is preserved.
            #      BUT: also accumulate scale from the OTHER variants
            first_fu = next(iter(bucket.keys()))
            final[first_fu] = total_exp

            # The first_fu will be kept with total_exp, so its scale^total_exp
            # will be folded normally. We need to account for the OTHER factors'
            # scale contributions that are being "absorbed" into this representative.
            for fu, exp in bucket.items():
                if fu is not first_fu:
                    # This factor is being absorbed; its scale contribution
                    # relative to first_fu needs to be captured
                    residual_scale_factor *= fu.scale.value.evaluated ** exp

        self.factors = final

        # Store the residual scale factor from cancellations (numeric)
        # Include inherited residual from nested UnitProducts
        self._residual_scale_factor = residual_scale_factor * inherited_residual

        # -----------------------------------------------------
        # Step 5 — Derive dimension via exponent algebra
        # -----------------------------------------------------
        self.dimension = reduce(
            lambda acc, item: acc * (item[0].dimension ** item[1]),
            self.factors.items(),
            NONE,
        )

    # ------------- Rendering -------------------------------------------------

    @classmethod
    def _append(cls, unit: Unit, power: float, num: list[str], den: list[str]) -> None:
        """
        Append a unit^power into numerator or denominator list. Works with
        both Unit and UnitFactor, since UnitFactor exposes dimension,
        shorthand, name, and aliases.
        """
        if unit.dimension == NONE:
            return
        part = getattr(unit, "shorthand", "") or getattr(unit, "name", "") or ""
        if not part:
            return

        def fmt_exp(p: float) -> str:
            """Format exponent, using int when possible to avoid '2.0' → '²·⁰'."""
            return str(int(p) if p == int(p) else p).translate(cls._SUPERSCRIPTS)

        if power > 0:
            if power == 1:
                num.append(part)
            else:
                num.append(part + fmt_exp(power))
        elif power < 0:
            if power == -1:
                den.append(part)
            else:
                den.append(part + fmt_exp(-power))

    @property
    def shorthand(self) -> str:
        """
        Human-readable composite unit string, e.g. 'kg·m/s²'.
        """
        if not self.factors:
            return ""

        num: list[str] = []
        den: list[str] = []

        for u, power in self.factors.items():
            self._append(u, power, num, den)

        numerator = "·".join(num) or "1"
        denominator = "·".join(den)
        if not denominator:
            return numerator
        if len(den) > 1:
            return f"{numerator}/({denominator})"
        return f"{numerator}/{denominator}"

    def fold_scale(self) -> float:
        """
        Compute the overall numeric scale factor of this UnitProduct by folding
        together the scales of each UnitFactor raised to its exponent,
        plus any residual scale factor from cancelled units.

        Returns
        -------
        float
            The combined numeric scale factor.
        """
        # Cache the result since UnitProduct is effectively immutable
        cached = getattr(self, '_fold_scale_cache', None)
        if cached is not None:
            return cached

        result = getattr(self, '_residual_scale_factor', 1.0)
        for factor, power in self.factors.items():
            result *= factor.scale.value.evaluated ** power

        self._fold_scale_cache = result
        return result

    def to_base_form(self) -> tuple:
        """Expand all factors to SI base units algebraically.

        Returns
        -------
        (base_factors, prefactor)
            base_factors: dict mapping base Unit → net exponent
            prefactor: cumulative scalar (product of all scale, decomposition prefactors)
        """
        cached = getattr(self, '_to_base_form_cache', None)
        if cached is not None:
            return cached

        base_factors: dict = {}
        prefactor = getattr(self, '_residual_scale_factor', 1.0)

        for uf, exp in self.factors.items():
            prefactor *= uf.scale.value.evaluated ** exp

            bf = uf.unit.base_form
            if bf is None:
                # No base_form — treat unit as its own base
                base_factors[uf.unit] = base_factors.get(uf.unit, 0.0) + exp
            else:
                prefactor *= bf.prefactor ** exp
                for base_unit, base_exp in bf.factors:
                    base_factors[base_unit] = base_factors.get(base_unit, 0.0) + base_exp * exp

        # Drop zero-exponent entries
        result = ({u: e for u, e in base_factors.items() if abs(e) > 1e-12}, prefactor)
        self._to_base_form_cache = result
        return result

    @property
    def base_signature(self) -> tuple:
        """Hashable, sorted projection of this product's base-unit decomposition.

        Returns a tuple of ``(base_unit_name, exponent)`` pairs, sorted by
        name. Composes each factor's ``Unit.base_signature`` contribution
        with the product's exponents, collapsing duplicates and dropping
        zero-exponent terms. The prefactor accumulated during base-form
        expansion is intentionally dropped.

        Leverages the same walk as :meth:`to_base_form` but discards the
        cumulative scalar, returning only the basis-identity fingerprint.

        Examples
        --------
        >>> from ucon.units import meter, second
        >>> (meter / second).base_signature
        (('meter', 1.0), ('second', -1.0))
        >>> (meter * meter / (second * second)).base_signature
        (('meter', 2.0), ('second', -2.0))
        """
        accumulated: dict = {}
        for uf, exp in self.factors.items():
            bf = uf.unit.base_form
            if bf is None:
                accumulated[uf.unit.name] = accumulated.get(uf.unit.name, 0.0) + exp
            else:
                for base_u, base_exp in bf.factors:
                    accumulated[base_u.name] = accumulated.get(base_u.name, 0.0) + base_exp * exp
        return tuple(sorted(
            (name, exp) for name, exp in accumulated.items() if abs(exp) > 1e-12
        ))

    # ------------- Helpers ---------------------------------------------------

    _from_unit_cache: dict[int, 'UnitProduct'] = {}

    @classmethod
    def from_unit(cls, unit: Unit) -> 'UnitProduct':
        """Wrap a plain Unit as a UnitProduct with Scale.one (cached)."""
        uid = id(unit)
        cached = cls._from_unit_cache.get(uid)
        if cached is not None:
            return cached
        result = cls({UnitFactor(unit, Scale.one): 1})
        cls._from_unit_cache[uid] = result
        return result

    def as_unit(self) -> Union[Unit, None]:
        """Extract the underlying Unit if this is a trivial single-factor product.

        Returns the Unit when this UnitProduct wraps exactly one factor with
        exponent 1 and Scale.one, otherwise None.
        """
        if len(self.factors) != 1:
            return None
        factor, exp = next(iter(self.factors.items()))
        if exp != 1 or factor.scale != Scale.one:
            return None
        return factor.unit

    def factors_by_dimension(self) -> dict[Dimension, tuple[UnitFactor, float]]:
        """Group factors by dimension.

        Returns a dict mapping each Dimension to (UnitFactor, exponent).
        Raises ValueError if multiple factors share the same Dimension.
        """
        result: dict[Dimension, tuple[UnitFactor, float]] = {}
        for factor, exp in self.factors.items():
            dim = factor.unit.dimension
            if dim in result:
                raise ValueError(f"Multiple factors for dimension {dim}")
            result[dim] = (factor, exp)
        return result

    def _norm(self, aliases: tuple[str, ...]) -> tuple[str, ...]:
        """Normalize alias bag: drop empty/whitespace-only aliases."""
        return tuple(a for a in aliases if a.strip())

    def __pow__(self, power):
        """UnitProduct ** n => new UnitProduct with scaled exponents."""
        return UnitProduct({u: exp * power for u, exp in self.factors.items()})

    # ------------- Algebra ---------------------------------------------------

    def __mul__(self, other):
        if isinstance(other, Unit):
            combined = self.factors.copy()
            combined[other] = combined.get(other, 0.0) + 1.0
            result = UnitProduct(combined)
            # Propagate residual scale factor from self
            result._residual_scale_factor *= self._residual_scale_factor
            return result

        if isinstance(other, UnitProduct):
            combined = self.factors.copy()
            for u, exp in other.factors.items():
                combined[u] = combined.get(u, 0.0) + exp
            result = UnitProduct(combined)
            # Propagate residual scale factors from both operands
            result._residual_scale_factor *= self._residual_scale_factor
            result._residual_scale_factor *= other._residual_scale_factor
            return result

        if isinstance(other, Scale):
            # respect the convention: Scale * Unit, not Unit * Scale
            return NotImplemented

        return NotImplemented

    def __rmul__(self, other):
        # Scale * UnitProduct → apply scale to a canonical sink unit
        if isinstance(other, Scale):
            if not self.factors:
                return self

            # heuristic: choose unit with positive exponent first, else first unit
            items = list(self.factors.items())
            positives = [(u, e) for (u, e) in items if e > 0]
            sink, _ = (positives or items)[0]

            # Normalize sink into a UnitFactor
            if isinstance(sink, UnitFactor):
                sink_fu = sink
            else:
                # Plain Unit has no scale
                sink_fu = UnitFactor(unit=sink, scale=Scale.one)

            # Combine scales (expression-level)
            if sink_fu.scale is not Scale.one:
                new_scale = other * sink_fu.scale
            else:
                new_scale = other

            scaled_sink = UnitFactor(
                unit=sink_fu.unit,
                scale=new_scale,
            )

            combined: dict[UnitFactor, float] = {}
            for u, exp in self.factors.items():
                # Normalize each key into UnitFactor as we go
                if isinstance(u, UnitFactor):
                    fu = u
                else:
                    # Plain Unit has no scale
                    fu = UnitFactor(unit=u, scale=Scale.one)

                if fu is sink_fu:
                    combined[scaled_sink] = combined.get(scaled_sink, 0.0) + exp
                else:
                    combined[fu] = combined.get(fu, 0.0) + exp

            result = UnitProduct(combined)
            # Propagate residual scale factor from self
            result._residual_scale_factor *= self._residual_scale_factor
            return result

        if isinstance(other, Unit):
            combined: dict[Unit, float] = {other: 1.0}
            for u, e in self.factors.items():
                combined[u] = combined.get(u, 0.0) + e
            result = UnitProduct(combined)
            # Propagate residual scale factor from self
            result._residual_scale_factor *= self._residual_scale_factor
            return result

        return NotImplemented

    def __truediv__(self, other):
        if isinstance(other, Unit):
            combined = self.factors.copy()
            combined[other] = combined.get(other, 0.0) - 1.0
            result = UnitProduct(combined)
            # Propagate residual scale factor from self
            result._residual_scale_factor *= self._residual_scale_factor
            return result

        if isinstance(other, UnitProduct):
            combined = self.factors.copy()
            for u, exp in other.factors.items():
                combined[u] = combined.get(u, 0.0) - exp
            result = UnitProduct(combined)
            # Propagate residual: self's residual divided by other's residual
            result._residual_scale_factor *= self._residual_scale_factor
            result._residual_scale_factor /= other._residual_scale_factor
            return result

        return NotImplemented

    # ------------- Identity & hashing ---------------------------------------

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.shorthand}>"

    def __eq__(self, other):
        if isinstance(other, Unit):
            # Only equal to a plain Unit if we have exactly that unit^1
            # Here, the tuple comparison will invoke UnitFactor.__eq__(Unit)
            # on the key when factors are keyed by UnitFactor.
            return len(self.factors) == 1 and list(self.factors.items()) == [(other, 1.0)]
        return isinstance(other, UnitProduct) and self.factors == other.factors

    def __hash__(self):
        # Sort by name; UnitFactor exposes .name, so this is stable.
        return hash(tuple(sorted(self.factors.items(), key=lambda x: x[0].name)))

    def __call__(self, quantity, uncertainty=None):
        """Create a Number or NumberArray with this unit product.

        Parameters
        ----------
        quantity : int, float, list, tuple, or numpy.ndarray
            The numeric value(s). If array-like, returns NumberArray.
        uncertainty : float, array-like, or None
            The measurement uncertainty.

        Returns
        -------
        Number or NumberArray
            Number for scalar inputs, NumberArray for array inputs.

        Example
        -------
        >>> (meter / second)(10)
        <10 m/s>
        >>> (meter / second)(10, uncertainty=0.5)
        <10 ± 0.5 m/s>
        >>> (meter / second)([10, 20, 30])  # requires numpy
        <NumberArray [10. 20. 30.] m/s>
        """
        # Check for array-like inputs
        if _HAS_NUMPY and (
            isinstance(quantity, np.ndarray)
            or (isinstance(quantity, (list, tuple)) and len(quantity) > 0)
        ):
            return NumberArray(quantities=quantity, unit=self, uncertainty=uncertainty)

        return Number(quantity=quantity, unit=self, uncertainty=uncertainty)


# =====================================================================
# Quantity types: Number, Ratio, DimensionConstraint
# =====================================================================

# Dimensionless unit for use as default in Number
_none = Unit()

_Quantifiable = Union['Number', 'Ratio']


class DimensionConstraint:
    """Annotation marker: constrains a Number to a specific Dimension.

    Used with typing.Annotated to enable Number[TIME] syntax.
    The decorator @enforce_dimensions introspects this marker at runtime.
    """

    __slots__ = ("dimension",)

    def __init__(self, dim: Dimension):
        self.dimension = dim

    def __repr__(self) -> str:
        return f"DimensionConstraint({self.dimension.name})"

    def __eq__(self, other) -> bool:
        return isinstance(other, DimensionConstraint) and self.dimension == other.dimension

    def __hash__(self) -> int:
        return hash(("DimensionConstraint", self.dimension))


@dataclass
class Number:
    """
    Represents a **numeric quantity** with an associated :class:`Unit` and :class:`Scale`.

    Combines magnitude, unit, and scale into a single, composable object that
    supports dimensional arithmetic and conversion:

        >>> from ucon.units import meter, second
        >>> length = meter(5)
        >>> time = second(2)
        >>> speed = length / time
        >>> speed
        <2.5 m/s>

    Optionally includes measurement uncertainty for error propagation:

        >>> length = meter(1.234, uncertainty=0.005)
        >>> length
        <1.234 ± 0.005 m>
    """
    quantity: Union[float, int] = 1.0
    unit: Union[Unit, UnitProduct] = None
    uncertainty: Union[float, None] = None
    kind: Union[Kind, None] = None

    def __post_init__(self):
        if self.unit is None:
            object.__setattr__(self, 'unit', _none)
        if self.kind is not None and self.kind.dimension != self.unit.dimension:
            raise KindDimensionMismatch(kind=self.kind, unit=self.unit)

    def __class_getitem__(cls, dim):
        """Enable Number[Dimension.X] syntax for type annotations.

        Returns Annotated[Number, DimensionConstraint(dim)] for runtime introspection
        by @enforce_dimensions decorator.
        """
        if isinstance(dim, Dimension):
            return Annotated[cls, DimensionConstraint(dim)]
        return cls

    @property
    def value(self) -> float:
        """Return the numeric magnitude as-expressed (no scale folding).

        Scale lives in the unit expression (e.g. kJ, mL) and is NOT
        folded into the returned value.  Use ``unit.fold_scale()`` on a
        UnitProduct when you need the base-unit-equivalent magnitude.
        """
        return round(self.quantity, 15)

    @property
    def _canonical_magnitude(self) -> float:
        """Quantity in coherent base-unit scale.

        Pure function of (self.quantity, self.unit). Does NOT consult any graph.
        """
        if isinstance(self.unit, UnitProduct):
            result = self.quantity * getattr(self.unit, '_residual_scale_factor', 1.0)
            for uf, exp in self.unit.factors.items():
                result *= uf.scale.value.evaluated ** exp
                bf = uf.unit.base_form
                if bf is not None:
                    result *= bf.prefactor ** exp
            return result
        bf = self.unit.base_form
        if bf is not None:
            return self.quantity * bf.prefactor
        return self.quantity

    @property
    def canonical_magnitude(self) -> float:
        """Quantity expressed in coherent base-unit scale, as a plain float.

        This is the magnitude you would get from :meth:`to_base` and then
        reading ``.quantity``. It is a pure function of ``(self.quantity,
        self.unit)`` and does NOT consult any conversion graph.

        Use :attr:`canonical_magnitude` at interop boundaries where you need
        a raw float in SI-coherent units (e.g., for a dimensionless formula
        constant, a JSON payload, or a plotting library). For unit-safe
        composition, prefer :meth:`to_base`, which returns a new ``Number``.

        Examples
        --------
        >>> from ucon.units import kilometer, hour
        >>> kilometer(5).canonical_magnitude
        5000.0
        >>> (kilometer(90) / hour(1)).canonical_magnitude
        25.0
        """
        return self._canonical_magnitude

    @property
    def base_signature(self) -> tuple:
        """Hashable, sorted base-unit-name projection of this Number's unit.

        Delegates to ``self.unit.base_signature``. See
        :attr:`Unit.base_signature` for semantics and intended uses.

        The signature is invariant under :meth:`to_base` — that is,
        ``n.base_signature == n.to_base().base_signature`` for every
        ``Number n``. This makes it a useful dispatch / grouping key for
        formula inputs expressed in arbitrary scales.

        Examples
        --------
        >>> from ucon.units import kilometer, hour
        >>> kilometer(5).base_signature
        (('meter', 1.0),)
        >>> (kilometer(90) / hour(1)).base_signature
        (('meter', 1.0), ('second', -1.0))
        """
        return self.unit.base_signature

    @property
    def in_base_form(self) -> bool:
        """True if this Number is already expressed in coherent base units.

        A Number is *in base form* when :meth:`to_base` would produce an
        output equivalent to ``self`` (up to structural identity of the
        unit expression). Concretely, this holds when:

        * every factor's scale is :attr:`Scale.one`,
        * every factor's underlying :class:`Unit` is a *leaf* — either
          ``base_form is None`` or a self-referential coherent base
          (e.g., ``kilogram``, ``meter``), and
        * any residual scale factor from cancelled factors is ``1.0``.

        Use ``in_base_form`` as a fast pre-check to avoid a redundant
        :meth:`to_base` call in hot paths, or as an invariant assertion at
        formula boundaries.

        Examples
        --------
        >>> from ucon.units import kilometer, meter, hour, joule
        >>> meter(5).in_base_form
        True
        >>> kilometer(5).in_base_form
        False
        >>> kilometer(5).to_base().in_base_form
        True
        >>> joule(1).in_base_form  # joule has a non-trivial base_form
        False
        """
        def _is_leaf(u: 'Unit') -> bool:
            bf = u.base_form
            if bf is None:
                return True
            return (len(bf.factors) == 1
                    and bf.factors[0][0] is u
                    and abs(bf.factors[0][1] - 1.0) < 1e-12)

        if isinstance(self.unit, UnitProduct):
            if getattr(self.unit, '_residual_scale_factor', 1.0) != 1.0:
                return False
            for uf in self.unit.factors:
                if uf.scale is not Scale.one:
                    return False
                if not _is_leaf(uf.unit):
                    return False
            return True
        return _is_leaf(self.unit)

    def to_base(self) -> 'Number':
        """Return a new Number expressed in coherent base-unit scale.

        Walks ``self.unit`` and decomposes each factor through its
        :attr:`~Unit.base_form` (when available) to produce a quantity in the
        basis's canonical base units (e.g., SI: ``kg, m, s, A, K, cd, mol``).

        This is a pure algebraic operation; no :class:`~ucon.graph.ConversionGraph`
        is consulted. Units that lack a ``base_form`` (affine temperature
        units, logarithmic units, or units whose definition is graph-only)
        are preserved as-is at ``Scale.one``.

        Returns
        -------
        Number
            A new ``Number`` whose unit is either a plain base ``Unit`` (when
            the decomposition collapses to a single factor at exponent 1) or
            a :class:`UnitProduct` of base units. Uncertainty is scaled by the
            same multiplier as the quantity.

        Examples
        --------
        >>> from ucon.units import kilometer, hour, joule
        >>> kilometer(5).to_base()
        <5000 m>
        >>> (kilometer(90) / hour(1)).to_base()
        <25 m/s>
        >>> joule(1).to_base()
        <1 kg·m²/s²>

        Notes
        -----
        ``to_base()`` is the unit-safe counterpart to
        :attr:`canonical_magnitude`. The identity
        ``n.to_base().quantity == n.canonical_magnitude`` holds for every
        ``Number n``.
        """
        # Total multiplier from self.unit to base-unit scale.
        # Compute on a unit Number so quantity=0 is handled correctly.
        multiplier = Number(1.0, self.unit)._canonical_magnitude
        canonical_q = self.quantity * multiplier

        new_uncertainty = None
        if self.uncertainty is not None:
            new_uncertainty = self.uncertainty * abs(multiplier)

        def _decompose(unit) -> dict:
            """Return a dict[UnitFactor, float] of base-unit factors for `unit`.

            If `unit` has no useful base_form (None or self-referential),
            it is preserved as-is at Scale.one.
            """
            bf = unit.base_form
            if bf is None:
                return {UnitFactor(unit, Scale.one): 1.0}
            # Self-referential coherent base (e.g., kilogram -> kilogram^1)
            if (len(bf.factors) == 1
                    and bf.factors[0][0] is unit
                    and abs(bf.factors[0][1] - 1.0) < 1e-12):
                return {UnitFactor(unit, Scale.one): 1.0}
            out: dict = {}
            for base_unit, base_exp in bf.factors:
                key = UnitFactor(base_unit, Scale.one)
                out[key] = out.get(key, 0.0) + base_exp
            return out

        # Accumulate base-unit factors with combined exponents
        base_dict: dict = {}
        if isinstance(self.unit, UnitProduct):
            for uf, exp in self.unit.factors.items():
                for key, base_exp in _decompose(uf.unit).items():
                    base_dict[key] = base_dict.get(key, 0.0) + base_exp * exp
        else:
            for key, base_exp in _decompose(self.unit).items():
                base_dict[key] = base_dict.get(key, 0.0) + base_exp

        # Drop zero exponents
        base_dict = {k: e for k, e in base_dict.items() if abs(e) > 1e-12}

        # Degenerate case: everything cancelled. Preserve structural unit.
        if not base_dict:
            return Number(
                quantity=canonical_q,
                unit=self.unit,
                uncertainty=new_uncertainty,
            )

        # Single factor at exp 1.0: return as plain Unit for ergonomic output
        if len(base_dict) == 1:
            key, exp = next(iter(base_dict.items()))
            if abs(exp - 1.0) < 1e-12:
                return Number(
                    quantity=canonical_q,
                    unit=key.unit,
                    uncertainty=new_uncertainty,
                )

        return Number(
            quantity=canonical_q,
            unit=UnitProduct(base_dict),
            uncertainty=new_uncertainty,
        )

    def same_dimension_as(self, other) -> bool:
        """Return True if ``self`` and ``other`` share a dimension.

        Accepts another :class:`Number`, :class:`Unit`, or
        :class:`UnitProduct`. Compares on :attr:`Dimension` equality — the
        fundamental invariant of unit compatibility — which is basis-aware
        and scale-agnostic.

        This is a lightweight compatibility check for the common case
        "can I add / compare / feed these into the same formula slot?"
        without the overhead of constructing a conversion or walking the
        graph.

        Parameters
        ----------
        other : Number, Unit, or UnitProduct
            The quantity or unit expression to compare dimensions with.

        Returns
        -------
        bool
            True if the dimensions match, False otherwise.

        Raises
        ------
        TypeError
            If ``other`` is not a Number, Unit, or UnitProduct.

        Examples
        --------
        >>> from ucon.units import kilometer, mile, hour, second, joule
        >>> kilometer(5).same_dimension_as(mile(3))
        True
        >>> kilometer(5).same_dimension_as(hour(2))
        False
        >>> (kilometer(90) / hour(1)).same_dimension_as(
        ...     kilometer(1) / second(1)
        ... )
        True
        """
        if isinstance(other, Number):
            return self.unit.dimension == other.unit.dimension
        if isinstance(other, (Unit, UnitProduct)):
            return self.unit.dimension == other.dimension
        raise TypeError(
            f"same_dimension_as expects Number, Unit, or UnitProduct; "
            f"got {type(other).__name__}"
        )

    def simplify(self) -> 'Number':
        """Return a new Number expressed in base scale (Scale.one).

        This normalizes the unit expression by removing all scale prefixes
        and adjusting the quantity accordingly. No conversion graph is needed
        since this is purely a scale transformation.

        Examples
        --------
        >>> from ucon import Scale, units
        >>> km = Scale.kilo * units.meter
        >>> km(5).simplify()
        <5000 m>
        >>> mg = Scale.milli * units.gram
        >>> mg(500).simplify()
        <0.5 g>
        """
        if not isinstance(self.unit, UnitProduct):
            # Plain Unit already has no scale
            return Number(quantity=self.quantity, unit=self.unit, uncertainty=self.uncertainty)

        # Compute the combined scale factor
        scale_factor = self.unit.fold_scale()

        # Create new unit with all factors at Scale.one
        base_factors: dict[UnitFactor, float] = {}
        for factor, exp in self.unit.factors.items():
            base_factor = UnitFactor(unit=factor.unit, scale=Scale.one)
            base_factors[base_factor] = exp

        base_unit = UnitProduct(base_factors)

        # Adjust quantity and uncertainty by the scale factor
        new_uncertainty = None
        if self.uncertainty is not None:
            new_uncertainty = self.uncertainty * abs(scale_factor)

        return Number(
            quantity=self.quantity * scale_factor,
            unit=base_unit,
            uncertainty=new_uncertainty,
        )

    def to(
        self,
        target,
        graph: "ConversionGraph | None" = None,
        propagate_factor_uncertainty: bool = False,
        *,
        system: "UnitSystem | None" = None,
    ):
        """Convert this Number to a different unit expression.

        Parameters
        ----------
        target : Unit, UnitProduct, or str
            The target unit to convert to. Strings are resolved via
            :func:`~ucon.resolver.parse_unit`, which supports bare names
            (``"foot"``), aliases (``"ft"``), scale prefixes (``"km"``),
            and composite expressions (``"m/s²"``).
        graph : ConversionGraph, optional
            The conversion graph to use. If not provided, uses the default graph.
        propagate_factor_uncertainty : bool, optional
            When ``True``, include the relative uncertainty of the conversion
            factor (from measured physical constants) in the result uncertainty
            via GUM quadrature.  Default ``False`` preserves backward
            compatibility — only measurement uncertainty is propagated.
        system : UnitSystem, optional
            When provided, routes through ``system.conversion_graph`` for graph
            lookups and ``system.units`` for string-target parsing. Takes
            precedence over ``graph=`` when both are given.

        Returns
        -------
        Number
            A new Number with the converted quantity and target unit.

        Examples
        --------
        >>> from ucon.units import meter, foot
        >>> length = meter(100)
        >>> length.to(foot)
        <328.084 ft>
        >>> length.to("ft")
        <328.084 ft>
        >>> length.to("km")
        <0.1 km>
        """
        # Resolve system and graph from ContextVars (no deferred imports).
        # _sys_active_var and _parsing_graph are Layer-1 leaf modules,
        # imported at top of this file. _sys_active_var holds an
        # ucon.system.ActiveContext; ``.system`` is the UnitSystem.
        if system is None:
            ctx = _sys_active_var.get()
            if ctx is None:
                raise RuntimeError(
                    "No active UnitSystem. This usually means Number.to() "
                    "was called before 'import ucon' completed."
                )
            system = ctx.system

        # Respect the 3-tier priority: context-local → active system → module default.
        if graph is None:
            graph = _parsing_graph.get() or system.conversion_graph

        # Resolve string targets via the system's resolver
        if isinstance(target, str):
            target = system.resolve_unit(target)

        # --- Fast path: plain Unit → plain Unit (no UnitProduct wrapping) ---
        src_unit = self.unit
        dst_unit = target

        src_is_plain = isinstance(src_unit, Unit) and not isinstance(src_unit, UnitProduct)
        dst_is_plain = isinstance(dst_unit, Unit) and not isinstance(dst_unit, UnitProduct)

        if not src_is_plain and isinstance(src_unit, UnitProduct) and len(src_unit.factors) == 1:
            uf, exp = next(iter(src_unit.factors.items()))
            if exp == 1.0 and uf.scale == Scale.one:
                src_is_plain = True
                src_unit = uf.unit

        if not dst_is_plain and isinstance(dst_unit, UnitProduct) and len(dst_unit.factors) == 1:
            uf, exp = next(iter(dst_unit.factors.items()))
            if exp == 1.0 and uf.scale == Scale.one:
                dst_is_plain = True
                dst_unit = uf.unit

        if src_is_plain and dst_is_plain and src_unit != dst_unit:
            # Strict source-unit resolution (v2.0 §3.4): under strict=True
            # (the default), require `src_unit` to be in `graph` by object
            # identity. Strict is a scope property, not a system property,
            # so the flag is read from the active context regardless of
            # whether `system=` / `graph=` was passed explicitly.
            _ctx = _sys_active_var.get()
            if _ctx is not None and _ctx.strict and not graph.contains_unit_by_identity(src_unit):
                raise UnitDefinitionMismatch(src_unit, graph=graph)
            conversion_map = graph.convert(src=src_unit, dst=dst_unit)
            converted = conversion_map(self.quantity)
            new_unc = None
            if self.uncertainty is not None or (
                propagate_factor_uncertainty and conversion_map.rel_uncertainty > 0
            ):
                dy_meas = abs(conversion_map.derivative(self.quantity)) * self.uncertainty \
                          if self.uncertainty is not None else 0.0
                dy_factor = abs(converted) * conversion_map.rel_uncertainty \
                            if propagate_factor_uncertainty else 0.0
                new_unc = math.sqrt(dy_meas**2 + dy_factor**2)
                if new_unc == 0.0:
                    new_unc = None
            return Number(quantity=converted, unit=target, uncertainty=new_unc, kind=self.kind)

        # --- General path: wrap into UnitProducts ---
        src = self.unit if isinstance(self.unit, UnitProduct) else UnitProduct.from_unit(self.unit)
        dst = target if isinstance(target, UnitProduct) else UnitProduct.from_unit(target)

        # Scale-only conversion (same base unit, different scale)
        if self._is_scale_only_conversion(src, dst):
            factor = src.fold_scale() / dst.fold_scale()
            new_uncertainty = None
            if self.uncertainty is not None:
                new_uncertainty = self.uncertainty * abs(factor)
            return Number(quantity=self.quantity * factor, unit=target, uncertainty=new_uncertainty, kind=self.kind)

        # Pass raw Units to graph.convert() when possible, so the graph
        # can use _convert_units() which handles cross-basis via rebased units.
        # UnitProducts only go through _convert_products() which lacks cross-basis support.
        graph_src: Union[Unit, UnitProduct] = src
        graph_dst: Union[Unit, UnitProduct] = dst
        if len(src.factors) == 1:
            uf, exp = next(iter(src.factors.items()))
            if exp == 1.0 and uf.scale == Scale.one:
                graph_src = uf.unit
        if len(dst.factors) == 1:
            uf, exp = next(iter(dst.factors.items()))
            if exp == 1.0 and uf.scale == Scale.one:
                graph_dst = uf.unit

        # Strict source-unit resolution (v2.0 §3.4) — mirror of fast-path
        # guard for general / UnitProduct sources. `contains_unit_by_identity`
        # descends into UnitProduct factors.
        _ctx = _sys_active_var.get()
        if _ctx is not None and _ctx.strict and not graph.contains_unit_by_identity(graph_src):
            raise UnitDefinitionMismatch(graph_src, graph=graph)

        conversion_map = graph.convert(src=graph_src, dst=graph_dst)
        # Use raw quantity - the conversion map handles scale via factorwise decomposition
        converted_quantity = conversion_map(self.quantity)

        # Account for residual scale factors from cancelled dimensions.
        # When units cancel (e.g., mcg/kg), the scale ratio goes into _residual_scale_factor.
        # The graph conversion only sees the remaining dimensions, so we must apply
        # the residual ratio here: src_residual / dst_residual.
        src_residual = getattr(src, '_residual_scale_factor', 1.0)
        dst_residual = getattr(dst, '_residual_scale_factor', 1.0)
        if src_residual != 1.0 or dst_residual != 1.0:
            converted_quantity *= (src_residual / dst_residual)

        # Propagate uncertainty through conversion using derivative
        new_uncertainty = None
        if self.uncertainty is not None or (
            propagate_factor_uncertainty and conversion_map.rel_uncertainty > 0
        ):
            derivative = abs(conversion_map.derivative(self.quantity))
            # Also apply residual scale to uncertainty
            if src_residual != 1.0 or dst_residual != 1.0:
                derivative *= abs(src_residual / dst_residual)
            dy_meas = derivative * self.uncertainty if self.uncertainty is not None else 0.0
            dy_factor = abs(converted_quantity) * conversion_map.rel_uncertainty \
                        if propagate_factor_uncertainty else 0.0
            new_uncertainty = math.sqrt(dy_meas**2 + dy_factor**2)
            if new_uncertainty == 0.0:
                new_uncertainty = None

        return Number(quantity=converted_quantity, unit=target, uncertainty=new_uncertainty, kind=self.kind)

    def _is_scale_only_conversion(self, src: UnitProduct, dst: UnitProduct) -> bool:
        """Check if conversion is just a scale change (same base units)."""
        if len(src.factors) != len(dst.factors):
            return False

        # Single-factor fast path: avoid building two dicts
        if len(src.factors) == 1:
            sf, se = next(iter(src.factors.items()))
            df, de = next(iter(dst.factors.items()))
            return sf.unit == df.unit and abs(se - de) < 1e-12

        src_by_dim = {}
        dst_by_dim = {}
        for f, exp in src.factors.items():
            src_by_dim[f.unit.dimension] = (f.unit, exp)
        for f, exp in dst.factors.items():
            dst_by_dim[f.unit.dimension] = (f.unit, exp)

        if src_by_dim.keys() != dst_by_dim.keys():
            return False

        for dim in src_by_dim:
            src_unit, src_exp = src_by_dim[dim]
            dst_unit, dst_exp = dst_by_dim[dim]
            if src_unit != dst_unit or abs(src_exp - dst_exp) > 1e-12:
                return False

        return True

    def as_ratio(self):
        return Ratio(self)

    def __mul__(self, other: _Quantifiable) -> 'Number':
        if isinstance(other, Ratio):
            other = other.evaluate()

        # Scalar multiplication
        if isinstance(other, (int, float)):
            new_uncertainty = None
            if self.uncertainty is not None:
                new_uncertainty = abs(other) * self.uncertainty
            return Number(
                quantity=self.quantity * other,
                unit=self.unit,
                uncertainty=new_uncertainty,
            )

        if not isinstance(other, Number):
            return NotImplemented

        # Uncertainty propagation for multiplication
        # δc = |c| * sqrt((δa/a)² + (δb/b)²)
        new_uncertainty = None
        result_quantity = self.quantity * other.quantity
        if self.uncertainty is not None or other.uncertainty is not None:
            rel_a = (self.uncertainty / abs(self.quantity)) if (self.uncertainty and self.quantity != 0) else 0
            rel_b = (other.uncertainty / abs(other.quantity)) if (other.uncertainty and other.quantity != 0) else 0
            rel_c = math.sqrt(rel_a**2 + rel_b**2)
            new_uncertainty = abs(result_quantity) * rel_c if rel_c > 0 else None

        return Number(
            quantity=result_quantity,
            unit=self.unit * other.unit,
            uncertainty=new_uncertainty,
        )

    def __add__(self, other: 'Number') -> 'Number':
        if not isinstance(other, Number):
            return NotImplemented

        # Dimensions must match for addition
        if self.unit.dimension != other.unit.dimension:
            raise TypeError(
                f"Cannot add Numbers with different dimensions: "
                f"{self.unit.dimension} vs {other.unit.dimension}"
            )

        # Uncertainty propagation for addition: δc = sqrt(δa² + δb²)
        new_uncertainty = None
        if self.uncertainty is not None or other.uncertainty is not None:
            ua = self.uncertainty if self.uncertainty is not None else 0
            ub = other.uncertainty if other.uncertainty is not None else 0
            new_uncertainty = math.sqrt(ua**2 + ub**2)

        return Number(
            quantity=self.quantity + other.quantity,
            unit=self.unit,
            uncertainty=new_uncertainty,
        )

    def __sub__(self, other: 'Number') -> 'Number':
        if not isinstance(other, Number):
            return NotImplemented

        # Dimensions must match for subtraction
        if self.unit.dimension != other.unit.dimension:
            raise TypeError(
                f"Cannot subtract Numbers with different dimensions: "
                f"{self.unit.dimension} vs {other.unit.dimension}"
            )

        # Uncertainty propagation for subtraction: δc = sqrt(δa² + δb²)
        new_uncertainty = None
        if self.uncertainty is not None or other.uncertainty is not None:
            ua = self.uncertainty if self.uncertainty is not None else 0
            ub = other.uncertainty if other.uncertainty is not None else 0
            new_uncertainty = math.sqrt(ua**2 + ub**2)

        return Number(
            quantity=self.quantity - other.quantity,
            unit=self.unit,
            uncertainty=new_uncertainty,
        )

    def __truediv__(self, other: _Quantifiable) -> "Number":
        # Allow dividing by a Ratio (interpret as its evaluated Number)
        if isinstance(other, Ratio):
            other = other.evaluate()

        # Scalar division
        if isinstance(other, (int, float)):
            new_uncertainty = None
            if self.uncertainty is not None:
                new_uncertainty = self.uncertainty / abs(other)
            return Number(
                quantity=self.quantity / other,
                unit=self.unit,
                uncertainty=new_uncertainty,
            )

        if not isinstance(other, Number):
            raise TypeError(f"Cannot divide Number by non-Number/Ratio type: {type(other)}")

        # Symbolic quotient in the unit algebra
        unit_quot = self.unit / other.unit

        # Uncertainty propagation for division
        # δc = |c| * sqrt((δa/a)² + (δb/b)²)
        def compute_uncertainty(result_quantity):
            if self.uncertainty is None and other.uncertainty is None:
                return None
            rel_a = (self.uncertainty / abs(self.quantity)) if (self.uncertainty and self.quantity != 0) else 0
            rel_b = (other.uncertainty / abs(other.quantity)) if (other.uncertainty and other.quantity != 0) else 0
            rel_c = math.sqrt(rel_a**2 + rel_b**2)
            return abs(result_quantity) * rel_c if rel_c > 0 else None

        # --- Case 1: Dimensionless result ----------------------------------
        # If the net dimension is none, we want a pure scalar:
        # fold *all* scale factors into the numeric magnitude.
        if not unit_quot.dimension:
            num = self._canonical_magnitude
            den = other._canonical_magnitude
            result = num / den
            return Number(quantity=result, unit=_none, uncertainty=compute_uncertainty(result))

        # --- Case 2: Dimensionful result -----------------------------------
        # For "real" physical results like g/mL, m/s², etc., preserve the
        # user's chosen unit scales symbolically. Only divide the raw quantities.
        new_quantity = self.quantity / other.quantity
        return Number(quantity=new_quantity, unit=unit_quot, uncertainty=compute_uncertainty(new_quantity))

    def __eq__(self, other: _Quantifiable) -> bool:
        if not isinstance(other, (Number, Ratio)):
            raise TypeError(
                f"Cannot compare Number to non-Number/Ratio type: {type(other)}"
            )

        # If comparing with a Ratio, evaluate it to a Number
        if isinstance(other, Ratio):
            other = other.evaluate()

        # Dimensions must match
        if self.unit.dimension != other.unit.dimension:
            return False

        # Compare magnitudes, scale-adjusted
        if abs(self._canonical_magnitude - other._canonical_magnitude) >= 1e-12:
            return False

        return True

    def __pow__(self, power: Union[int, float]) -> 'Number':
        """Raise Number to a power.

        Examples
        --------
        >>> from ucon import units
        >>> v = units.meter(3) / units.second(1)
        >>> v ** 2
        <9 m²/s²>
        """
        new_quantity = self.quantity ** power
        new_unit = self.unit ** power

        # Uncertainty propagation: δ(x^n) = |n| * x^(n-1) * δx = |n| * (x^n / x) * δx
        new_uncertainty = None
        if self.uncertainty is not None and self.quantity != 0:
            new_uncertainty = abs(power) * abs(new_quantity / self.quantity) * self.uncertainty

        return Number(
            quantity=new_quantity,
            unit=new_unit,
            uncertainty=new_uncertainty,
        )

    def __repr__(self):
        if self.uncertainty is not None:
            if not self.unit.dimension:
                return f"<{self.quantity} ± {self.uncertainty}>"
            return f"<{self.quantity} ± {self.uncertainty} {self.unit.shorthand}>"
        if not self.unit.dimension:
            return f"<{self.quantity}>"
        return f"<{self.quantity} {self.unit.shorthand}>"


class Ratio:
    """
    Represents a **ratio of two Numbers**, preserving their unit semantics.

    Useful for expressing physical relationships like efficiency, density,
    or dimensionless comparisons:

        >>> ratio = Ratio(length, time)
        >>> ratio.evaluate()
        <2.5 m/s>
    """
    def __init__(self, numerator: Number = None, denominator: Number = None):
        self.numerator = numerator if numerator is not None else Number()
        self.denominator = denominator if denominator is not None else Number()

    def reciprocal(self) -> 'Ratio':
        return Ratio(numerator=self.denominator, denominator=self.numerator)

    def evaluate(self) -> "Number":
        """Evaluate the ratio to a Number.

        Uses Exponent-derived arithmetic for scale handling:
        - If the result is dimensionless (units cancel), scales are folded
          into the magnitude using _canonical_magnitude.
        - If the result is dimensionful, raw quantities are divided and
          unit scales are preserved symbolically.

        This matches the behavior of Number.__truediv__ for consistency.
        """
        # Symbolic quotient in the unit algebra
        unit = self.numerator.unit / self.denominator.unit

        # Dimensionless result: fold all scale factors into magnitude
        if not unit.dimension:
            num = self.numerator._canonical_magnitude
            den = self.denominator._canonical_magnitude
            return Number(quantity=num / den, unit=_none)

        # Dimensionful result: preserve user's chosen scales symbolically
        numeric = self.numerator.quantity / self.denominator.quantity
        return Number(quantity=numeric, unit=unit)

    def __mul__(self, another_ratio: 'Ratio') -> 'Ratio':
        if self.numerator.unit == another_ratio.denominator.unit:
            factor = self.numerator / another_ratio.denominator
            numerator, denominator = factor * another_ratio.numerator, self.denominator
        elif self.denominator.unit == another_ratio.numerator.unit:
            factor = another_ratio.numerator / self.denominator
            numerator, denominator = factor * self.numerator, another_ratio.denominator
        else:
            factor = Number()
            another_number = another_ratio.evaluate()
            numerator, denominator = self.numerator * another_number, self.denominator
        return Ratio(numerator=numerator, denominator=denominator)

    def __truediv__(self, another_ratio: 'Ratio') -> 'Ratio':
        return Ratio(
            numerator=self.numerator * another_ratio.denominator,
            denominator=self.denominator * another_ratio.numerator,
        )

    def __eq__(self, another_ratio: 'Ratio') -> bool:
        if isinstance(another_ratio, Ratio):
            return self.evaluate() == another_ratio.evaluate()
        elif isinstance(another_ratio, Number):
            return self.evaluate() == another_ratio
        else:
            raise ValueError(f'"{another_ratio}" is not a Ratio or Number. Comparison not possible.')

    def __repr__(self):
        return f'{self.evaluate()}' if self.numerator == self.denominator else f'{self.numerator} / {self.denominator}'


# =====================================================================
# NumberArray (soft numpy dependency)
# =====================================================================

# Module-level cache for scale factors: (src_unit, dst_unit) -> factor
_scale_factor_cache: dict[tuple, float] = {}

# Module-level cache for unit multiplication: (unit_a, unit_b) -> result_unit
_unit_mul_cache: dict[tuple, 'UnitProduct'] = {}

# Module-level cache for unit division: (unit_a, unit_b) -> result_unit
_unit_div_cache: dict[tuple, 'UnitProduct'] = {}


def _require_numpy() -> None:
    """Raise ImportError if numpy is not available."""
    if not _HAS_NUMPY:
        raise ImportError(
            "NumPy is required for NumberArray. "
            "Install with: pip install ucon[numpy]"
        )


class NumberArray:
    """
    A collection of quantities with a shared unit.

    Combines a numpy array of magnitudes with a unit, enabling vectorized
    arithmetic and conversion.

    Parameters
    ----------
    quantities : array-like
        The numeric values (will be converted to numpy array).
    unit : Unit or UnitProduct, optional
        The unit for all quantities. Defaults to dimensionless.
    uncertainty : float or array-like, optional
        Uncertainty value(s). If scalar, applies uniformly to all elements.
        If array-like, must match the shape of quantities.

    Examples
    --------
    >>> from ucon import units
    >>> from ucon.numpy import NumberArray

    Create from list:

    >>> heights = NumberArray([1.7, 1.8, 1.9], unit=units.meter)
    >>> len(heights)
    3

    Vectorized conversion:

    >>> heights_ft = heights.to(units.foot)
    >>> heights_ft[0].quantity  # doctest: +ELLIPSIS
    5.577...

    With uniform uncertainty:

    >>> temps = NumberArray([20, 21, 22], unit=units.celsius, uncertainty=0.5)

    With per-element uncertainty:

    >>> measurements = NumberArray([1.0, 2.0, 3.0], unit=units.meter,
    ...                            uncertainty=[0.01, 0.02, 0.015])
    """

    __slots__ = ('_quantities', '_unit', '_uncertainty')

    def __init__(
        self,
        quantities: 'ArrayLike',
        unit: Union[Unit, UnitProduct, None] = None,
        uncertainty: Union[float, 'ArrayLike', None] = None,
    ):
        _require_numpy()

        self._quantities: NDArray[np.floating] = np.asarray(quantities, dtype=float)
        self._unit = unit if unit is not None else _none

        if uncertainty is not None:
            if isinstance(uncertainty, (int, float)):
                self._uncertainty: Union[float, NDArray[np.floating], None] = float(uncertainty)
            else:
                self._uncertainty = np.asarray(uncertainty, dtype=float)
                if self._uncertainty.shape != self._quantities.shape:
                    raise ValueError(
                        f"Uncertainty shape {self._uncertainty.shape} does not match "
                        f"quantities shape {self._quantities.shape}"
                    )
        else:
            self._uncertainty = None

    @property
    def quantities(self) -> 'NDArray[np.floating]':
        """The array of numeric values."""
        return self._quantities

    @property
    def unit(self) -> Union[Unit, UnitProduct]:
        """The unit shared by all quantities."""
        return self._unit

    @property
    def uncertainty(self) -> Union[float, 'NDArray[np.floating]', None]:
        """The uncertainty (scalar or per-element array)."""
        return self._uncertainty

    def __len__(self) -> int:
        """Return the number of elements."""
        return len(self._quantities)

    @property
    def shape(self) -> tuple:
        """Shape of the quantities array."""
        return self._quantities.shape

    @property
    def ndim(self) -> int:
        """Number of dimensions."""
        return self._quantities.ndim

    @property
    def dtype(self) -> 'np.dtype':
        """Data type of the quantities array."""
        return self._quantities.dtype

    @property
    def dimension(self):
        """The physical dimension of the quantities."""
        if hasattr(self._unit, 'dimension'):
            return self._unit.dimension
        return None

    def __getitem__(self, key) -> Union[Number, 'NumberArray']:
        """Index or slice the array.

        Returns Number for scalar index, NumberArray for slice.
        """
        q = self._quantities[key]

        # Determine uncertainty for the slice
        if self._uncertainty is None:
            unc = None
        elif isinstance(self._uncertainty, float):
            unc = self._uncertainty
        else:
            unc = self._uncertainty[key]

        # Return Number for scalar index, NumberArray for slice
        if np.ndim(q) == 0:
            unc_val = float(unc) if unc is not None and not isinstance(unc, float) else unc
            return Number(quantity=float(q), unit=self._unit, uncertainty=unc_val)
        else:
            return NumberArray(quantities=q, unit=self._unit, uncertainty=unc)

    def __iter__(self) -> Iterator[Number]:
        """Iterate as Number instances."""
        for i in range(len(self)):
            yield self[i]  # type: ignore

    def __repr__(self) -> str:
        """String representation with truncation for large arrays."""
        # Format quantities with truncation for large arrays
        if len(self._quantities) <= 6:
            q_str = np.array2string(
                self._quantities,
                separator=', ',
                precision=4,
                suppress_small=True,
            )
        else:
            # Show first 3 and last 3
            head = ', '.join(f'{x:.4g}' for x in self._quantities[:3])
            tail = ', '.join(f'{x:.4g}' for x in self._quantities[-3:])
            q_str = f'[{head}, ..., {tail}]'

        # Format unit
        unit_str = self._format_unit()

        # Format uncertainty
        if self._uncertainty is None:
            return f'<{q_str} {unit_str}>'
        elif isinstance(self._uncertainty, float):
            return f'<{q_str} \u00b1 {self._uncertainty:.4g} {unit_str}>'
        else:
            # Per-element uncertainty - show shape indicator
            return f'<{q_str} \u00b1 [...] {unit_str}>'

    def _format_unit(self) -> str:
        """Format the unit for display."""
        if hasattr(self._unit, 'shorthand') and self._unit.shorthand:
            return self._unit.shorthand
        elif hasattr(self._unit, 'name'):
            return self._unit.name
        else:
            return str(self._unit)

    # -------------------------------------------------------------------------
    # Arithmetic Operations
    # -------------------------------------------------------------------------

    def __mul__(self, other) -> 'NumberArray':
        """Multiply by scalar, Number, or NumberArray."""
        if isinstance(other, (int, float)):
            new_unc = None
            if self._uncertainty is not None:
                new_unc = self._uncertainty * abs(other)
            return NumberArray(
                quantities=self._quantities * other,
                unit=self._unit,
                uncertainty=new_unc,
            )

        if isinstance(other, Number):
            result_q = self._quantities * other.quantity
            result_unit = self._unit * other.unit

            new_unc = self._propagate_mul_uncertainty(
                self._quantities, self._uncertainty,
                other.quantity, other.uncertainty
            )
            return NumberArray(quantities=result_q, unit=result_unit, uncertainty=new_unc)

        if isinstance(other, NumberArray):
            # Allow numpy broadcasting - shapes must be broadcast-compatible
            try:
                result_q = self._quantities * other._quantities
            except ValueError as e:
                raise ValueError(
                    f"Shapes {self.shape} and {other.shape} are not broadcast-compatible"
                ) from e

            # Cache unit multiplication (expensive due to UnitProduct.__init__)
            unit_key = (self._unit, other._unit)
            if unit_key in _unit_mul_cache:
                result_unit = _unit_mul_cache[unit_key]
            else:
                result_unit = self._unit * other._unit
                _unit_mul_cache[unit_key] = result_unit

            new_unc = self._propagate_mul_uncertainty(
                self._quantities, self._uncertainty,
                other._quantities, other._uncertainty
            )
            return NumberArray(quantities=result_q, unit=result_unit, uncertainty=new_unc)

        return NotImplemented

    def __rmul__(self, other) -> 'NumberArray':
        """Right multiplication."""
        return self.__mul__(other)

    def __truediv__(self, other) -> 'NumberArray':
        """Divide by scalar, Number, or NumberArray."""
        if isinstance(other, (int, float)):
            new_unc = None
            if self._uncertainty is not None:
                new_unc = self._uncertainty / abs(other)
            return NumberArray(
                quantities=self._quantities / other,
                unit=self._unit,
                uncertainty=new_unc,
            )

        if isinstance(other, Number):
            result_q = self._quantities / other.quantity
            result_unit = self._unit / other.unit

            new_unc = self._propagate_div_uncertainty(
                self._quantities, self._uncertainty,
                other.quantity, other.uncertainty
            )
            return NumberArray(quantities=result_q, unit=result_unit, uncertainty=new_unc)

        if isinstance(other, NumberArray):
            # Allow numpy broadcasting - shapes must be broadcast-compatible
            try:
                result_q = self._quantities / other._quantities
            except ValueError as e:
                raise ValueError(
                    f"Shapes {self.shape} and {other.shape} are not broadcast-compatible"
                ) from e

            # Cache unit division (expensive due to UnitProduct.__init__)
            unit_key = (self._unit, other._unit)
            if unit_key in _unit_div_cache:
                result_unit = _unit_div_cache[unit_key]
            else:
                result_unit = self._unit / other._unit
                _unit_div_cache[unit_key] = result_unit

            new_unc = self._propagate_div_uncertainty(
                self._quantities, self._uncertainty,
                other._quantities, other._uncertainty
            )
            return NumberArray(quantities=result_q, unit=result_unit, uncertainty=new_unc)

        return NotImplemented

    def __rtruediv__(self, other) -> 'NumberArray':
        """Right division (other / self)."""
        if isinstance(other, (int, float)):
            result_q = other / self._quantities

            new_unc = None
            if self._uncertainty is not None:
                # For c = a/x, δc = |c| * |δx/x|
                rel_unc = np.where(
                    self._quantities != 0,
                    np.abs(self._uncertainty / self._quantities),
                    0
                )
                new_unc = np.abs(result_q) * rel_unc

            # Unit is 1/self.unit
            inv_unit = _none / self._unit
            return NumberArray(quantities=result_q, unit=inv_unit, uncertainty=new_unc)

        return NotImplemented

    def __add__(self, other) -> 'NumberArray':
        """Add NumberArray or Number (same unit required)."""
        if isinstance(other, Number):
            self._check_same_unit(other.unit)
            result_q = self._quantities + other.quantity
            new_unc = self._propagate_add_uncertainty(
                self._uncertainty, other.uncertainty
            )
            return NumberArray(quantities=result_q, unit=self._unit, uncertainty=new_unc)

        if isinstance(other, NumberArray):
            self._check_same_unit(other._unit)
            # Allow numpy broadcasting - shapes must be broadcast-compatible
            try:
                result_q = self._quantities + other._quantities
            except ValueError as e:
                raise ValueError(
                    f"Shapes {self.shape} and {other.shape} are not broadcast-compatible"
                ) from e

            new_unc = self._propagate_add_uncertainty(
                self._uncertainty, other._uncertainty
            )
            return NumberArray(quantities=result_q, unit=self._unit, uncertainty=new_unc)

        return NotImplemented

    def __radd__(self, other) -> 'NumberArray':
        """Right addition."""
        return self.__add__(other)

    def __sub__(self, other) -> 'NumberArray':
        """Subtract NumberArray or Number (same unit required)."""
        if isinstance(other, Number):
            self._check_same_unit(other.unit)
            result_q = self._quantities - other.quantity
            new_unc = self._propagate_add_uncertainty(
                self._uncertainty, other.uncertainty
            )
            return NumberArray(quantities=result_q, unit=self._unit, uncertainty=new_unc)

        if isinstance(other, NumberArray):
            self._check_same_unit(other._unit)
            # Allow numpy broadcasting - shapes must be broadcast-compatible
            try:
                result_q = self._quantities - other._quantities
            except ValueError as e:
                raise ValueError(
                    f"Shapes {self.shape} and {other.shape} are not broadcast-compatible"
                ) from e

            new_unc = self._propagate_add_uncertainty(
                self._uncertainty, other._uncertainty
            )
            return NumberArray(quantities=result_q, unit=self._unit, uncertainty=new_unc)

        return NotImplemented

    def __rsub__(self, other) -> 'NumberArray':
        """Right subtraction (other - self)."""
        if isinstance(other, Number):
            self._check_same_unit(other.unit)
            result_q = other.quantity - self._quantities
            new_unc = self._propagate_add_uncertainty(
                other.uncertainty, self._uncertainty
            )
            return NumberArray(quantities=result_q, unit=self._unit, uncertainty=new_unc)

        return NotImplemented

    def __neg__(self) -> 'NumberArray':
        """Negation."""
        return NumberArray(
            quantities=-self._quantities,
            unit=self._unit,
            uncertainty=self._uncertainty,
        )

    def __pos__(self) -> 'NumberArray':
        """Unary positive (returns copy)."""
        return NumberArray(
            quantities=self._quantities.copy(),
            unit=self._unit,
            uncertainty=self._uncertainty if isinstance(self._uncertainty, float)
                        else self._uncertainty.copy() if self._uncertainty is not None
                        else None,
        )

    def __abs__(self) -> 'NumberArray':
        """Absolute value."""
        return NumberArray(
            quantities=np.abs(self._quantities),
            unit=self._unit,
            uncertainty=self._uncertainty,
        )

    # -------------------------------------------------------------------------
    # Comparison Operators
    # -------------------------------------------------------------------------

    def __eq__(self, other) -> 'NDArray[np.bool_]':
        """Element-wise equality comparison. Returns boolean array."""
        if isinstance(other, NumberArray):
            self._check_same_unit(other._unit)
            return self._quantities == other._quantities
        if isinstance(other, Number):
            self._check_same_unit(other.unit)
            return self._quantities == other.quantity
        if isinstance(other, (int, float)):
            return self._quantities == other
        return NotImplemented

    def __ne__(self, other) -> 'NDArray[np.bool_]':
        """Element-wise inequality comparison. Returns boolean array."""
        if isinstance(other, NumberArray):
            self._check_same_unit(other._unit)
            return self._quantities != other._quantities
        if isinstance(other, Number):
            self._check_same_unit(other.unit)
            return self._quantities != other.quantity
        if isinstance(other, (int, float)):
            return self._quantities != other
        return NotImplemented

    def __lt__(self, other) -> 'NDArray[np.bool_]':
        """Element-wise less-than comparison. Returns boolean array."""
        if isinstance(other, NumberArray):
            self._check_same_unit(other._unit)
            return self._quantities < other._quantities
        if isinstance(other, Number):
            self._check_same_unit(other.unit)
            return self._quantities < other.quantity
        if isinstance(other, (int, float)):
            return self._quantities < other
        return NotImplemented

    def __le__(self, other) -> 'NDArray[np.bool_]':
        """Element-wise less-than-or-equal comparison. Returns boolean array."""
        if isinstance(other, NumberArray):
            self._check_same_unit(other._unit)
            return self._quantities <= other._quantities
        if isinstance(other, Number):
            self._check_same_unit(other.unit)
            return self._quantities <= other.quantity
        if isinstance(other, (int, float)):
            return self._quantities <= other
        return NotImplemented

    def __gt__(self, other) -> 'NDArray[np.bool_]':
        """Element-wise greater-than comparison. Returns boolean array."""
        if isinstance(other, NumberArray):
            self._check_same_unit(other._unit)
            return self._quantities > other._quantities
        if isinstance(other, Number):
            self._check_same_unit(other.unit)
            return self._quantities > other.quantity
        if isinstance(other, (int, float)):
            return self._quantities > other
        return NotImplemented

    def __ge__(self, other) -> 'NDArray[np.bool_]':
        """Element-wise greater-than-or-equal comparison. Returns boolean array."""
        if isinstance(other, NumberArray):
            self._check_same_unit(other._unit)
            return self._quantities >= other._quantities
        if isinstance(other, Number):
            self._check_same_unit(other.unit)
            return self._quantities >= other.quantity
        if isinstance(other, (int, float)):
            return self._quantities >= other
        return NotImplemented

    def _check_same_unit(self, other_unit) -> None:
        """Raise ValueError if units don't match for addition/subtraction."""
        if self._unit != other_unit:
            raise ValueError(
                f"Cannot add/subtract quantities with different units: "
                f"{self._format_unit()} vs {other_unit}"
            )

    def _propagate_mul_uncertainty(
        self,
        a: 'NDArray',
        ua: Union[float, 'NDArray', None],
        b: Union[float, 'NDArray'],
        ub: Union[float, None],
    ) -> Union[float, 'NDArray', None]:
        """Propagate uncertainty through multiplication."""
        if ua is None and ub is None:
            return None

        # Convert to arrays for uniform handling
        a_arr = np.asarray(a)
        b_arr = np.asarray(b)

        # Relative uncertainties
        if ua is not None:
            rel_a = np.where(a_arr != 0, np.abs(ua) / np.abs(a_arr), 0.0)
        else:
            rel_a = np.zeros_like(a_arr)

        if ub is not None:
            rel_b = np.where(b_arr != 0, np.abs(ub) / np.abs(b_arr), 0.0)
        else:
            rel_b = np.zeros_like(b_arr)

        rel_c = np.sqrt(rel_a**2 + rel_b**2)
        result = np.abs(a_arr * b_arr) * rel_c

        # Return scalar if result is uniform and both inputs were scalar uncertainty
        if isinstance(ua, (float, type(None))) and isinstance(ub, (float, type(None))):
            if result.size == 1:
                return float(result.flat[0])
            if np.allclose(result, result.flat[0]):
                return float(result.flat[0])

        return result

    def _propagate_div_uncertainty(
        self,
        a: 'NDArray',
        ua: Union[float, 'NDArray', None],
        b: Union[float, 'NDArray'],
        ub: Union[float, None],
    ) -> Union[float, 'NDArray', None]:
        """Propagate uncertainty through division (same as multiplication)."""
        return self._propagate_mul_uncertainty(a, ua, b, ub)

    def _propagate_add_uncertainty(
        self,
        ua: Union[float, 'NDArray', None],
        ub: Union[float, 'NDArray', None],
    ) -> Union[float, 'NDArray', None]:
        """Propagate uncertainty through addition/subtraction."""
        if ua is None and ub is None:
            return None

        if ua is None:
            return ub
        if ub is None:
            return ua

        # Quadrature addition
        result = np.sqrt(np.asarray(ua)**2 + np.asarray(ub)**2)

        # Return scalar if both inputs were scalar
        if isinstance(ua, float) and isinstance(ub, float):
            return float(result)

        return result

    # -------------------------------------------------------------------------
    # Conversion
    # -------------------------------------------------------------------------

    def to(self, target: Union[Unit, UnitProduct], graph=None) -> 'NumberArray':
        """Convert all quantities to a different unit.

        Parameters
        ----------
        target : Unit or UnitProduct
            The target unit to convert to.
        graph : ConversionGraph, optional
            The conversion graph to use. Defaults to the global default graph.

        Returns
        -------
        NumberArray
            A new NumberArray with converted quantities.

        Examples
        --------
        >>> from ucon import units
        >>> heights = NumberArray([1, 2, 3], unit=units.meter)
        >>> heights_ft = heights.to(units.foot)
        """
        # Check scale factor cache first
        cache_key = (self._unit, target)
        if cache_key in _scale_factor_cache:
            factor = _scale_factor_cache[cache_key]
            new_unc = None
            if self._uncertainty is not None:
                new_unc = self._uncertainty * abs(factor)
            return NumberArray(
                quantities=self._quantities * factor,
                unit=target,
                uncertainty=new_unc,
            )

        # Normalize to UnitProduct
        src = self._unit if isinstance(self._unit, UnitProduct) else UnitProduct.from_unit(self._unit)
        dst = target if isinstance(target, UnitProduct) else UnitProduct.from_unit(target)

        # Scale-only conversion (no graph needed)
        if self._is_scale_only_conversion(src, dst):
            factor = src.fold_scale() / dst.fold_scale()
            _scale_factor_cache[cache_key] = factor  # Cache it
            new_unc = None
            if self._uncertainty is not None:
                new_unc = self._uncertainty * abs(factor)
            return NumberArray(
                quantities=self._quantities * factor,
                unit=target,
                uncertainty=new_unc,
            )

        # Graph-based conversion
        if graph is None:
            graph = _parsing_graph.get()
            if graph is None:
                ctx = _sys_active_var.get()
                if ctx is None:
                    raise RuntimeError(
                        "No active UnitSystem. This usually means NumberArray.to() "
                        "was called before 'import ucon' completed."
                    )
                graph = ctx.system.conversion_graph

        # Strict source-unit resolution (v2.0 §3.4): mirror of Number.to.
        _ctx = _sys_active_var.get()
        if _ctx is not None and _ctx.strict and not graph.contains_unit_by_identity(src):
            raise UnitDefinitionMismatch(src, graph=graph)

        conversion_map = graph.convert(src=src, dst=dst)

        # Apply map to array
        converted = conversion_map(self._quantities)

        # Propagate uncertainty through conversion
        new_unc = None
        if self._uncertainty is not None:
            derivative = np.abs(conversion_map.derivative(self._quantities))
            new_unc = derivative * self._uncertainty

        return NumberArray(quantities=converted, unit=target, uncertainty=new_unc)

    def _is_scale_only_conversion(self, src: UnitProduct, dst: UnitProduct) -> bool:
        """Check if conversion is just a scale change (same base units)."""
        if len(src.factors) != len(dst.factors):
            return False

        src_by_dim = {}
        dst_by_dim = {}
        for f, exp in src.factors.items():
            src_by_dim[f.unit.dimension] = (f.unit, exp)
        for f, exp in dst.factors.items():
            dst_by_dim[f.unit.dimension] = (f.unit, exp)

        if src_by_dim.keys() != dst_by_dim.keys():
            return False

        for dim in src_by_dim:
            src_unit, src_exp = src_by_dim[dim]
            dst_unit, dst_exp = dst_by_dim[dim]
            if src_unit != dst_unit or abs(src_exp - dst_exp) > 1e-12:
                return False

        return True

    # -------------------------------------------------------------------------
    # NumPy Integration
    # -------------------------------------------------------------------------

    def __array__(self, dtype=None) -> 'NDArray':
        """Support np.asarray(number_array)."""
        if dtype is None:
            return self._quantities
        return self._quantities.astype(dtype)

    def sum(self) -> Number:
        """Sum all quantities."""
        total = float(np.sum(self._quantities))

        # Uncertainty propagation for sum
        unc = None
        if self._uncertainty is not None:
            if isinstance(self._uncertainty, float):
                # Uniform uncertainty: σ_sum = σ * sqrt(n)
                unc = self._uncertainty * math.sqrt(len(self))
            else:
                # Per-element: σ_sum = sqrt(Σσᵢ²)
                unc = float(np.sqrt(np.sum(self._uncertainty**2)))

        return Number(quantity=total, unit=self._unit, uncertainty=unc)

    def mean(self) -> Number:
        """Compute the mean."""
        avg = float(np.mean(self._quantities))

        # Uncertainty propagation for mean
        unc = None
        if self._uncertainty is not None:
            if isinstance(self._uncertainty, float):
                # Uniform uncertainty: σ_mean = σ / sqrt(n)
                unc = self._uncertainty / math.sqrt(len(self))
            else:
                # Per-element: σ_mean = sqrt(Σσᵢ²) / n
                unc = float(np.sqrt(np.sum(self._uncertainty**2)) / len(self))

        return Number(quantity=avg, unit=self._unit, uncertainty=unc)

    def std(self, ddof: int = 0) -> Number:
        """Compute the standard deviation."""
        s = float(np.std(self._quantities, ddof=ddof))
        return Number(quantity=s, unit=self._unit, uncertainty=None)

    def min(self) -> Number:
        """Return the minimum value."""
        idx = np.argmin(self._quantities)
        return self[idx]  # type: ignore

    def max(self) -> Number:
        """Return the maximum value."""
        idx = np.argmax(self._quantities)
        return self[idx]  # type: ignore
