# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Tests for basis context scoping (v0.8.4)."""

import pytest

from ucon import (
    Basis,
    BasisComponent,
    BasisGraph,
    CGS,
    SI,
    get_default_basis,
    get_basis_graph,
    reset_default_basis_graph,
    set_default_basis_graph,
    using_basis,
    using_basis_graph,
)
from ucon.dimension import Dimension


class TestDefaultBasis:
    """Tests for get_default_basis() and using_basis()."""

    def test_default_basis_is_si(self):
        """No context returns SI."""
        assert get_default_basis() == SI

    def test_using_basis_overrides_default(self):
        """Context sets custom basis."""
        with using_basis(CGS) as b:
            assert b == CGS
            assert get_default_basis() == CGS

    def test_using_basis_restores_on_exit(self):
        """Normal exit restores."""
        assert get_default_basis() == SI
        with using_basis(CGS):
            assert get_default_basis() == CGS
        assert get_default_basis() == SI

    def test_using_basis_restores_on_exception(self):
        """Exception exit restores."""
        assert get_default_basis() == SI
        with pytest.raises(ValueError):
            with using_basis(CGS):
                assert get_default_basis() == CGS
                raise ValueError("test error")
        assert get_default_basis() == SI

    def test_nested_using_basis(self):
        """Inner restores to outer."""
        custom_basis = Basis("Custom", ["foo", "bar"])

        assert get_default_basis() == SI
        with using_basis(CGS):
            assert get_default_basis() == CGS
            with using_basis(custom_basis):
                assert get_default_basis() == custom_basis
            assert get_default_basis() == CGS
        assert get_default_basis() == SI


class TestBasisGraph:
    """Tests for get_basis_graph() and using_basis_graph()."""

    def teardown_method(self):
        """Reset basis graph after each test."""
        reset_default_basis_graph()

    def test_default_basis_graph_has_standard_transforms(self):
        """SI/CGS/CGS-ESU connected."""
        graph = get_basis_graph()
        # SI -> CGS should be reachable
        assert graph.are_connected(SI, CGS)
        # CGS -> SI should be reachable (via embedding)
        assert graph.are_connected(CGS, SI)

    def test_using_basis_graph_overrides_default(self):
        """Context sets custom graph."""
        custom_graph = BasisGraph()
        with using_basis_graph(custom_graph) as g:
            assert g is custom_graph
            assert get_basis_graph() is custom_graph

    def test_using_basis_graph_restores_on_exit(self):
        """Normal exit restores default graph."""
        default_graph = get_basis_graph()
        custom_graph = BasisGraph()
        with using_basis_graph(custom_graph):
            assert get_basis_graph() is custom_graph
        assert get_basis_graph() is default_graph

    def test_using_basis_graph_with_none(self):
        """Passing None to using_basis_graph falls back to default."""
        default_graph = get_basis_graph()
        with using_basis_graph(None):
            # None in context should still return default
            assert get_basis_graph() is default_graph

    def test_set_default_basis_graph_replaces_singleton(self):
        """Module replacement works."""
        custom_graph = BasisGraph()
        original_graph = get_basis_graph()

        set_default_basis_graph(custom_graph)
        assert get_basis_graph() is custom_graph
        assert get_basis_graph() is not original_graph

        # Reset restores to standard graph (lazily built)
        reset_default_basis_graph()
        new_default = get_basis_graph()
        assert new_default is not custom_graph
        # New default should have standard transforms
        assert new_default.are_connected(SI, CGS)


class TestDimensionContextIntegration:
    """Tests for Dimension methods using context basis."""

    def test_dimension_from_components_uses_context_basis(self):
        """CGS context creates CGS dimension."""
        with using_basis(CGS):
            dim = Dimension.from_components(L=1, T=-1, name="velocity")
            assert dim.basis == CGS

    def test_dimension_pseudo_uses_context_basis(self):
        """CGS context creates CGS pseudo-dimension."""
        with using_basis(CGS):
            angle = Dimension.pseudo("angle")
            assert angle.basis == CGS
            assert angle.is_pseudo

    def test_explicit_basis_overrides_context(self):
        """basis=SI wins over context."""
        with using_basis(CGS):
            # Explicit basis should win
            dim = Dimension.from_components(SI, L=1, name="length")
            assert dim.basis == SI

            pseudo = Dimension.pseudo("test", basis=SI)
            assert pseudo.basis == SI

    def test_default_basis_used_without_context(self):
        """SI is used when no context is set."""
        dim = Dimension.from_components(L=1, name="length")
        assert dim.basis == SI

        pseudo = Dimension.pseudo("angle")
        assert pseudo.basis == SI


class TestThreadSafety:
    """Tests verifying context isolation (conceptual, using same thread)."""

    def test_context_isolation_simulation(self):
        """Different contexts are isolated."""
        # Simulate what would happen in different threads/contexts
        # by verifying reset/restore behavior

        # "Thread 1" sets CGS
        with using_basis(CGS):
            assert get_default_basis() == CGS

            # "Thread 2" (nested, but simulates isolation) sets custom
            custom = Basis("Custom", ["x"])
            with using_basis(custom):
                assert get_default_basis() == custom

            # Back to "Thread 1" context
            assert get_default_basis() == CGS

        # Outside all contexts
        assert get_default_basis() == SI
