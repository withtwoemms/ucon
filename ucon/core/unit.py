# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
ucon.core.unit
==============

Unit types: :class:`Unit`, :class:`RebasedUnit`, :class:`UnitFactor`,
and :class:`BaseForm`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ucon.basis import Basis, BasisGraph
from ucon.core.scale import Scale
from ucon.dimension import Dimension, NONE

if TYPE_CHECKING:
    from ucon.core.product import UnitProduct
    from ucon.core.quantity import Number

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    np = None  # type: ignore[assignment]
    _HAS_NUMPY = False


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
        from ucon.core.product import UnitProduct

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
        from ucon.core.product import UnitProduct

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
        from ucon.core.product import UnitProduct
        return UnitProduct({self: power})

    # ----------------- equality & hashing -----------------

    def __eq__(self, other):
        from ucon.core.product import UnitProduct

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
        from ucon.core.product import UnitProduct
        from ucon.core.quantity import Number

        # Check for array-like inputs
        if _HAS_NUMPY and (
            isinstance(quantity, np.ndarray)
            or (isinstance(quantity, (list, tuple)) and len(quantity) > 0)
        ):
            from ucon.integrations.numpy import NumberArray
            return NumberArray(quantities=quantity, unit=self, uncertainty=uncertainty)

        return Number(quantity=quantity, unit=UnitProduct.from_unit(self), uncertainty=uncertainty)


# --------------------------------------------------------------------------------------
# RebasedUnit
# --------------------------------------------------------------------------------------

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
