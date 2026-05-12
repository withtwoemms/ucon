# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Direct coverage for :mod:`ucon.basis.ops`.

:class:`ucon.basis.vector.Vector` arithmetic is strict same-basis; cross-basis
multiplication / division lives in :mod:`ucon.basis.ops`. These tests exercise
the ops module directly, including the three graph-resolution branches:

- explicit ``graph=`` kwarg (highest priority)
- ``system=`` kwarg (mid priority)
- ContextVar-scoped active graph (fallback)

and the same-basis fast paths.
"""

from __future__ import annotations

import dataclasses
from fractions import Fraction

import pytest

from ucon.basis import (
    Basis,
    BasisComponent,
    BasisGraph,
    BasisMismatch,
    BasisTransform,
    Vector,
    ops,
    using_basis_graph,
)
from ucon.basis.builtin import SI
from ucon.basis.graph import get_basis_graph
from ucon.system import UnitSystem


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _economic_basis() -> Basis:
    """SI plus a 'currency' slot."""
    return Basis("economic", list(SI) + [BasisComponent("currency", "$")])


def _si_to_economic(economic: Basis) -> BasisTransform:
    n_src = len(SI)
    n_tgt = len(economic)
    matrix = tuple(
        tuple(Fraction(1) if j == i else Fraction(0) for j in range(n_tgt))
        for i in range(n_src)
    )
    return BasisTransform(SI, economic, matrix)


def _vec(basis: Basis, **named: int) -> Vector:
    components = tuple(Fraction(named.get(c.name, 0)) for c in basis)
    return Vector(basis, components)


# ---------------------------------------------------------------------------
# unify — same-basis fast path and forward / reverse projection
# ---------------------------------------------------------------------------


class TestUnifySameBasis:
    """``unify`` short-circuits when both vectors share a basis."""

    def test_same_basis_returns_inputs_unchanged(self) -> None:
        a = _vec(SI, length=1)
        b = _vec(SI, time=-1)
        a_, b_ = ops.unify(a, b)
        assert a_ is a
        assert b_ is b

    def test_same_basis_skips_graph_lookup(self) -> None:
        """No graph consultation occurs on the fast path; an empty graph
        suffices."""
        empty = BasisGraph()
        a = _vec(SI, mass=1)
        b = _vec(SI, mass=-1)
        a_, b_ = ops.unify(a, b, graph=empty)
        assert a_.basis == SI and b_.basis == SI


class TestUnifyCrossBasis:
    """Cross-basis ``unify`` consults the graph."""

    def setup_method(self) -> None:
        self.economic = _economic_basis()
        self.embedding = _si_to_economic(self.economic)
        self.graph = get_basis_graph().with_transform(self.embedding)

    def test_forward_projection_si_to_economic(self) -> None:
        si_time = _vec(SI, time=1)
        usd = _vec(self.economic, currency=1)
        a_, b_ = ops.unify(si_time, usd, graph=self.graph)
        assert a_.basis == self.economic
        assert b_.basis == self.economic
        # SI time should have been embedded into the economic basis.
        assert a_["time"] == 1
        assert a_["currency"] == 0

    def test_reverse_projection_when_only_inverse_path_clean(self) -> None:
        """If ``a -> b`` is unavailable but ``b -> a`` is clean, the second
        branch is taken."""
        # economic -> SI is lossy (currency would be discarded); but
        # SI -> economic is clean. Calling unify with (economic, SI) means
        # the first attempt (a.basis -> b.basis) is economic -> SI which
        # is lossy on a non-zero currency component. The function then
        # tries the reverse SI -> economic, which succeeds.
        usd = _vec(self.economic, currency=1)
        si_mass = _vec(SI, mass=1)
        a_, b_ = ops.unify(usd, si_mass, graph=self.graph)
        assert a_.basis == self.economic
        assert b_.basis == self.economic
        assert a_["currency"] == 1
        assert b_["mass"] == 1


class TestUnifyFailures:
    """``unify`` raises :class:`BasisMismatch` when no clean path exists."""

    def test_no_transform_path(self) -> None:
        unrelated = Basis("unrelated", [BasisComponent("flux", "Φ")])
        flux = _vec(unrelated, flux=1)
        kg = _vec(SI, mass=1)
        with pytest.raises(BasisMismatch, match="different bases"):
            ops.unify(flux, kg, graph=BasisGraph())

    def test_basis_mismatch_is_value_error(self) -> None:
        """Legacy ``except ValueError`` callsites continue to catch."""
        unrelated = Basis("unrelated", [BasisComponent("flux", "Φ")])
        flux = _vec(unrelated, flux=1)
        kg = _vec(SI, mass=1)
        with pytest.raises(ValueError, match="different bases"):
            ops.unify(flux, kg, graph=BasisGraph())

    def test_basis_mismatch_carries_left_right_op(self) -> None:
        unrelated = Basis("unrelated", [BasisComponent("flux", "Φ")])
        flux = _vec(unrelated, flux=1)
        kg = _vec(SI, mass=1)
        try:
            ops.unify(flux, kg, graph=BasisGraph())
        except BasisMismatch as exc:
            assert exc.left == unrelated
            assert exc.right == SI
            assert exc.op == "unify"
        else:  # pragma: no cover
            pytest.fail("BasisMismatch was not raised")


# ---------------------------------------------------------------------------
# multiply_via / divide_via
# ---------------------------------------------------------------------------


class TestMultiplyVia:
    def setup_method(self) -> None:
        self.economic = _economic_basis()
        self.graph = get_basis_graph().with_transform(_si_to_economic(self.economic))

    def test_same_basis_delegates_to_operator(self) -> None:
        kg = _vec(SI, mass=1)
        m_per_s = _vec(SI, length=1, time=-1)
        result = ops.multiply_via(kg, m_per_s)
        assert result.basis == SI
        assert result["mass"] == 1
        assert result["length"] == 1
        assert result["time"] == -1

    def test_cross_basis_promotes_to_extended(self) -> None:
        usd = _vec(self.economic, currency=1)
        second = _vec(SI, time=1)
        result = ops.multiply_via(usd, second, graph=self.graph)
        assert result.basis == self.economic
        assert result["currency"] == 1
        assert result["time"] == 1

    def test_cross_basis_no_path_raises(self) -> None:
        unrelated = Basis("unrelated", [BasisComponent("flux", "Φ")])
        flux = _vec(unrelated, flux=1)
        kg = _vec(SI, mass=1)
        with pytest.raises(BasisMismatch):
            ops.multiply_via(flux, kg, graph=self.graph)


class TestDivideVia:
    def setup_method(self) -> None:
        self.economic = _economic_basis()
        self.graph = get_basis_graph().with_transform(_si_to_economic(self.economic))

    def test_same_basis_delegates_to_operator(self) -> None:
        m = _vec(SI, length=1)
        s = _vec(SI, time=1)
        result = ops.divide_via(m, s)
        assert result.basis == SI
        assert result["length"] == 1
        assert result["time"] == -1

    def test_cross_basis_promotes_to_extended(self) -> None:
        usd = _vec(self.economic, currency=1)
        year = _vec(SI, time=1)
        result = ops.divide_via(usd, year, graph=self.graph)
        assert result.basis == self.economic
        assert result["currency"] == 1
        assert result["time"] == -1


# ---------------------------------------------------------------------------
# Graph resolution priority: explicit graph > system.basis_graph > active
# ---------------------------------------------------------------------------


class TestGraphResolution:
    """Cover the three branches of ``ops._resolve_graph``."""

    def setup_method(self) -> None:
        self.economic = _economic_basis()
        self.embedding = _si_to_economic(self.economic)
        self.extended_graph = get_basis_graph().with_transform(self.embedding)

    def test_explicit_graph_wins(self) -> None:
        """``graph=`` kwarg is honoured even when the active graph is
        unrelated."""
        usd = _vec(self.economic, currency=1)
        s = _vec(SI, time=1)
        # Active graph is the default — has no economic transform.
        # Passing ``graph=`` provides one.
        with using_basis_graph(BasisGraph()):
            result = ops.multiply_via(usd, s, graph=self.extended_graph)
        assert result.basis == self.economic
        assert result["currency"] == 1
        assert result["time"] == 1

    def test_system_basis_graph_used_when_no_explicit_graph(self) -> None:
        """``system=`` kwarg supplies the graph when ``graph=`` is omitted."""
        system = dataclasses.replace(UnitSystem.from_globals(), basis_graph=self.extended_graph)
        usd = _vec(self.economic, currency=1)
        s = _vec(SI, time=1)
        # Active graph again deliberately empty so it cannot mediate.
        with using_basis_graph(BasisGraph()):
            result = ops.multiply_via(usd, s, system=system)
        assert result.basis == self.economic

    def test_active_graph_fallback(self) -> None:
        """When neither ``graph=`` nor ``system=`` is given, the active
        ContextVar-scoped graph is used."""
        usd = _vec(self.economic, currency=1)
        s = _vec(SI, time=1)
        with using_basis_graph(self.extended_graph):
            result = ops.multiply_via(usd, s)
        assert result.basis == self.economic

    def test_explicit_graph_beats_system(self) -> None:
        """Explicit ``graph=`` overrides ``system.basis_graph``."""
        # System has the working graph; we force a useless one through graph=.
        system = dataclasses.replace(UnitSystem.from_globals(), basis_graph=self.extended_graph)
        usd = _vec(self.economic, currency=1)
        s = _vec(SI, time=1)
        with pytest.raises(BasisMismatch):
            ops.multiply_via(usd, s, system=system, graph=BasisGraph())


# ---------------------------------------------------------------------------
# Cocone (3-way) fallback: neither a→b nor b→a is clean, but both a and b
# embed into some common third basis.
# ---------------------------------------------------------------------------


class TestUnifyCoconeFallback:
    """``unify`` searches for a common upper-bound basis when neither operand
    directly embeds in the other.
    """

    def setup_method(self) -> None:
        self.flux = Basis("flux", [BasisComponent("flux", "Φ")])

    def _combined(self, name: str = "combined") -> Basis:
        """SI + flux slot, packaged as a combined basis."""
        return Basis(name, list(SI) + [BasisComponent("flux", "Φ")])

    def _si_to_combined(self, combined: Basis) -> BasisTransform:
        n_tgt = len(combined)
        matrix = tuple(
            tuple(Fraction(1) if j == i else Fraction(0) for j in range(n_tgt))
            for i in range(len(SI))
        )
        return BasisTransform(SI, combined, matrix)

    def _flux_to_combined_clean(self, combined: Basis) -> BasisTransform:
        """flux → combined: maps the lone flux axis to the last column."""
        n_tgt = len(combined)
        matrix = ((Fraction(0),) * (n_tgt - 1) + (Fraction(1),),)
        return BasisTransform(self.flux, combined, matrix)

    def _flux_to_combined_lossy(self, combined: Basis) -> BasisTransform:
        """flux → combined: matrix row is all zeros, so any non-zero flux
        component raises LossyProjection on call."""
        n_tgt = len(combined)
        matrix = ((Fraction(0),) * n_tgt,)
        return BasisTransform(self.flux, combined, matrix)

    def test_cocone_bridges_incomparable_bases(self) -> None:
        """``flux`` and SI are incomparable in the embedding order; the
        graph contains both → combined, so unify meets in combined."""
        combined = self._combined()
        g = BasisGraph()
        g.add_transform(self._flux_to_combined_clean(combined))
        g.add_transform(self._si_to_combined(combined))

        flux_vec = _vec(self.flux, flux=1)
        si_vec = _vec(SI, time=1)
        a_, b_ = ops.unify(flux_vec, si_vec, graph=g)
        assert a_.basis == combined
        assert b_.basis == combined
        assert a_["flux"] == 1
        assert b_["time"] == 1

    def test_cocone_skips_lossy_candidate_and_uses_clean_one(self) -> None:
        """When ``common`` has multiple candidates and one is lossy on the
        test vector, the loop continues until it finds a clean one. The
        result lives in the clean candidate's basis regardless of set
        iteration order."""
        combined_bad = self._combined("combined_bad")
        combined_ok = self._combined("combined_ok")

        g = BasisGraph()
        # flux → combined_bad is lossy on flux=1; flux → combined_ok is clean.
        g.add_transform(self._flux_to_combined_lossy(combined_bad))
        g.add_transform(self._flux_to_combined_clean(combined_ok))
        # SI projects cleanly into both.
        g.add_transform(self._si_to_combined(combined_bad))
        g.add_transform(self._si_to_combined(combined_ok))

        flux_vec = _vec(self.flux, flux=1)
        si_vec = _vec(SI, time=1)
        a_, b_ = ops.unify(flux_vec, si_vec, graph=g)
        # Only combined_ok yields a clean projection; whichever iteration
        # order picks, the loop converges there.
        assert a_.basis == combined_ok
        assert b_.basis == combined_ok
        assert a_["flux"] == 1

    def test_cocone_all_candidates_lossy_raises_basis_mismatch(self) -> None:
        """When every candidate in ``common`` is lossy on the test vector,
        the loop exhausts and falls through to ``BasisMismatch``. This
        deterministically exercises the ``continue`` branch for every
        candidate before the fall-through, regardless of iteration order.
        """
        combined1 = self._combined("combined1")
        combined2 = self._combined("combined2")

        g = BasisGraph()
        g.add_transform(self._flux_to_combined_lossy(combined1))
        g.add_transform(self._flux_to_combined_lossy(combined2))
        g.add_transform(self._si_to_combined(combined1))
        g.add_transform(self._si_to_combined(combined2))

        flux_vec = _vec(self.flux, flux=1)
        si_vec = _vec(SI, time=1)
        with pytest.raises(BasisMismatch, match="different bases"):
            ops.unify(flux_vec, si_vec, graph=g)

    def test_cocone_empty_common_raises_basis_mismatch(self) -> None:
        """When ``a.basis`` and ``b.basis`` share no reachable upper bound
        in the graph, ``common`` is empty, the loop never executes, and the
        function falls through to ``BasisMismatch``."""
        # Install only outgoing edges that lead to disjoint targets.
        flux_only = Basis("flux_only", [BasisComponent("flux", "Φ")])
        flux_to_flux_only = BasisTransform(
            self.flux, flux_only, ((Fraction(1),),)
        )
        g = BasisGraph()
        g.add_transform(flux_to_flux_only)
        # SI in this graph reaches only itself.

        flux_vec = _vec(self.flux, flux=1)
        si_vec = _vec(SI, time=1)
        with pytest.raises(BasisMismatch, match="different bases"):
            ops.unify(flux_vec, si_vec, graph=g)
