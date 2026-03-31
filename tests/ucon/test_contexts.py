# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""Tests for conversion contexts (ucon.contexts)."""

import unittest

from ucon import units, Number
from ucon.contexts import (
    ContextEdge,
    ConversionContext,
    using_context,
    _build_spectroscopy,
    _build_boltzmann,
)
from ucon.graph import get_default_graph
from ucon.maps import LinearMap, ReciprocalMap


class TestContextEdge(unittest.TestCase):
    """Test ContextEdge dataclass."""

    def test_creation(self):
        """ContextEdge stores src, dst, map."""
        edge = ContextEdge(
            src=units.meter,
            dst=units.hertz,
            map=ReciprocalMap(299792458.0),
        )
        self.assertIs(edge.src, units.meter)
        self.assertIs(edge.dst, units.hertz)
        self.assertIsInstance(edge.map, ReciprocalMap)


class TestConversionContext(unittest.TestCase):
    """Test ConversionContext dataclass."""

    def test_creation(self):
        """ConversionContext stores name and edges."""
        ctx = ConversionContext(
            name="test",
            edges=(
                ContextEdge(
                    src=units.meter,
                    dst=units.hertz,
                    map=ReciprocalMap(299792458.0),
                ),
            ),
            description="A test context.",
        )
        self.assertEqual(ctx.name, "test")
        self.assertEqual(len(ctx.edges), 1)
        self.assertEqual(ctx.description, "A test context.")

    def test_spectroscopy_structure(self):
        """_build_spectroscopy returns valid context with 4 edges."""
        ctx = _build_spectroscopy()
        self.assertEqual(ctx.name, "spectroscopy")
        self.assertEqual(len(ctx.edges), 4)

    def test_boltzmann_structure(self):
        """_build_boltzmann returns valid context with 1 edge."""
        ctx = _build_boltzmann()
        self.assertEqual(ctx.name, "boltzmann")
        self.assertEqual(len(ctx.edges), 1)


class TestUsingContext(unittest.TestCase):
    """Test using_context() context manager."""

    def test_spectroscopy_wavelength_to_frequency(self):
        """Wavelength -> frequency via c = lambda * f."""
        from ucon.contexts import spectroscopy
        wavelength_m = 500e-9  # 500 nm
        expected_freq = 299792458.0 / wavelength_m

        with using_context(spectroscopy):
            result = units.meter(wavelength_m).to(units.hertz)

        self.assertIsInstance(result, Number)
        self.assertAlmostEqual(result.quantity, expected_freq, places=0)

    def test_spectroscopy_frequency_to_wavelength(self):
        """Frequency -> wavelength (inverse direction)."""
        from ucon.contexts import spectroscopy
        freq = 5e14
        expected_wavelength = 299792458.0 / freq

        with using_context(spectroscopy):
            result = units.hertz(freq).to(units.meter)

        self.assertAlmostEqual(result.quantity, expected_wavelength, delta=1e-16)

    def test_spectroscopy_frequency_to_energy(self):
        """Frequency -> energy via E = h * f."""
        from ucon.contexts import spectroscopy
        freq = 5e14
        h = 6.62607015e-34
        expected_energy = h * freq

        with using_context(spectroscopy):
            result = units.hertz(freq).to(units.joule)

        self.assertAlmostEqual(result.quantity, expected_energy, places=50)

    def test_boltzmann_temperature_to_energy(self):
        """Temperature -> energy via E = k_B * T."""
        from ucon.contexts import boltzmann
        temp = 300.0
        k_B = 1.380649e-23
        expected_energy = k_B * temp

        with using_context(boltzmann):
            result = units.kelvin(temp).to(units.joule)

        self.assertAlmostEqual(result.quantity, expected_energy, places=30)

    def test_boltzmann_energy_to_temperature(self):
        """Energy -> temperature (inverse)."""
        from ucon.contexts import boltzmann
        k_B = 1.380649e-23
        energy = 4.14e-21  # ~300K

        with using_context(boltzmann):
            result = units.joule(energy).to(units.kelvin)

        expected_temp = energy / k_B
        self.assertAlmostEqual(result.quantity, expected_temp, places=5)

    def test_multiple_contexts(self):
        """Multiple contexts compose in one using_context() call."""
        from ucon.contexts import spectroscopy, boltzmann

        with using_context(spectroscopy, boltzmann):
            # Both spectroscopy and boltzmann edges should be available
            freq_result = units.meter(500e-9).to(units.hertz)
            temp_result = units.kelvin(300).to(units.joule)

        self.assertIsInstance(freq_result, Number)
        self.assertIsInstance(temp_result, Number)

    def test_graph_restored_after_exit(self):
        """Original graph is unmodified after context exits."""
        from ucon.contexts import spectroscopy
        from ucon.graph import DimensionMismatch

        with using_context(spectroscopy):
            # Should work inside context
            units.meter(500e-9).to(units.hertz)

        # Outside context, cross-dimensional conversion should fail
        with self.assertRaises(DimensionMismatch):
            units.meter(500e-9).to(units.hertz)

    def test_yields_extended_graph(self):
        """using_context() yields the extended graph."""
        from ucon.contexts import spectroscopy

        with using_context(spectroscopy) as graph:
            self.assertIsNotNone(graph)
            # The yielded graph should support context conversions
            result = units.meter(500e-9).to(units.hertz)
            self.assertIsInstance(result, Number)


class TestLazySingletons(unittest.TestCase):
    """Test module-level __getattr__ lazy initialization."""

    def test_spectroscopy_is_cached(self):
        """Subsequent accesses return the same object."""
        from ucon import contexts
        s1 = contexts.spectroscopy
        s2 = contexts.spectroscopy
        self.assertIs(s1, s2)
        self.assertIsInstance(s1, ConversionContext)

    def test_boltzmann_is_cached(self):
        """Subsequent accesses return the same object."""
        from ucon import contexts
        b1 = contexts.boltzmann
        b2 = contexts.boltzmann
        self.assertIs(b1, b2)
        self.assertIsInstance(b1, ConversionContext)

    def test_unknown_attr_raises(self):
        """Accessing unknown attribute raises AttributeError."""
        from ucon import contexts
        with self.assertRaises(AttributeError):
            _ = contexts.nonexistent_context


if __name__ == '__main__':
    unittest.main()
