# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Tests for :func:`ucon.using_conversion_graph`."""

import warnings

from ucon import (
    ConversionGraph,
    get_default_graph,
    using_conversion_graph,
)


class TestUsingConversionGraph:
    """Behavioral tests for using_conversion_graph."""

    def test_does_not_warn(self) -> None:
        custom = ConversionGraph()
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            with using_conversion_graph(custom):
                assert get_default_graph() is custom

    def test_restores_on_exit(self) -> None:
        default_graph = get_default_graph()
        custom = ConversionGraph()
        with using_conversion_graph(custom):
            assert get_default_graph() is custom
        assert get_default_graph() is default_graph

    def test_yields_same_graph(self) -> None:
        custom = ConversionGraph()
        with using_conversion_graph(custom) as g:
            assert g is custom
