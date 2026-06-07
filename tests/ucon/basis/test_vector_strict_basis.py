# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Pin strict same-basis semantics directly at the ``Vector`` boundary.

``Vector`` arithmetic is strict same-basis: cross-basis ``*`` / ``/`` raise
:class:`ucon.basis.types.BasisMismatch`. Cross-basis arithmetic lives in
:mod:`ucon.basis.ops` (covered by ``tests/ucon/test_basis_ops.py``). This
file exists so the strict-basis invariant is independently observable at
the algebra layer and so an import-level audit confirms that
``ucon.basis.vector`` never reaches for ``BasisGraph`` or
``BasisTransform``.
"""

from __future__ import annotations

from fractions import Fraction

import pytest

from ucon.basis import Basis, BasisComponent, BasisMismatch, Vector
from ucon.basis.builtin import SI


def _vec(basis: Basis, **named: int) -> Vector:
    components = tuple(Fraction(named.get(c.name, 0)) for c in basis)
    return Vector(basis, components)


def _flux_basis() -> Basis:
    return Basis("flux_basis", [BasisComponent("flux", "Φ")])


class TestSameBasisBaseline:
    """Same-basis ``*`` / ``/`` continue to compose component-wise."""

    def test_mul_same_basis_returns_sum_vector(self) -> None:
        length = _vec(SI, length=1)
        inv_time = _vec(SI, time=-1)
        velocity = length * inv_time
        assert velocity.basis is SI
        assert velocity["length"] == 1
        assert velocity["time"] == -1

    def test_truediv_same_basis_returns_difference_vector(self) -> None:
        length = _vec(SI, length=1)
        time = _vec(SI, time=1)
        velocity = length / time
        assert velocity.basis is SI
        assert velocity["length"] == 1
        assert velocity["time"] == -1


class TestCrossBasisRaises:
    """Cross-basis ``*`` / ``/`` raise :class:`BasisMismatch` immediately."""

    def test_mul_cross_basis_raises_basis_mismatch(self) -> None:
        flux_basis = _flux_basis()
        kg = _vec(SI, mass=1)
        flux = _vec(flux_basis, flux=1)
        with pytest.raises(BasisMismatch) as exc_info:
            kg * flux
        exc = exc_info.value
        assert exc.left is SI
        assert exc.right is flux_basis
        assert exc.op == "multiply"

    def test_truediv_cross_basis_raises_basis_mismatch(self) -> None:
        flux_basis = _flux_basis()
        kg = _vec(SI, mass=1)
        flux = _vec(flux_basis, flux=1)
        with pytest.raises(BasisMismatch) as exc_info:
            kg / flux
        exc = exc_info.value
        assert exc.left is SI
        assert exc.right is flux_basis
        assert exc.op == "divide"

    def test_basis_mismatch_is_value_error_subclass(self) -> None:
        """Legacy ``except ValueError`` callsites continue to catch."""
        assert issubclass(BasisMismatch, ValueError)


class TestVectorImportSurface:
    """``vector.py`` must not reach the graph layer."""

    def test_vector_module_does_not_expose_basis_graph(self) -> None:
        import ucon.basis.vector as vector_module

        attrs = dir(vector_module)
        assert "BasisGraph" not in attrs
        assert "BasisTransform" not in attrs
