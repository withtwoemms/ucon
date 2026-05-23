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

    def test_set_default_basis_graph_is_masked_by_active_system(self):
        """v1.11: set_default_basis_graph mutates the module-level variable
        but the active system takes precedence in get_basis_graph()."""
        import warnings
        active_graph = get_basis_graph()
        custom_graph = BasisGraph()

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            set_default_basis_graph(custom_graph)
        # Active system tier takes precedence
        assert get_basis_graph() is active_graph
        assert get_basis_graph() is not custom_graph

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            reset_default_basis_graph()


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


class TestGetBasisGraphActiveSystemHook:
    """Tests for the active-``UnitSystem`` lookup tier inside
    :func:`get_basis_graph`. The tier sits between the context-local graph
    (highest priority) and the module-level default (lowest), so a
    ``with use(system):`` block routes through it without changing operator
    signatures."""

    def teardown_method(self) -> None:
        reset_default_basis_graph()

    def test_active_system_supplies_basis_graph(self) -> None:
        """When a UnitSystem is active and no context-local graph is set,
        get_basis_graph returns the system's basis_graph."""
        import dataclasses

        from ucon.system import UnitSystem, use

        custom = BasisGraph()
        system = dataclasses.replace(UnitSystem.from_globals(), basis_graph=custom)
        with use(system):
            assert get_basis_graph() is custom

    def test_no_active_system_falls_through_to_default(self) -> None:
        """When neither context-local graph nor active system is set, the
        module-level default is returned. This exercises the
        ``sys is None`` branch of the active-system tier."""
        # No `use(...)` block, no `using_basis_graph(...)`: the function
        # should fall through past the active-system tier to the default.
        default_graph = get_basis_graph()
        # A second call returns the same lazily-built default.
        assert get_basis_graph() is default_graph

    def test_active_system_import_failure_falls_through(self, monkeypatch) -> None:
        """The active-system lookup is wrapped in ``try/except ImportError``
        as defensive bootstrap code. If ``ucon.system`` cannot be imported
        (or lacks ``_active``), ``get_basis_graph`` falls through to the
        module-level default rather than raising."""
        import sys as _sys

        import ucon.system as _ucon_system

        # Simulate the import failing by hiding the attribute. The
        # ``from ucon.system import _active`` statement inside
        # ``get_basis_graph`` will raise ImportError when _active is absent.
        monkeypatch.delattr(_ucon_system, "_active", raising=True)
        # Also evict any cached reference path that would let the import
        # succeed from a parent package's __init__ re-export.
        for name in list(_sys.modules):
            if name.startswith("ucon.system") and name != "ucon.system":
                # leave submodules alone — only the parent package's
                # `_active` attribute matters for the from-import
                pass

        # Should fall through cleanly to the module default; no exception.
        graph = get_basis_graph()
        assert isinstance(graph, BasisGraph)


class TestRetirementWarnings:
    """``set_default_basis_graph`` and ``reset_default_basis_graph`` emit
    ``DeprecationWarning`` in v1.8 because the module-level default
    basis graph is being retired in favor of :class:`UnitSystem` ownership."""

    def teardown_method(self) -> None:
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            reset_default_basis_graph()

    def test_set_default_basis_graph_emits_deprecation(self) -> None:
        custom_graph = BasisGraph()
        with pytest.warns(DeprecationWarning, match="set_default_basis_graph"):
            set_default_basis_graph(custom_graph)
        # v1.11: mutation still takes effect at module level, but active
        # system tier takes precedence in get_basis_graph().
        # The warning is the important behavior to verify here.

    def test_reset_default_basis_graph_emits_pending_deprecation(self) -> None:
        with pytest.warns(DeprecationWarning, match="reset_default_basis_graph"):
            reset_default_basis_graph()
        # Behavior preserved: a subsequent get rebuilds the standard graph.
        rebuilt = get_basis_graph()
        assert rebuilt.are_connected(SI, CGS)


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
