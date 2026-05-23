# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Parametrized tests for all deprecated symbols in ucon v2.0.

Each deprecated symbol is expected to emit ``DeprecationWarning``
(upgraded from ``PendingDeprecationWarning`` in v1.8).
"""

import warnings

import pytest

import ucon
from ucon.system import UnitSystem


# -----------------------------------------------------------------------
# UnitSystem.conversions property
# -----------------------------------------------------------------------

class TestConversionsPropertyDeprecated:

    def test_emits_deprecation_warning(self):
        from ucon.system import active
        s = active()
        with pytest.warns(DeprecationWarning, match="conversion_graph"):
            _ = s.conversions

    def test_returns_conversion_graph(self):
        from ucon.system import active
        s = active()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            assert s.conversions is s.conversion_graph


# -----------------------------------------------------------------------
# UnitSystem(conversions=...) kwarg alias
# -----------------------------------------------------------------------

class TestConversionsKwargDeprecated:

    def test_emits_deprecation_warning(self):
        from ucon.system import active
        parent = active()
        with pytest.warns(DeprecationWarning, match="conversion_graph"):
            UnitSystem(
                basis=parent.basis,
                units=parent.units,
                dimensions=parent.dimensions,
                base_units=parent.base_units,
                conversions=parent.conversion_graph,
                basis_graph=parent.basis_graph,
            )


# -----------------------------------------------------------------------
# using_graph (legacy alias for using_conversion_graph)
# -----------------------------------------------------------------------

class TestUsingGraphDeprecated:

    def test_emits_deprecation_warning(self):
        from ucon import ConversionGraph, using_graph
        custom = ConversionGraph()
        with pytest.warns(DeprecationWarning, match="using_conversion_graph"):
            with using_graph(custom):
                pass


# -----------------------------------------------------------------------
# set_default_basis_graph / reset_default_basis_graph
# -----------------------------------------------------------------------

class TestBasisGraphGlobalsDeprecated:

    def teardown_method(self):
        from ucon.basis.graph import reset_default_basis_graph
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            reset_default_basis_graph()

    def test_set_default_basis_graph_emits_deprecation(self):
        from ucon.basis.graph import BasisGraph, set_default_basis_graph
        with pytest.warns(DeprecationWarning, match="set_default_basis_graph"):
            set_default_basis_graph(BasisGraph())

    def test_reset_default_basis_graph_emits_deprecation(self):
        from ucon.basis.graph import reset_default_basis_graph
        with pytest.warns(DeprecationWarning, match="reset_default_basis_graph"):
            reset_default_basis_graph()


# -----------------------------------------------------------------------
# set_default_graph / reset_default_graph
# -----------------------------------------------------------------------

class TestConversionGraphGlobalsDeprecated:

    def teardown_method(self):
        from ucon.graph import reset_default_graph
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            reset_default_graph()

    def test_set_default_graph_emits_deprecation(self):
        from ucon.graph import ConversionGraph, set_default_graph
        with pytest.warns(DeprecationWarning, match="set_default_graph"):
            set_default_graph(ConversionGraph())

    def test_reset_default_graph_emits_deprecation(self):
        from ucon.graph import reset_default_graph
        with pytest.warns(DeprecationWarning, match="reset_default_graph"):
            reset_default_graph()


# -----------------------------------------------------------------------
# UnitSystem.from_globals()
# -----------------------------------------------------------------------

class TestFromGlobalsDeprecated:

    def test_emits_deprecation_warning(self):
        with pytest.warns(DeprecationWarning, match="from_globals"):
            UnitSystem.from_globals()

    def test_internal_flag_suppresses_warning(self):
        """The _internal=True flag used by active() and __init__.py
        must not emit the warning."""
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            UnitSystem.from_globals(_internal=True)


# -----------------------------------------------------------------------
# get_unit_by_name (legacy alias for parse_unit)
# -----------------------------------------------------------------------

class TestGetUnitByNameDeprecated:

    def test_emits_deprecation_warning(self):
        from ucon.resolver import get_unit_by_name
        with pytest.warns(DeprecationWarning, match="parse_unit"):
            get_unit_by_name("meter")
