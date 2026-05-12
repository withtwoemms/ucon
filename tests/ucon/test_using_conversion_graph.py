# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Tests for the v1.8 canonical :func:`ucon.using_conversion_graph` and its
:class:`PendingDeprecationWarning` alias :func:`ucon.using_graph`.

The rename brings the conversion-graph context manager into symmetry with
:func:`ucon.basis.using_basis_graph` and the planned v2 ``UnitSystem``
field naming (``conversion_graph`` rather than ``conversions``).
"""

import warnings

import pytest

from ucon import (
    ConversionGraph,
    get_default_graph,
    using_conversion_graph,
    using_graph,
)


class TestUsingConversionGraph:
    """Behavioral tests for the canonical name."""

    def test_canonical_does_not_warn(self) -> None:
        custom = ConversionGraph()
        with warnings.catch_warnings():
            warnings.simplefilter("error", PendingDeprecationWarning)
            with using_conversion_graph(custom):
                assert get_default_graph() is custom

    def test_canonical_restores_on_exit(self) -> None:
        default_graph = get_default_graph()
        custom = ConversionGraph()
        with using_conversion_graph(custom):
            assert get_default_graph() is custom
        assert get_default_graph() is default_graph

    def test_canonical_yields_same_graph(self) -> None:
        custom = ConversionGraph()
        with using_conversion_graph(custom) as g:
            assert g is custom


class TestUsingGraphAlias:
    """The legacy :func:`using_graph` name is a PendingDeprecationWarning alias."""

    def test_alias_emits_pending_deprecation(self) -> None:
        custom = ConversionGraph()
        with pytest.warns(PendingDeprecationWarning, match="using_conversion_graph"):
            with using_graph(custom):
                pass

    def test_alias_preserves_behavior(self) -> None:
        """Despite the warning, the alias still scopes the graph correctly."""
        custom = ConversionGraph()
        default_graph = get_default_graph()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", PendingDeprecationWarning)
            with using_graph(custom):
                assert get_default_graph() is custom
            assert get_default_graph() is default_graph
