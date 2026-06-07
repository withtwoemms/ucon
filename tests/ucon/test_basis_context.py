# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Tests for basis context scoping via the active UnitSystem."""

from ucon import CGS, SI
from ucon.dimension import Dimension
from ucon.system import active_system, use


class TestDimensionContextIntegration:
    """Tests for Dimension methods using context basis."""

    def test_dimension_from_components_uses_context_basis(self):
        """CGS-active UnitSystem creates CGS dimension."""
        with use(active_system().with_basis(CGS)):
            dim = Dimension.from_components(L=1, T=-1, name="velocity")
            assert dim.basis == CGS

    def test_dimension_pseudo_uses_context_basis(self):
        """CGS-active UnitSystem creates CGS pseudo-dimension."""
        with use(active_system().with_basis(CGS)):
            angle = Dimension.pseudo("angle")
            assert angle.basis == CGS
            assert angle.is_pseudo

    def test_explicit_basis_overrides_context(self):
        """basis=SI wins over active system."""
        with use(active_system().with_basis(CGS)):
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
