# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
ucon.conversion.map
====================

Implements the **Map** class hierarchy — the composable substrate for
all unit conversion morphisms in *ucon*.

Classes
-------
- :class:`Map` — Abstract base for conversion morphisms.
- :class:`LinearMap` — y = factor * x
- :class:`AffineMap` — y = scale * x + offset
- :class:`ComposedMap` — Generic composition fallback: g(f(x))
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class Map(ABC):
    """Abstract base for all conversion morphisms.

    Subclasses must implement ``__call__``, ``inverse``, and ``invertible``.
    Composition via ``@`` defaults to :class:`ComposedMap`; subclasses may
    override for closed composition within their own type.
    """

    @abstractmethod
    def __call__(self, x: float) -> float:
        """Apply the map to a numeric value."""
        ...

    @abstractmethod
    def inverse(self) -> Map:
        """Return the inverse map, if invertible."""
        ...

    def __matmul__(self, other: Map) -> Map:
        """Compose: ``(f @ g)(x) == f(g(x))``.

        Subclasses should override to return a closed type when possible
        (e.g. LinearMap @ LinearMap -> LinearMap).
        """
        if not isinstance(other, Map):
            return NotImplemented
        return ComposedMap(self, other)

    @property
    @abstractmethod
    def invertible(self) -> bool:
        ...


class LinearMap(Map):
    """A linear conversion: ``y = factor * x``."""

    def __init__(self, factor: float):
        self.factor = factor

    def __call__(self, x: float) -> float:
        return self.factor * x

    def inverse(self) -> LinearMap:
        if self.factor == 0:
            raise ZeroDivisionError("LinearMap with factor=0 is not invertible.")
        return LinearMap(1.0 / self.factor)

    def __matmul__(self, other: Map) -> Map:
        if isinstance(other, LinearMap):
            return LinearMap(self.factor * other.factor)
        if not isinstance(other, Map):
            return NotImplemented
        return ComposedMap(self, other)

    @classmethod
    def identity(cls) -> LinearMap:
        return cls(1.0)

    @property
    def invertible(self) -> bool:
        return self.factor != 0

    def __eq__(self, other) -> bool:
        if not isinstance(other, LinearMap):
            return NotImplemented
        return abs(self.factor - other.factor) < 1e-12

    def __hash__(self) -> int:
        return hash(round(self.factor, 12))

    def __repr__(self) -> str:
        return f"LinearMap({self.factor})"


class AffineMap(Map):
    """An affine conversion: ``y = scale * x + offset``."""

    def __init__(self, scale: float, offset: float):
        self.scale = scale
        self.offset = offset

    def __call__(self, x: float) -> float:
        return self.scale * x + self.offset

    def inverse(self) -> AffineMap:
        if self.scale == 0:
            raise ZeroDivisionError("AffineMap with scale=0 is not invertible.")
        return AffineMap(1.0 / self.scale, -self.offset / self.scale)

    def __matmul__(self, other: Map) -> Map:
        if isinstance(other, AffineMap):
            # (s1 * (s2 * x + o2) + o1) = (s1*s2)*x + (s1*o2 + o1)
            return AffineMap(
                self.scale * other.scale,
                self.scale * other.offset + self.offset,
            )
        if not isinstance(other, Map):
            return NotImplemented
        return ComposedMap(self, other)

    @property
    def invertible(self) -> bool:
        return self.scale != 0

    def __eq__(self, other) -> bool:
        if not isinstance(other, AffineMap):
            return NotImplemented
        return (
            abs(self.scale - other.scale) < 1e-12
            and abs(self.offset - other.offset) < 1e-12
        )

    def __hash__(self) -> int:
        return hash((round(self.scale, 12), round(self.offset, 12)))

    def __repr__(self) -> str:
        return f"AffineMap(scale={self.scale}, offset={self.offset})"


class ComposedMap(Map):
    """Generic composition fallback: ``(outer ∘ inner)(x) = outer(inner(x))``."""

    def __init__(self, outer: Map, inner: Map):
        self.outer = outer
        self.inner = inner

    def __call__(self, x: float) -> float:
        return self.outer(self.inner(x))

    def inverse(self) -> ComposedMap:
        if not self.invertible:
            raise ValueError("ComposedMap is not invertible: one or both components are not invertible.")
        return ComposedMap(self.inner.inverse(), self.outer.inverse())

    @property
    def invertible(self) -> bool:
        return self.outer.invertible and self.inner.invertible

    def __repr__(self) -> str:
        return f"ComposedMap({self.outer!r} ∘ {self.inner!r})"
