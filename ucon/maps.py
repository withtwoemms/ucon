# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
ucon.maps
=========

Implements the **Map** class hierarchy — the composable substrate for
all unit conversion morphisms in *ucon*.

Classes
-------
- :class:`Map` — Abstract base for conversion morphisms.
- :class:`LinearMap` — y = a * x
- :class:`AffineMap` — y = a * x + b
- :class:`LogMap` — y = scale * log_base(x) + offset
- :class:`ExpMap` — y = base^(scale * x + offset)
- :class:`ReciprocalMap` — y = a / x (inversely proportional)
- :class:`PolynomialMap` — y = a0 + a1*x + ... + an*x**n over a declared domain
- :class:`PolynomialInverseMap` — the branch of a polynomial's inverse that is
  single-valued on that domain
- :class:`ComposedMap` — Generic composition fallback: g(f(x))

All maps support both scalar and numpy array inputs. NumPy is optional;
scalar operations use the standard library `math` module.
"""
from __future__ import annotations

__all__ = [
    'Map',
    'LinearMap',
    'AffineMap',
    'LogMap',
    'ExpMap',
    'ReciprocalMap',
    'PolynomialMap',
    'PolynomialInverseMap',
    'ComposedMap',
    'NonMonotoneOnDomain',
]

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Union, TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray
    Numeric = Union[float, NDArray[np.floating]]

# --- lazy numpy accessor ---
_np = None
_np_checked = False


def _get_numpy():
    """Return the numpy module if available, else None. Cached after first call."""
    global _np, _np_checked
    if not _np_checked:
        try:
            import numpy
            _np = numpy
        except ImportError:
            pass
        _np_checked = True
    return _np


def _is_array(x) -> bool:
    """Check if x is a numpy array."""
    np = _get_numpy()
    return np is not None and isinstance(x, np.ndarray)


def _log(x, base: float):
    """Logarithm that works with both scalars and numpy arrays."""
    np = _get_numpy()
    if np is not None and isinstance(x, np.ndarray):
        return np.log(x) / np.log(base)
    return math.log(x, base)


def _exp(base: float, x):
    """Exponentiation that works with both scalars and numpy arrays."""
    np = _get_numpy()
    if np is not None and isinstance(x, np.ndarray):
        return np.power(base, x)
    return base ** x


def _validate_positive(x, name: str = "x") -> None:
    """Validate that x is positive (for logarithm arguments)."""
    np = _get_numpy()
    if np is not None and isinstance(x, np.ndarray):
        if np.any(x <= 0):
            raise ValueError(f"Logarithm argument must be positive")
        return
    if x <= 0:
        raise ValueError(f"Logarithm argument must be positive, got {x}")


# --- polynomial helpers ---
#
# Coefficients are **ascending**: ``coeffs[i]`` multiplies ``x**i``, so the
# constant term comes first.  This matches the TOML ``coefficients`` key and
# the way calibration equations are published (``R0*(1 + A*T + B*T**2)`` reads
# off as ``[R0, R0*A, R0*B]``).

_SOLVE_REL_TOL = 1e-14      # relative convergence tolerance for inverse solves
_SOLVE_MAX_ITER = 200
_ROOT_DEDUPE_TOL = 1e-9     # relative spacing below which two roots are one


def _strip_trailing_zeros(coeffs: tuple) -> tuple:
    """Drop leading-order zero coefficients so ``len() - 1`` is the true degree."""
    c = list(coeffs)
    while len(c) > 1 and c[-1] == 0:
        c.pop()
    return tuple(c)


def _poly_eval(coeffs: tuple, x):
    """Horner evaluation. Works with scalars and numpy arrays."""
    acc = coeffs[-1]
    for c in reversed(coeffs[:-1]):
        acc = acc * x + c
    return acc


def _poly_derivative_coeffs(coeffs: tuple) -> tuple:
    """Analytic derivative coefficients: ``d[i-1] = i * coeffs[i]``."""
    if len(coeffs) <= 1:
        return (0.0,)
    return tuple(i * c for i, c in enumerate(coeffs))[1:]


def _poly_compose(outer: tuple, inner: tuple) -> tuple:
    """Exact coefficients of ``outer(inner(x))``, both ascending."""
    result: tuple = (0.0,)
    for c in reversed(outer):
        result = _poly_add(_poly_mul(result, inner), (c,))
    return _strip_trailing_zeros(result)


def _poly_add(p: tuple, q: tuple) -> tuple:
    n = max(len(p), len(q))
    return tuple(
        (p[i] if i < len(p) else 0.0) + (q[i] if i < len(q) else 0.0)
        for i in range(n)
    )


def _poly_mul(p: tuple, q: tuple) -> tuple:
    out = [0.0] * (len(p) + len(q) - 1)
    for i, a in enumerate(p):
        if a == 0:
            continue
        for j, b in enumerate(q):
            out[i + j] += a * b
    return tuple(out)


def _bisect_root(coeffs: tuple, a: float, b: float) -> float:
    """Bisect a sign-changing bracket on which the polynomial is monotone."""
    fa = _poly_eval(coeffs, a)
    for _ in range(_SOLVE_MAX_ITER):
        mid = 0.5 * (a + b)
        if abs(b - a) <= _SOLVE_REL_TOL * max(1.0, abs(mid)):
            return mid
        fm = _poly_eval(coeffs, mid)
        if fm == 0.0:
            return mid
        if (fa < 0) != (fm < 0):
            b = mid
        else:
            a, fa = mid, fm
    return 0.5 * (a + b)


def _poly_roots_in(coeffs: tuple, lo: float, hi: float) -> tuple:
    """Real roots of *coeffs* in the closed interval ``[lo, hi]``, ascending.

    Exact root isolation by recursion on the derivative: the critical points
    of ``p`` partition ``[lo, hi]`` into subintervals on which ``p`` is
    monotone, so each subinterval holds at most one root and a sign change
    locates it.  No numpy, no eigenvalue solve, and correct to any degree.
    """
    c = _strip_trailing_zeros(coeffs)
    if len(c) <= 1:
        return ()  # constant: no isolated roots
    if len(c) == 2:
        r = -c[0] / c[1] + 0.0   # + 0.0 normalizes -0.0
        return (r,) if lo <= r <= hi else ()

    breakpoints = [lo, *_poly_roots_in(_poly_derivative_coeffs(c), lo, hi), hi]
    found: list[float] = []
    for a, b in zip(breakpoints, breakpoints[1:]):
        fa, fb = _poly_eval(c, a), _poly_eval(c, b)
        if fa == 0.0:
            found.append(a)
        if fb == 0.0:
            found.append(b)
        elif (fa < 0) != (fb < 0) and fa != 0.0:
            found.append(_bisect_root(c, a, b))

    unique: list[float] = []
    for r in sorted(found):
        span = max(1.0, abs(r))
        if not unique or abs(r - unique[-1]) > _ROOT_DEDUPE_TOL * span:
            unique.append(r)
    return tuple(unique)


def _solve_monotone(coeffs: tuple, dcoeffs: tuple, y: float,
                    lo: float, hi: float) -> float:
    """Return the unique ``x`` in ``[lo, hi]`` with ``p(x) == y``.

    Safeguarded Newton: a Newton step is taken whenever it lands inside the
    live bracket and the derivative is usable, and a bisection step otherwise.
    The bracket never widens, so this converges for every monotone polynomial
    including those whose derivative vanishes at an endpoint.
    """
    a, b = lo, hi
    fa = _poly_eval(coeffs, a) - y
    fb = _poly_eval(coeffs, b) - y
    if fa == 0.0:
        return a
    if fb == 0.0:
        return b
    if (fa < 0) == (fb < 0):
        raise ValueError(
            f"{y!r} is outside the image of the declared domain "
            f"[{lo!r}, {hi!r}]: the polynomial maps it to "
            f"[{min(fa + y, fb + y)!r}, {max(fa + y, fb + y)!r}]."
        )

    x = 0.5 * (a + b)
    for _ in range(_SOLVE_MAX_ITER):
        fx = _poly_eval(coeffs, x) - y
        if fx == 0.0:
            return x
        if (fa < 0) != (fx < 0):
            b = x
        else:
            a, fa = x, fx
        slope = _poly_eval(dcoeffs, x)
        nxt = x - fx / slope if slope != 0.0 else 0.5 * (a + b)
        if not (a < nxt < b):
            nxt = 0.5 * (a + b)
        if abs(nxt - x) <= _SOLVE_REL_TOL * max(1.0, abs(nxt)):
            return nxt
        x = nxt
    return x


class NonMonotoneOnDomain(ValueError):
    """Raised when a :class:`PolynomialMap` has no single inverse branch.

    A polynomial of degree >= 2 is not injective on all of the reals, so its
    inverse is only a function once the input is restricted to an interval on
    which the polynomial is monotone.  :class:`PolynomialMap` takes that
    interval as its declared ``domain``; when the polynomial turns inside it —
    or is constant, and so has no branch at all — there is no unique branch to
    return and this is raised rather than a root being silently chosen.

    Subclasses :exc:`ValueError`, so callers already handling the
    ``ComposedMap`` non-invertibility path need no change.
    """


class Map(ABC):
    """Abstract base for all conversion morphisms.

    Subclasses must implement ``__call__``, ``inverse``, ``__pow__``, and ``derivative``.
    Composition via ``@`` defaults to :class:`ComposedMap`; subclasses may
    override for closed composition within their own type.

    All concrete maps carry a ``rel_uncertainty`` property (default ``0.0``)
    representing the relative standard uncertainty of the conversion factor.
    This is nonzero for edges derived from measured physical constants (e.g.,
    Hartree energy, Planck mass). Uncertainty composes through ``@`` via
    quadrature and is preserved through ``inverse()``.
    """

    @abstractmethod
    def __call__(self, x: float) -> float:
        """Apply the map to a numeric value."""
        ...

    @abstractmethod
    def inverse(self) -> Map:
        """Return the inverse map."""
        ...

    @abstractmethod
    def __matmul__(self, other: Map) -> Map:
        """Compose: ``(f @ g)(x) == f(g(x))``."""
        ...

    @abstractmethod
    def __pow__(self, exp: float) -> Map:
        """Raise map to a power (for exponent handling in factorwise conversion)."""
        ...

    @abstractmethod
    def derivative(self, x: float) -> float:
        """Return the derivative of the map at point x.

        Used for uncertainty propagation: δy = |f'(x)| * δx
        """
        ...

    @property
    def rel_uncertainty(self) -> float:
        """Relative uncertainty of the conversion factor. Default: 0 (exact)."""
        return 0.0

    def is_identity(self, tol: float = 1e-9) -> bool:
        """Check if this map is approximately the identity."""
        return abs(self(1.0) - 1.0) < tol and abs(self(0.0) - 0.0) < tol

    def to_dict(self) -> dict:
        """Serialize this map to a TOML-friendly dict.

        Map-valued fields are recursively serialized via their own
        ``to_dict()``.  Lists are handled element-wise.
        """
        if not hasattr(self, '_map_type'):
            raise TypeError(
                f"Cannot serialize map type: {type(self).__name__}. "
                f"Define a _map_type class attribute."
            )
        from dataclasses import fields as dc_fields
        d: dict = {"type": self._map_type}
        for f in dc_fields(self):
            if f.name.startswith('_'):
                continue
            val = getattr(self, f.name)
            if f.name == 'rel_uncertainty' and val == 0.0:
                continue  # omit exact (default)
            if isinstance(val, Map):
                val = val.to_dict()
            elif isinstance(val, list):
                val = [v.to_dict() if isinstance(v, Map) else v for v in val]
            d[f.name] = val
        return d


@dataclass(frozen=True)
class LinearMap(Map):
    """A linear conversion: ``y = a * x``.

    Parameters
    ----------
    a : float
        Scale factor.
    rel_uncertainty : float
        Relative standard uncertainty of ``a``. Default ``0.0`` (exact).
        Nonzero for factors derived from measured constants (e.g., CODATA).
    """

    _map_type = "linear"

    a: float
    rel_uncertainty: float = 0.0

    def __call__(self, x: float) -> float:
        return self.a * x

    @property
    def invertible(self) -> bool:
        return self.a != 0

    def inverse(self) -> LinearMap:
        if not self.invertible:
            raise ZeroDivisionError("LinearMap with a=0 is not invertible.")
        return LinearMap(1.0 / self.a, rel_uncertainty=self.rel_uncertainty)

    def __matmul__(self, other: Map) -> Map:
        if isinstance(other, LinearMap):
            combined_ru = math.sqrt(self.rel_uncertainty**2 + other.rel_uncertainty**2)
            return LinearMap(self.a * other.a, rel_uncertainty=combined_ru)
        if isinstance(other, AffineMap):
            # a1 * (a2*x + b2) = (a1*a2)*x + (a1*b2)
            combined_ru = math.sqrt(self.rel_uncertainty**2 + other.rel_uncertainty**2)
            return AffineMap(self.a * other.a, self.a * other.b, rel_uncertainty=combined_ru)
        if not isinstance(other, Map):
            return NotImplemented
        return ComposedMap(self, other)

    def __pow__(self, exp: float) -> LinearMap:
        return LinearMap(self.a ** exp, rel_uncertainty=abs(exp) * self.rel_uncertainty)

    def derivative(self, x: float) -> float:
        """Derivative of y = a*x is a (constant)."""
        return self.a

    _identity_instance: LinearMap | None = None

    @classmethod
    def identity(cls) -> LinearMap:
        if cls._identity_instance is None:
            cls._identity_instance = cls(1.0)
        return cls._identity_instance


@dataclass(frozen=True)
class AffineMap(Map):
    """An affine conversion: ``y = a * x + b``.

    Parameters
    ----------
    a : float
        Slope (scale factor).
    b : float
        Offset.
    rel_uncertainty : float
        Relative standard uncertainty of the slope ``a``. Default ``0.0``
        (exact). The offset ``b`` is always treated as exact.
    """

    _map_type = "affine"

    a: float
    b: float
    rel_uncertainty: float = 0.0

    def __call__(self, x: float) -> float:
        return self.a * x + self.b

    @property
    def invertible(self) -> bool:
        return self.a != 0

    def inverse(self) -> AffineMap:
        if not self.invertible:
            raise ZeroDivisionError("AffineMap with a=0 is not invertible.")
        return AffineMap(1.0 / self.a, -self.b / self.a, rel_uncertainty=self.rel_uncertainty)

    def __matmul__(self, other: Map) -> Map:
        if isinstance(other, LinearMap):
            # a1 * (a2*x) + b1 = (a1*a2)*x + b1
            combined_ru = math.sqrt(self.rel_uncertainty**2 + other.rel_uncertainty**2)
            return AffineMap(self.a * other.a, self.b, rel_uncertainty=combined_ru)
        if isinstance(other, AffineMap):
            # a1 * (a2*x + b2) + b1 = (a1*a2)*x + (a1*b2 + b1)
            combined_ru = math.sqrt(self.rel_uncertainty**2 + other.rel_uncertainty**2)
            return AffineMap(self.a * other.a, self.a * other.b + self.b, rel_uncertainty=combined_ru)
        if not isinstance(other, Map):
            return NotImplemented
        return ComposedMap(self, other)

    def __pow__(self, exp: float) -> Map:
        if exp == 1:
            return self
        if exp == -1:
            return self.inverse()
        raise ValueError("AffineMap only supports exp=1 or exp=-1")

    def derivative(self, x: float) -> float:
        """Derivative of y = a*x + b is a (constant)."""
        return self.a


@dataclass(frozen=True)
class LogMap(Map):
    """
    Logarithmic map: ``y = scale * log_base(x / reference) + offset``

    Parameters
    ----------
    scale : float
        Multiplier for logarithm (10 for dB power, 20 for dB amplitude)
    base : float
        Logarithm base (10 for dB, e for neper)
    reference : float
        Reference value; x/reference is the argument to log.
        Default 1.0 means pure ratio (no reference level).
    offset : float
        Added after logarithm (rarely used)

    Examples::

        LogMap()                           # log₁₀(x) — pure ratio
        LogMap(scale=10)                   # 10·log₁₀(x) — bel×10 (dB power)
        LogMap(scale=10, reference=0.001)  # 10·log₁₀(x/1mW) — dBm
        LogMap(scale=-1)                   # -log₁₀(x) — pH-style
        LogMap(base=math.e)                # ln(x) — neper

    For transforms like nines ``(-log₁₀(1-x))``, compose with AffineMap::

        LogMap(scale=-1) @ AffineMap(a=-1, b=1)
    """

    _map_type = "log"

    scale: float = 1.0
    base: float = 10.0
    reference: float = 1.0
    offset: float = 0.0

    def __call__(self, x):
        """Apply the logarithmic map. Works with scalars and numpy arrays."""
        _validate_positive(x)
        return self.scale * _log(x / self.reference, self.base) + self.offset

    @property
    def invertible(self) -> bool:
        return self.scale != 0

    def inverse(self) -> 'ExpMap':
        """Return the inverse exponential map."""
        if not self.invertible:
            raise ZeroDivisionError("LogMap with scale=0 is not invertible.")
        return ExpMap(
            scale=1.0 / self.scale,
            base=self.base,
            reference=self.reference,
            offset=-self.offset / self.scale,
        )

    def __matmul__(self, other: Map) -> Map:
        if not isinstance(other, Map):
            return NotImplemented
        return ComposedMap(self, other)

    def __pow__(self, exp: float) -> Map:
        if exp == 1:
            return self
        if exp == -1:
            return self.inverse()
        raise ValueError("LogMap only supports exp=1 or exp=-1")

    def derivative(self, x):
        """Derivative: d/dx[scale * log_base(x/ref)] = scale / (x * ln(base))

        Works with both scalars and numpy arrays.
        """
        _validate_positive(x)
        return self.scale / (x * math.log(self.base))

    def to_dict(self) -> dict:
        d: dict = {"type": self._map_type, "scale": self.scale, "base": self.base}
        if self.reference != 1.0:
            d["reference"] = self.reference
        if self.offset != 0.0:
            d["offset"] = self.offset
        return d

    def is_identity(self, tol: float = 1e-9) -> bool:
        return False  # Logarithm is never identity


@dataclass(frozen=True)
class ExpMap(Map):
    """
    Exponential map: ``y = reference * base^(scale * x + offset)``

    This is the inverse of :class:`LogMap`. Typically obtained via
    ``LogMap.inverse()`` rather than constructed directly.

    Parameters
    ----------
    scale : float
        Multiplier for the exponent.
    base : float
        Base of the exponential (10 for dB, e for neper).
    reference : float
        Multiplier for the result. Default 1.0 for pure ratio.
    offset : float
        Added to exponent before evaluation.
    """

    _map_type = "exp"

    scale: float = 1.0
    base: float = 10.0
    reference: float = 1.0
    offset: float = 0.0

    def __call__(self, x):
        """Apply the exponential map. Works with scalars and numpy arrays."""
        return self.reference * _exp(self.base, self.scale * x + self.offset)

    @property
    def invertible(self) -> bool:
        return self.scale != 0

    def inverse(self) -> LogMap:
        """Return the inverse logarithmic map."""
        if not self.invertible:
            raise ZeroDivisionError("ExpMap with scale=0 is not invertible.")
        return LogMap(
            scale=1.0 / self.scale,
            base=self.base,
            reference=self.reference,
            offset=-self.offset / self.scale,
        )

    def __matmul__(self, other: Map) -> Map:
        if not isinstance(other, Map):
            return NotImplemented
        return ComposedMap(self, other)

    def __pow__(self, exp: float) -> Map:
        if exp == 1:
            return self
        if exp == -1:
            return self.inverse()
        raise ValueError("ExpMap only supports exp=1 or exp=-1")

    def derivative(self, x):
        """Derivative: d/dx[ref * base^(scale*x + offset)] = ln(base) * scale * ref * base^(scale*x + offset)

        Works with both scalars and numpy arrays.
        """
        return math.log(self.base) * self.scale * self(x)

    def to_dict(self) -> dict:
        d: dict = {"type": self._map_type, "scale": self.scale, "base": self.base}
        if self.reference != 1.0:
            d["reference"] = self.reference
        if self.offset != 0.0:
            d["offset"] = self.offset
        return d

    def is_identity(self, tol: float = 1e-9) -> bool:
        return False  # Exponential is never identity


@dataclass(frozen=True)
class ReciprocalMap(Map):
    """Inversely proportional map: ``y = a / x``.

    Used for cross-dimensional conversions where quantities are inversely
    related through a physical constant (e.g., wavelength and frequency
    via ``c = λν``).

    Parameters
    ----------
    a : float
        The constant of proportionality.
    rel_uncertainty : float
        Relative uncertainty of the constant ``a``. Default: 0.0 (exact).
    """

    _map_type = "reciprocal"

    a: float
    rel_uncertainty: float = 0.0

    def __call__(self, x):
        """Apply the inverse map. Works with scalars and numpy arrays."""
        if _is_array(x):
            return self.a / x
        return self.a / x

    @property
    def invertible(self) -> bool:
        return self.a != 0

    def inverse(self) -> 'ReciprocalMap':
        """ReciprocalMap is self-inverse: if y = a/x, then x = a/y."""
        return ReciprocalMap(self.a, rel_uncertainty=self.rel_uncertainty)

    def __matmul__(self, other: Map) -> Map:
        if not isinstance(other, Map):
            return NotImplemented
        return ComposedMap(self, other)

    def __pow__(self, exp: float) -> Map:
        if exp == 1:
            return self
        if exp == -1:
            return self.inverse()
        raise ValueError("ReciprocalMap only supports exp=1 or exp=-1")

    def derivative(self, x):
        """Derivative: d/dx[a/x] = -a/x². Works with scalars and numpy arrays."""
        if _is_array(x):
            return -self.a / (x * x)
        return -self.a / (x * x)

    def is_identity(self, tol: float = 1e-9) -> bool:
        return False  # Inverse proportionality is never identity


@dataclass(frozen=True)
class PolynomialMap(Map):
    """A polynomial conversion over a declared domain:
    ``y = a0 + a1*x + a2*x**2 + ... + an*x**n``.

    This is the calibration-curve map.  Instrument manufacturers and standards
    bodies publish nonlinear sensor responses as polynomials, not as
    compositions of simpler charts: the Callendar-Van Dusen equation for a
    platinum RTD, the NIST ITS-90 thermocouple reference functions, a fitted
    load-cell or spectrophotometer curve.  None of them is expressible as a
    :class:`LinearMap` / :class:`AffineMap` / :class:`LogMap` chain.

    The domain
    ----------
    ``domain`` is **not** an implementation convenience; it is half the datum.
    A calibration polynomial is always published with a validity range (IEC
    60751 gives Callendar-Van Dusen over 0..850 degC; NIST gives each
    thermocouple polynomial a sub-range), and that range is what makes the
    inverse a function: a polynomial of degree >= 2 is not injective, but on
    an interval where it is monotone exactly one inverse branch exists.
    :meth:`inverse` returns that branch; when the polynomial turns inside the
    declared domain it raises :exc:`NonMonotoneOnDomain` rather than picking a
    root.

    ``__call__`` does **not** refuse arguments outside ``domain``.  Every other
    :class:`Map` extrapolates freely, and refusing here would be a conversion
    policy rather than a property of the morphism.  The domain's job in this
    class is branch selection.

    Parameters
    ----------
    coefficients : tuple[float, ...]
        **Ascending** order — ``coefficients[i]`` multiplies ``x**i``, so the
        constant term ``a0`` comes first.  Leading-order zeros are stripped at
        construction so that :attr:`degree` is the true degree.  Lists are
        accepted and normalized to a tuple (TOML yields lists).
    domain : tuple[float, float]
        The closed interval ``(lo, hi)`` over which the polynomial is declared
        valid, and over which its inverse branch is taken.  Required: a
        calibration polynomial without a stated span is not a calibration.
    rel_uncertainty : float
        Relative standard uncertainty of the computed value — the fit residual
        or the sensor's tolerance class (a Class A PT100 is +/-0.15 degC at
        0 degC).  Default ``0.0`` (exact), matching the other maps.

    Examples
    --------
    A PT100 platinum RTD, ``R(T) = R0*(1 + A*T + B*T**2)`` for ``T >= 0``::

        >>> pt100 = PolynomialMap((100.0, 0.39083, -5.775e-5), domain=(0.0, 850.0))
        >>> round(pt100(100.0), 4)       # ohms at 100 degC
        138.5055
        >>> round(pt100.inverse()(138.5055), 9)
        100.0
    """

    _map_type = "polynomial"

    coefficients: tuple
    domain: tuple
    rel_uncertainty: float = 0.0

    def __post_init__(self) -> None:
        coeffs = _strip_trailing_zeros(tuple(float(c) for c in self.coefficients))
        if not coeffs:
            raise ValueError("PolynomialMap requires at least one coefficient.")
        object.__setattr__(self, 'coefficients', coeffs)

        dom = tuple(float(v) for v in self.domain)
        if len(dom) != 2:
            raise ValueError(
                f"PolynomialMap domain must be a (lo, hi) pair, got {self.domain!r}."
            )
        if not dom[0] < dom[1]:
            raise ValueError(
                f"PolynomialMap domain must satisfy lo < hi, got {dom!r}."
            )
        object.__setattr__(self, 'domain', dom)

    @property
    def degree(self) -> int:
        """Degree of the polynomial (0 for a constant)."""
        return len(self.coefficients) - 1

    @property
    def derivative_coefficients(self) -> tuple:
        """Ascending coefficients of the analytic derivative."""
        return _poly_derivative_coeffs(self.coefficients)

    def __call__(self, x):
        """Horner evaluation. Works with scalars and numpy arrays."""
        return _poly_eval(self.coefficients, x)

    def derivative(self, x):
        """Analytic derivative, Horner-evaluated on the derivative coefficients.

        Exact, not a finite difference: the uncertainty machinery multiplies
        this by the measurement uncertainty, so a numerical estimate here
        would put differencing noise into every propagated delta.
        """
        return _poly_eval(self.derivative_coefficients, x)

    @property
    def turning_points(self) -> tuple:
        """Critical points strictly inside the declared domain, ascending.

        Empty exactly when the polynomial is monotone on the domain.  A
        critical point *on* a boundary does not break monotonicity (``x**2``
        is monotone on ``[0, 1]``) and is not reported.
        """
        lo, hi = self.domain
        return tuple(
            r for r in _poly_roots_in(self.derivative_coefficients, lo, hi)
            if lo < r < hi
        )

    @property
    def invertible(self) -> bool:
        """True when a single inverse branch covers the declared domain."""
        if self.degree < 1:
            return False
        return not self.turning_points

    def inverse(self) -> Map:
        """Return the single inverse branch over the declared domain.

        Degenerate degrees delegate rather than carry machinery they do not
        need: degree 1 is an :class:`AffineMap` and inverts in closed form;
        degree 0 is constant and has no branch.

        Raises
        ------
        NonMonotoneOnDomain
            If the polynomial is constant, or turns inside the domain, so that
            no single branch covers it.
        """
        if self.degree < 1:
            raise NonMonotoneOnDomain(
                f"PolynomialMap with coefficients {self.coefficients} is constant "
                f"and has no inverse branch."
            )
        if self.degree == 1:
            a0, a1 = self.coefficients
            return AffineMap(1.0 / a1, -a0 / a1, rel_uncertainty=self.rel_uncertainty)
        turning = self.turning_points
        if turning:
            raise NonMonotoneOnDomain(
                f"PolynomialMap of degree {self.degree} is not monotone on its "
                f"declared domain {self.domain}: it turns at "
                f"{', '.join(repr(t) for t in turning)}. No single inverse "
                f"branch covers the domain — narrow the domain to one side of "
                f"the turning point(s)."
            )
        return PolynomialInverseMap(self)

    def __matmul__(self, other: Map) -> Map:
        """Compose. Polynomial-of-polynomial stays a polynomial, exactly.

        :class:`LinearMap` and :class:`AffineMap` are degree-1 polynomials, so
        they fold in too — the common authoring shape where a raw signal is
        rescaled before the calibration curve is applied.  The composite's
        domain is the inner map's input domain (for an affine inner map, the
        preimage of this map's domain).  Everything else falls back to
        :class:`ComposedMap` like the other subclasses.
        """
        if isinstance(other, PolynomialMap):
            return PolynomialMap(
                _poly_compose(self.coefficients, other.coefficients),
                domain=other.domain,
                rel_uncertainty=math.sqrt(
                    self.rel_uncertainty**2 + other.rel_uncertainty**2
                ),
            )
        if isinstance(other, (LinearMap, AffineMap)):
            a = other.a
            b = other.b if isinstance(other, AffineMap) else 0.0
            if a != 0.0:
                lo, hi = self.domain
                edges = sorted(((lo - b) / a, (hi - b) / a))
                return PolynomialMap(
                    _poly_compose(self.coefficients, (b, a)),
                    domain=(edges[0], edges[1]),
                    rel_uncertainty=math.sqrt(
                        self.rel_uncertainty**2 + other.rel_uncertainty**2
                    ),
                )
        if not isinstance(other, Map):
            return NotImplemented
        return ComposedMap(self, other)

    def __pow__(self, exp: float) -> Map:
        if exp == 1:
            return self
        if exp == -1:
            return self.inverse()
        raise ValueError("PolynomialMap only supports exp=1 or exp=-1")

    def to_dict(self) -> dict:
        d: dict = {
            "type": self._map_type,
            "coefficients": list(self.coefficients),
            "domain": list(self.domain),
        }
        if self.rel_uncertainty != 0.0:
            d["rel_uncertainty"] = self.rel_uncertainty
        return d

    def is_identity(self, tol: float = 1e-9) -> bool:
        """Only the degree-1 polynomial ``0 + 1*x`` is the identity."""
        if self.degree != 1:
            return False
        a0, a1 = self.coefficients
        return abs(a1 - 1.0) < tol and abs(a0) < tol


@dataclass(frozen=True)
class PolynomialInverseMap(Map):
    """The single inverse branch of a :class:`PolynomialMap` on its domain.

    The inverse of a polynomial of degree >= 2 is not itself a polynomial, so
    it gets its own type rather than being forced into one.  Obtained via
    ``PolynomialMap.inverse()`` rather than constructed directly.

    Evaluation is a safeguarded Newton solve (Newton step when it lands inside
    the live bracket, bisection otherwise) over the forward map's declared
    domain, which brackets the root by monotonicity.  The derivative comes
    from the implicit function theorem — ``1 / p'(p_inv(y))`` — so it is
    analytic in the forward map's exact derivative and the uncertainty
    machinery transports through this edge like any other.

    Parameters
    ----------
    polynomial : PolynomialMap
        The forward map.  Must be monotone on its declared domain; this is
        re-checked at construction so a deserialized instance cannot be
        invalid.
    """

    _map_type = "polynomial_inverse"

    polynomial: PolynomialMap

    def __post_init__(self) -> None:
        if not isinstance(self.polynomial, PolynomialMap):
            raise TypeError(
                f"PolynomialInverseMap wraps a PolynomialMap, got "
                f"{type(self.polynomial).__name__}."
            )
        if not self.polynomial.invertible:
            raise NonMonotoneOnDomain(
                f"PolynomialMap {self.polynomial.coefficients} is not invertible "
                f"on {self.polynomial.domain}; there is no single branch to wrap."
            )

    @property
    def domain(self) -> tuple:
        """The image of the forward map's domain — this map's valid inputs."""
        lo, hi = self.polynomial.domain
        a, b = self.polynomial(lo), self.polynomial(hi)
        return (a, b) if a <= b else (b, a)

    @property
    def rel_uncertainty(self) -> float:
        return self.polynomial.rel_uncertainty

    def __call__(self, y):
        """Solve ``p(x) == y`` for the unique ``x`` in the forward domain.

        Works with scalars and numpy arrays; array inputs are solved
        elementwise, since each solve carries its own bracket.
        """
        if _is_array(y):
            np = _get_numpy()
            flat = [self._solve(float(v)) for v in y.ravel()]
            return np.array(flat, dtype=float).reshape(y.shape)
        return self._solve(y)

    def _solve(self, y: float) -> float:
        lo, hi = self.polynomial.domain
        return _solve_monotone(
            self.polynomial.coefficients,
            self.polynomial.derivative_coefficients,
            y,
            lo,
            hi,
        )

    def derivative(self, y):
        """Implicit function theorem: ``d/dy p_inv(y) = 1 / p'(p_inv(y))``."""
        x = self(y)
        slope = self.polynomial.derivative(x)
        if _is_array(slope):
            return 1.0 / slope
        if slope == 0.0:
            raise ZeroDivisionError(
                f"PolynomialMap derivative vanishes at x={x!r}; the inverse "
                f"branch has infinite slope there."
            )
        return 1.0 / slope

    @property
    def invertible(self) -> bool:
        return True

    def inverse(self) -> PolynomialMap:
        """Self-inverse pairing: the forward polynomial comes back."""
        return self.polynomial

    def __matmul__(self, other: Map) -> Map:
        if not isinstance(other, Map):
            return NotImplemented
        return ComposedMap(self, other)

    def __pow__(self, exp: float) -> Map:
        if exp == 1:
            return self
        if exp == -1:
            return self.inverse()
        raise ValueError("PolynomialInverseMap only supports exp=1 or exp=-1")

    def is_identity(self, tol: float = 1e-9) -> bool:
        return self.polynomial.is_identity(tol)


@dataclass(frozen=True)
class ComposedMap(Map):
    """Generic composition fallback: ``(outer ∘ inner)(x) = outer(inner(x))``.

    ``rel_uncertainty`` is computed as a property:
    ``sqrt(outer.rel_uncertainty**2 + inner.rel_uncertainty**2)``.
    """

    _map_type = "composed"

    outer: Map
    inner: Map

    def __call__(self, x: float) -> float:
        return self.outer(self.inner(x))

    @property
    def rel_uncertainty(self) -> float:
        outer_ru = self.outer.rel_uncertainty
        inner_ru = self.inner.rel_uncertainty
        return math.sqrt(outer_ru**2 + inner_ru**2)

    @property
    def invertible(self) -> bool:
        return self.outer.invertible and self.inner.invertible

    def inverse(self) -> ComposedMap:
        if not self.invertible:
            raise ValueError("ComposedMap is not invertible: one or both components are not invertible.")
        return ComposedMap(self.inner.inverse(), self.outer.inverse())

    def __matmul__(self, other: Map) -> ComposedMap:
        if not isinstance(other, Map):
            return NotImplemented
        return ComposedMap(self, other)

    def __pow__(self, exp: float) -> Map:
        if exp == 1:
            return self
        if exp == -1:
            return self.inverse()
        raise ValueError("ComposedMap only supports exp=1 or exp=-1")

    def derivative(self, x: float) -> float:
        """Chain rule: d/dx [outer(inner(x))] = outer'(inner(x)) * inner'(x)."""
        inner_val = self.inner(x)
        return self.outer.derivative(inner_val) * self.inner.derivative(x)
