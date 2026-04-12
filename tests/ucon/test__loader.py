# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
Tests for ucon._loader — the central TOML loader with single-load caching.
"""
from __future__ import annotations

import pytest

from ucon._loader import get_constants, get_graph, get_units, reset
from ucon.constants import Constant
from ucon.core import Unit
from ucon.graph import ConversionGraph


class TestGetGraph:
    """Tests for get_graph()."""

    def test_returns_conversion_graph(self):
        graph = get_graph()
        assert isinstance(graph, ConversionGraph)

    def test_graph_has_units(self):
        graph = get_graph()
        # Should contain at least the core SI units
        assert 'meter' in graph._name_registry_cs
        assert 'kilogram' in graph._name_registry_cs
        assert 'second' in graph._name_registry_cs

    def test_graph_has_constants(self):
        graph = get_graph()
        assert len(graph._package_constants) >= 26


class TestGetUnits:
    """Tests for get_units()."""

    def test_returns_dict(self):
        units = get_units()
        assert isinstance(units, dict)

    def test_contains_core_si_units(self):
        units = get_units()
        for name in ('meter', 'kilogram', 'second', 'ampere', 'kelvin', 'mole', 'candela'):
            assert name in units, f"Missing core SI unit: {name}"
            assert isinstance(units[name], Unit)

    def test_contains_derived_units(self):
        units = get_units()
        for name in ('newton', 'joule', 'watt', 'pascal', 'hertz'):
            assert name in units, f"Missing derived unit: {name}"

    def test_keyed_by_canonical_name(self):
        """Keys match the Unit.name attribute."""
        units = get_units()
        for name, unit in units.items():
            assert name == unit.name, f"Key {name!r} does not match unit.name {unit.name!r}"


class TestGetConstants:
    """Tests for get_constants()."""

    def test_returns_dict(self):
        constants = get_constants()
        assert isinstance(constants, dict)

    def test_contains_speed_of_light_by_symbol(self):
        constants = get_constants()
        assert 'c' in constants
        assert constants['c'].symbol == 'c'

    def test_contains_speed_of_light_by_alias(self):
        constants = get_constants()
        assert 'speed_of_light' in constants
        assert constants['speed_of_light'].symbol == 'c'

    def test_contains_planck_constant(self):
        constants = get_constants()
        assert 'h' in constants
        assert constants['h'].name == 'Planck constant'

    def test_contains_gravitational_constant(self):
        constants = get_constants()
        assert 'G' in constants
        assert constants['G'].uncertainty is not None  # measured, not exact

    def test_all_values_are_constants(self):
        constants = get_constants()
        for key, val in constants.items():
            assert isinstance(val, Constant), f"constants[{key!r}] is {type(val)}, expected Constant"


class TestObjectIdentity:
    """Verify that loader returns the same objects as the graph."""

    def test_units_are_same_objects(self):
        """get_units()['meter'] is get_graph()._name_registry_cs['meter']"""
        units = get_units()
        graph = get_graph()
        for name in ('meter', 'kilogram', 'second', 'joule'):
            assert units[name] is graph._name_registry_cs[name], (
                f"Unit {name!r} is not the same object in get_units() and get_graph()"
            )


class TestCaching:
    """Verify single-load caching behavior."""

    def test_get_graph_returns_same_object(self):
        g1 = get_graph()
        g2 = get_graph()
        assert g1 is g2

    def test_get_units_returns_same_dict(self):
        u1 = get_units()
        u2 = get_units()
        assert u1 is u2

    def test_get_constants_returns_same_dict(self):
        c1 = get_constants()
        c2 = get_constants()
        assert c1 is c2

    def test_reset_clears_cache(self):
        """After reset(), a fresh graph is loaded."""
        g1 = get_graph()
        reset()
        g2 = get_graph()
        # After reset, a new graph is built — it should not be the same object
        assert g1 is not g2
        # But it should have the same content
        assert 'meter' in get_units()
