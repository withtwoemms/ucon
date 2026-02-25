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
- :class:`ComposedMap` — Generic composition fallback: g(f(x))
"""
from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass


class Map(ABC):
    """Abstract base for all conversion morphisms.

    Subclasses must implement ``__call__``, ``inverse``, ``__pow__``, and ``derivative``.
    Composition via ``@`` defaults to :class:`ComposedMap`; subclasses may
    override for closed composition within their own type.
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

    def is_identity(self, tol: float = 1e-9) -> bool:
        """Check if this map is approximately the identity."""
        return abs(self(1.0) - 1.0) < tol and abs(self(0.0) - 0.0) < tol


@dataclass(frozen=True)
class LinearMap(Map):
    """A linear conversion: ``y = a * x``."""

    a: float

    def __call__(self, x: float) -> float:
        return self.a * x

    @property
    def invertible(self) -> bool:
        return self.a != 0

    def inverse(self) -> LinearMap:
        if not self.invertible:
            raise ZeroDivisionError("LinearMap with a=0 is not invertible.")
        return LinearMap(1.0 / self.a)

    def __matmul__(self, other: Map) -> Map:
        if isinstance(other, LinearMap):
            return LinearMap(self.a * other.a)
        if isinstance(other, AffineMap):
            # a1 * (a2*x + b2) = (a1*a2)*x + (a1*b2)
            return AffineMap(self.a * other.a, self.a * other.b)
        if not isinstance(other, Map):
            return NotImplemented
        return ComposedMap(self, other)

    def __pow__(self, exp: float) -> LinearMap:
        return LinearMap(self.a ** exp)

    def derivative(self, x: float) -> float:
        """Derivative of y = a*x is a (constant)."""
        return self.a

    @classmethod
    def identity(cls) -> LinearMap:
        return cls(1.0)


@dataclass(frozen=True)
class AffineMap(Map):
    """An affine conversion: ``y = a * x + b``."""

    a: float
    b: float

    def __call__(self, x: float) -> float:
        return self.a * x + self.b

    @property
    def invertible(self) -> bool:
        return self.a != 0

    def inverse(self) -> AffineMap:
        if not self.invertible:
            raise ZeroDivisionError("AffineMap with a=0 is not invertible.")
        return AffineMap(1.0 / self.a, -self.b / self.a)

    def __matmul__(self, other: Map) -> Map:
        if isinstance(other, LinearMap):
            # a1 * (a2*x) + b1 = (a1*a2)*x + b1
            return AffineMap(self.a * other.a, self.b)
        if isinstance(other, AffineMap):
            # a1 * (a2*x + b2) + b1 = (a1*a2)*x + (a1*b2 + b1)
            return AffineMap(self.a * other.a, self.a * other.b + self.b)
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

    scale: float = 1.0
    base: float = 10.0
    reference: float = 1.0
    offset: float = 0.0

    def __call__(self, x: float) -> float:
        if x <= 0:
            raise ValueError(f"Logarithm argument must be positive, got {x}")
        return self.scale * math.log(x / self.reference, self.base) + self.offset

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

    def derivative(self, x: float) -> float:
        """Derivative: d/dx[scale * log_base(x/ref)] = scale / (x * ln(base))"""
        if x <= 0:
            raise ValueError(f"Derivative undefined for x={x}")
        return self.scale / (x * math.log(self.base))

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

    scale: float = 1.0
    base: float = 10.0
    reference: float = 1.0
    offset: float = 0.0

    def __call__(self, x: float) -> float:
        return self.reference * self.base ** (self.scale * x + self.offset)

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

    def derivative(self, x: float) -> float:
        """Derivative: d/dx[ref * base^(scale*x + offset)] = ln(base) * scale * ref * base^(scale*x + offset)"""
        return math.log(self.base) * self.scale * self(x)

    def is_identity(self, tol: float = 1e-9) -> bool:
        return False  # Exponential is never identity


@dataclass(frozen=True)
class ComposedMap(Map):
    """Generic composition fallback: ``(outer ∘ inner)(x) = outer(inner(x))``."""

    outer: Map
    inner: Map

    def __call__(self, x: float) -> float:
        return self.outer(self.inner(x))

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
