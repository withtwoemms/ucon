# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Tests for cross-basis unit conversions.

Verifies that CGS and CGS-ESU units are defined in their native basis
with BasisTransform-mediated edges bridging to SI.
"""
import math
import unittest

from ucon import (
    Dimension,
    get_default_graph,
    get_unit_by_name,
    units,
    using_graph,
)
from ucon.basis.builtin import CGS, CGS_ESU, NATURAL, SI
from ucon.core import RebasedUnit
from ucon.dimension import (
    CGS_FORCE,
    CGS_ENERGY,
    CGS_PRESSURE,
    CGS_DYNAMIC_VISCOSITY,
    CGS_KINEMATIC_VISCOSITY,
    CGS_ESU_CHARGE,
    CGS_ESU_CURRENT,
    CGS_ESU_VOLTAGE,
    CGS_ESU_RESISTANCE,
    CGS_ESU_CAPACITANCE,
    CGS_ESU_MAGNETIC_FLUX_DENSITY,
    CGS_ESU_MAGNETIC_FLUX,
    CGS_ESU_MAGNETIC_FIELD_STRENGTH,
    NATURAL_ENERGY,
    FORCE,
    ENERGY,
    PRESSURE,
    DYNAMIC_VISCOSITY,
    KINEMATIC_VISCOSITY,
)


class TestCGSDimensionIsolation(unittest.TestCase):
    """CGS dimensions are distinct from their SI counterparts."""

    def test_cgs_force_is_not_si_force(self):
        self.assertNotEqual(units.dyne.dimension, FORCE)

    def test_cgs_energy_is_not_si_energy(self):
        self.assertNotEqual(units.erg.dimension, ENERGY)

    def test_cgs_pressure_is_not_si_pressure(self):
        self.assertNotEqual(units.barye.dimension, PRESSURE)

    def test_cgs_dynamic_viscosity_is_not_si(self):
        self.assertNotEqual(units.poise.dimension, DYNAMIC_VISCOSITY)

    def test_cgs_kinematic_viscosity_is_not_si(self):
        self.assertNotEqual(units.stokes.dimension, KINEMATIC_VISCOSITY)

    def test_cgs_units_have_cgs_basis(self):
        for unit in (units.dyne, units.erg, units.barye, units.poise, units.stokes):
            self.assertEqual(
                unit.dimension.basis, CGS,
                f"{unit.name} should have CGS basis, got {unit.dimension.basis.name}",
            )

    def test_cgs_esu_units_have_cgs_esu_basis(self):
        for unit in (
            units.statcoulomb, units.statampere, units.statvolt,
            units.statohm, units.statfarad, units.gauss,
            units.maxwell, units.oersted,
        ):
            self.assertEqual(
                unit.dimension.basis, CGS_ESU,
                f"{unit.name} should have CGS-ESU basis, got {unit.dimension.basis.name}",
            )


class TestCGSDimensionCorrectness(unittest.TestCase):
    """CGS dimension vectors are correct."""

    def test_dyne_dimension(self):
        self.assertEqual(units.dyne.dimension, CGS_FORCE)

    def test_erg_dimension(self):
        self.assertEqual(units.erg.dimension, CGS_ENERGY)

    def test_barye_dimension(self):
        self.assertEqual(units.barye.dimension, CGS_PRESSURE)

    def test_poise_dimension(self):
        self.assertEqual(units.poise.dimension, CGS_DYNAMIC_VISCOSITY)

    def test_stokes_dimension(self):
        self.assertEqual(units.stokes.dimension, CGS_KINEMATIC_VISCOSITY)


class TestCGSESUDimensionCorrectness(unittest.TestCase):
    """CGS-ESU dimension vectors are correct."""

    def test_statcoulomb_dimension(self):
        self.assertEqual(units.statcoulomb.dimension, CGS_ESU_CHARGE)

    def test_statampere_dimension(self):
        self.assertEqual(units.statampere.dimension, CGS_ESU_CURRENT)

    def test_statvolt_dimension(self):
        self.assertEqual(units.statvolt.dimension, CGS_ESU_VOLTAGE)

    def test_statohm_dimension(self):
        self.assertEqual(units.statohm.dimension, CGS_ESU_RESISTANCE)

    def test_statfarad_dimension(self):
        self.assertEqual(units.statfarad.dimension, CGS_ESU_CAPACITANCE)

    def test_gauss_dimension(self):
        self.assertEqual(units.gauss.dimension, CGS_ESU_MAGNETIC_FLUX_DENSITY)

    def test_maxwell_dimension(self):
        self.assertEqual(units.maxwell.dimension, CGS_ESU_MAGNETIC_FLUX)

    def test_oersted_dimension(self):
        self.assertEqual(units.oersted.dimension, CGS_ESU_MAGNETIC_FIELD_STRENGTH)


class TestCGSMechanicalConversions(unittest.TestCase):
    """Cross-basis CGS ↔ SI conversions."""

    def setUp(self):
        self.graph = get_default_graph()

    def test_dyne_to_newton(self):
        m = self.graph.convert(src=units.dyne, dst=units.newton)
        self.assertAlmostEqual(m(1), 1e-5, places=10)

    def test_newton_to_dyne(self):
        m = self.graph.convert(src=units.newton, dst=units.dyne)
        self.assertAlmostEqual(m(1), 1e5, places=5)

    def test_erg_to_joule(self):
        m = self.graph.convert(src=units.erg, dst=units.joule)
        self.assertAlmostEqual(m(1), 1e-7, places=12)

    def test_joule_to_erg(self):
        m = self.graph.convert(src=units.joule, dst=units.erg)
        self.assertAlmostEqual(m(1), 1e7, places=0)

    def test_barye_to_pascal(self):
        m = self.graph.convert(src=units.barye, dst=units.pascal)
        self.assertAlmostEqual(m(1), 0.1, places=5)

    def test_poise_to_pascal_second(self):
        m = self.graph.convert(src=units.poise, dst=units.pascal_second)
        self.assertAlmostEqual(m(1), 0.1, places=5)

    def test_stokes_to_square_meter_per_second(self):
        m = self.graph.convert(src=units.stokes, dst=units.square_meter_per_second)
        self.assertAlmostEqual(m(1), 1e-4, places=9)

    def test_dyne_roundtrip(self):
        """1 N → dyn → N round-trip preserves value."""
        fwd = self.graph.convert(src=units.newton, dst=units.dyne)
        rev = self.graph.convert(src=units.dyne, dst=units.newton)
        self.assertAlmostEqual(rev(fwd(1)), 1.0, places=10)


class TestCGSESUElectromagneticConversions(unittest.TestCase):
    """Cross-basis CGS-ESU ↔ SI electromagnetic conversions."""

    def setUp(self):
        self.graph = get_default_graph()

    def test_ampere_to_statampere(self):
        m = self.graph.convert(src=units.ampere, dst=units.statampere)
        self.assertAlmostEqual(m(1), 2.99792458e9, places=0)

    def test_coulomb_to_statcoulomb(self):
        m = self.graph.convert(src=units.coulomb, dst=units.statcoulomb)
        self.assertAlmostEqual(m(1), 2.99792458e9, places=0)

    def test_volt_to_statvolt(self):
        m = self.graph.convert(src=units.volt, dst=units.statvolt)
        expected = 1 / 2.99792458e2
        self.assertAlmostEqual(m(1), expected, places=8)

    def test_ohm_to_statohm(self):
        m = self.graph.convert(src=units.ohm, dst=units.statohm)
        expected = 1 / 8.9875517873681764e11
        self.assertAlmostEqual(m(1), expected, places=20)

    def test_farad_to_statfarad(self):
        m = self.graph.convert(src=units.farad, dst=units.statfarad)
        self.assertAlmostEqual(m(1), 8.9875517873681764e11, places=0)

    def test_tesla_to_gauss(self):
        m = self.graph.convert(src=units.tesla, dst=units.gauss)
        self.assertAlmostEqual(m(1), 1e4, places=0)

    def test_weber_to_maxwell(self):
        m = self.graph.convert(src=units.weber, dst=units.maxwell)
        self.assertAlmostEqual(m(1), 1e8, places=0)

    def test_ampere_per_meter_to_oersted(self):
        m = self.graph.convert(src=units.ampere_per_meter, dst=units.oersted)
        expected = 4 * math.pi * 1e-3
        self.assertAlmostEqual(m(1), expected, places=8)

    def test_statampere_roundtrip(self):
        """1 A → statA → A round-trip preserves value."""
        fwd = self.graph.convert(src=units.ampere, dst=units.statampere)
        rev = self.graph.convert(src=units.statampere, dst=units.ampere)
        self.assertAlmostEqual(rev(fwd(1)), 1.0, places=5)


class TestRebasedUnits(unittest.TestCase):
    """Verify RebasedUnit bridge nodes are present."""

    def test_rebased_units_exist(self):
        graph = get_default_graph()
        rebased = graph.list_rebased_units()
        # CGS mechanical units should have rebased entries
        for unit in (units.dyne, units.erg, units.barye, units.poise, units.stokes):
            self.assertIn(
                unit, rebased,
                f"{unit.name} should have a RebasedUnit in the graph",
            )

    def test_rebased_units_are_rebased_type(self):
        graph = get_default_graph()
        rebased = graph.list_rebased_units()
        for unit, rebased_unit in rebased.items():
            self.assertIsInstance(rebased_unit, RebasedUnit)

    def test_si_em_units_rebased_to_cgs_esu(self):
        """SI EM units should be rebased when bridging to CGS-ESU."""
        graph = get_default_graph()
        rebased = graph.list_rebased_units()
        for unit in (
            units.ampere, units.coulomb, units.volt,
            units.ohm, units.farad, units.tesla,
            units.weber, units.ampere_per_meter,
        ):
            self.assertIn(
                unit, rebased,
                f"{unit.name} should have a RebasedUnit for CGS-ESU bridging",
            )


class TestBasisGraphAttached(unittest.TestCase):
    """The default graph has a BasisGraph."""

    def test_basis_graph_is_set(self):
        graph = get_default_graph()
        self.assertIsNotNone(graph._basis_graph)

    def test_basis_graph_has_transforms(self):
        graph = get_default_graph()
        bg = graph._basis_graph
        self.assertTrue(bg.are_connected(SI, CGS))
        self.assertTrue(bg.are_connected(SI, CGS_ESU))


class TestCrossSystemNameResolution(unittest.TestCase):
    """CGS/CGS-ESU units are resolvable by name in the default graph."""

    def test_resolve_dyne(self):
        graph = get_default_graph()
        with using_graph(graph):
            resolved = get_unit_by_name('dyne')
            self.assertEqual(resolved, units.dyne)

    def test_resolve_gauss(self):
        graph = get_default_graph()
        with using_graph(graph):
            resolved = get_unit_by_name('gauss')
            self.assertEqual(resolved, units.gauss)

    def test_resolve_statampere(self):
        graph = get_default_graph()
        with using_graph(graph):
            resolved = get_unit_by_name('statampere')
            self.assertEqual(resolved, units.statampere)

    def test_resolve_oersted_by_alias(self):
        graph = get_default_graph()
        with using_graph(graph):
            resolved = get_unit_by_name('Oe')
            self.assertEqual(resolved, units.oersted)


class TestNaturalUnitDimensionIsolation(unittest.TestCase):
    """Natural-unit dimensions are distinct from their SI counterparts."""

    def test_ev_dimension_is_not_si_energy(self):
        self.assertNotEqual(units.electron_volt.dimension, ENERGY)

    def test_ev_dimension_is_natural_energy(self):
        self.assertEqual(units.electron_volt.dimension, NATURAL_ENERGY)

    def test_ev_has_natural_basis(self):
        self.assertEqual(
            units.electron_volt.dimension.basis, NATURAL,
            f"electron_volt should have natural basis, got {units.electron_volt.dimension.basis.name}",
        )

    def test_hartree_has_natural_basis(self):
        self.assertEqual(units.hartree.dimension, NATURAL_ENERGY)
        self.assertEqual(units.hartree.dimension.basis, NATURAL)

    def test_rydberg_has_natural_basis(self):
        self.assertEqual(units.rydberg.dimension, NATURAL_ENERGY)
        self.assertEqual(units.rydberg.dimension.basis, NATURAL)


class TestNaturalUnitConversions(unittest.TestCase):
    """Cross-basis natural ↔ SI conversions."""

    def setUp(self):
        self.graph = get_default_graph()

    def test_joule_to_ev(self):
        m = self.graph.convert(src=units.joule, dst=units.electron_volt)
        self.assertAlmostEqual(m(1), 1 / 1.602176634e-19, places=0)

    def test_ev_to_joule(self):
        m = self.graph.convert(src=units.electron_volt, dst=units.joule)
        self.assertAlmostEqual(m(1), 1.602176634e-19, places=30)

    def test_ev_joule_roundtrip(self):
        """1 J → eV → J round-trip preserves value."""
        fwd = self.graph.convert(src=units.joule, dst=units.electron_volt)
        rev = self.graph.convert(src=units.electron_volt, dst=units.joule)
        self.assertAlmostEqual(rev(fwd(1)), 1.0, places=10)

    def test_ev_rebased_unit_exists(self):
        """joule should have a RebasedUnit for natural bridging."""
        rebased = self.graph.list_rebased_units()
        self.assertIn(
            units.joule, rebased,
            "joule should have a RebasedUnit for natural-unit bridging",
        )

    def test_resolve_ev_by_alias(self):
        with using_graph(self.graph):
            resolved = get_unit_by_name('eV')
            self.assertEqual(resolved, units.electron_volt)

    def test_hartree_to_joule(self):
        m = self.graph.convert(src=units.hartree, dst=units.joule)
        self.assertAlmostEqual(m(1), 4.3597447222071e-18, places=30)

    def test_rydberg_to_joule(self):
        m = self.graph.convert(src=units.rydberg, dst=units.joule)
        self.assertAlmostEqual(m(1), 2.1798723611035e-18, places=30)

    def test_hartree_to_ev(self):
        m = self.graph.convert(src=units.hartree, dst=units.electron_volt)
        self.assertAlmostEqual(m(1), 27.211386, places=4)

    def test_rydberg_to_ev(self):
        m = self.graph.convert(src=units.rydberg, dst=units.electron_volt)
        self.assertAlmostEqual(m(1), 13.605693, places=4)

    def test_hartree_rydberg_ratio(self):
        """1 Eh = 2 Ry by definition."""
        eh_to_j = self.graph.convert(src=units.hartree, dst=units.joule)
        ry_to_j = self.graph.convert(src=units.rydberg, dst=units.joule)
        self.assertAlmostEqual(eh_to_j(1) / ry_to_j(1), 2.0, places=10)


class TestCrossBasisCallableAndTo(unittest.TestCase):
    """Unit.__call__() and Number.to() work for cross-basis units."""

    def test_callable_natural_unit(self):
        n = units.electron_volt(1)
        self.assertEqual(n.quantity, 1)
        self.assertEqual(n.unit.dimension, NATURAL_ENERGY)

    def test_callable_cgs_unit(self):
        n = units.dyne(1)
        self.assertEqual(n.quantity, 1)
        self.assertEqual(n.unit.dimension, CGS_FORCE)

    def test_callable_cgs_esu_unit(self):
        n = units.gauss(1)
        self.assertEqual(n.quantity, 1)
        self.assertEqual(n.unit.dimension, CGS_ESU_MAGNETIC_FLUX_DENSITY)

    def test_number_to_cross_basis_natural(self):
        result = units.joule(1).to(units.electron_volt)
        self.assertAlmostEqual(result.quantity, 1 / 1.602176634e-19, places=0)

    def test_number_to_cross_basis_cgs(self):
        result = units.newton(1).to(units.dyne)
        self.assertAlmostEqual(result.quantity, 1e5, places=5)

    def test_number_to_cross_basis_cgs_esu(self):
        result = units.ampere(1).to(units.statampere)
        self.assertAlmostEqual(result.quantity, 2.99792458e9, places=0)

    def test_number_to_string_cross_basis(self):
        result = units.joule(1).to("eV")
        self.assertAlmostEqual(result.quantity, 1 / 1.602176634e-19, places=0)

    def test_cross_basis_roundtrip_via_to(self):
        original = units.joule(1)
        via_ev = original.to(units.electron_volt)
        back = via_ev.to(units.joule)
        self.assertAlmostEqual(back.quantity, 1.0, places=10)

    def test_cross_basis_roundtrip_cgs_via_to(self):
        original = units.newton(1)
        via_dyne = original.to(units.dyne)
        back = via_dyne.to(units.newton)
        self.assertAlmostEqual(back.quantity, 1.0, places=10)


if __name__ == '__main__':
    unittest.main()
