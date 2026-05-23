# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
Tests for system initialization — verifying units, constants, and graph
are accessible through the active UnitSystem.

Replaces the former ``test__loader.py`` after elimination of ``ucon._loader``.
"""
from __future__ import annotations

from ucon.constants import Constant
from ucon.core import Unit
from ucon.graph import ConversionGraph
from ucon.system import active


class TestActiveSystemGraph:
    """Tests for the conversion graph in the active system."""

    def test_returns_conversion_graph(self):
        system = active()
        assert isinstance(system.conversion_graph, ConversionGraph)

    def test_graph_has_units(self):
        graph = active().conversion_graph
        assert 'meter' in graph._name_registry_cs
        assert 'kilogram' in graph._name_registry_cs
        assert 'second' in graph._name_registry_cs

    def test_graph_has_constants(self):
        graph = active().conversion_graph
        assert len(graph._package_constants) >= 26


class TestActiveSystemUnits:
    """Tests for units in the active system."""

    def test_returns_dict(self):
        units = active().units
        assert isinstance(units, dict)

    def test_contains_core_si_units(self):
        units = active().units
        for name in ('meter', 'kilogram', 'second', 'ampere', 'kelvin', 'mole', 'candela'):
            assert name in units, f"Missing core SI unit: {name}"
            assert isinstance(units[name], Unit)

    def test_contains_derived_units(self):
        units = active().units
        for name in ('newton', 'joule', 'watt', 'pascal', 'hertz'):
            assert name in units, f"Missing derived unit: {name}"

    def test_keyed_by_canonical_name(self):
        """Keys match the Unit.name attribute."""
        units = active().units
        for name, unit in units.items():
            assert name == unit.name, f"Key {name!r} does not match unit.name {unit.name!r}"


class TestActiveSystemConstants:
    """Tests for constants in the active system."""

    def test_returns_dict(self):
        constants = active().constants
        assert isinstance(constants, dict)

    def test_contains_speed_of_light_by_symbol(self):
        constants = active().constants
        assert 'c' in constants
        assert constants['c'].symbol == 'c'

    def test_contains_speed_of_light_by_alias(self):
        constants = active().constants
        assert 'speed_of_light' in constants
        assert constants['speed_of_light'].symbol == 'c'

    def test_contains_planck_constant(self):
        constants = active().constants
        assert 'h' in constants
        assert constants['h'].name == 'Planck constant'

    def test_contains_gravitational_constant(self):
        constants = active().constants
        assert 'G' in constants
        assert constants['G'].uncertainty is not None  # measured, not exact

    def test_all_values_are_constants(self):
        constants = active().constants
        for key, val in constants.items():
            assert isinstance(val, Constant), f"constants[{key!r}] is {type(val)}, expected Constant"


class TestObjectIdentity:
    """Verify that units in the system are the same objects as in the graph."""

    def test_units_are_same_objects(self):
        """active().units['meter'] is active().conversion_graph._name_registry_cs['meter']"""
        system = active()
        for name in ('meter', 'kilogram', 'second', 'joule'):
            assert system.units[name] is system.conversion_graph._name_registry_cs[name], (
                f"Unit {name!r} is not the same object in units and conversion_graph"
            )
