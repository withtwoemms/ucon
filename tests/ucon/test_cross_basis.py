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
from ucon.basis.builtin import CGS, CGS_ESU, CGS_EMU, NATURAL, PLANCK, ATOMIC, SI
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
    CGS_EMU_CURRENT,
    CGS_EMU_CHARGE,
    CGS_EMU_VOLTAGE,
    CGS_EMU_RESISTANCE,
    CGS_EMU_CAPACITANCE,
    CGS_EMU_INDUCTANCE,
    NATURAL_ENERGY,
    PLANCK_ENERGY,
    PLANCK_LENGTH,
    ATOMIC_ENERGY,
    ATOMIC_LENGTH,
    FORCE,
    ENERGY,
    PRESSURE,
    CURRENT,
    CHARGE,
    VOLTAGE,
    RESISTANCE,
    CAPACITANCE,
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
        for unit, rebased_list in rebased.items():
            for rebased_unit in rebased_list:
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

    def test_hartree_has_atomic_basis(self):
        self.assertEqual(units.hartree.dimension, ATOMIC_ENERGY)
        self.assertEqual(units.hartree.dimension.basis, ATOMIC)

    def test_rydberg_has_atomic_basis(self):
        self.assertEqual(units.rydberg.dimension, ATOMIC_ENERGY)
        self.assertEqual(units.rydberg.dimension.basis, ATOMIC)


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


class TestCrossBasisProductFallback(unittest.TestCase):
    """Cross-basis conversion via UnitProduct wrapping.

    When a CGS unit is wrapped as a UnitProduct (e.g., from_unit(poise))
    and the target is also a UnitProduct (e.g., parsed from "Pa·s"),
    the dimension mismatch (cgs_dynamic_viscosity != dynamic_viscosity)
    must fall back to Unit-level cross-basis conversion.
    """

    def setUp(self):
        self.graph = get_default_graph()

    def test_poise_product_to_pascal_second_product(self):
        from ucon.core import UnitProduct, UnitFactor, Scale
        src = UnitProduct.from_unit(units.poise)
        dst = UnitProduct({UnitFactor(units.pascal_second, Scale.one): 1})
        m = self.graph.convert(src=src, dst=dst)
        self.assertAlmostEqual(m(1), 0.1, places=5)

    def test_stokes_product_to_square_meter_per_second_product(self):
        from ucon.core import UnitProduct
        src = UnitProduct.from_unit(units.stokes)
        dst = UnitProduct.from_unit(units.square_meter_per_second)
        m = self.graph.convert(src=src, dst=dst)
        self.assertAlmostEqual(m(1), 1e-4, places=9)

    def test_galileo_product_to_meter_per_second_squared_product(self):
        from ucon.core import UnitProduct
        src = UnitProduct.from_unit(units.galileo)
        dst = UnitProduct.from_unit(units.meter_per_second_squared)
        m = self.graph.convert(src=src, dst=dst)
        self.assertAlmostEqual(m(1), 0.01, places=5)

    def test_reyn_product_to_pascal_second_product(self):
        from ucon.core import UnitProduct
        src = UnitProduct.from_unit(units.reyn)
        dst = UnitProduct.from_unit(units.pascal_second)
        m = self.graph.convert(src=src, dst=dst)
        self.assertAlmostEqual(m(1), 6894.757, places=2)


class TestCrossBasisStringResolution(unittest.TestCase):
    """End-to-end cross-basis conversion using string aliases.

    Verifies that Number.to("Pa·s") works when the source is a CGS unit,
    exercising the full resolver → graph → cross-basis path.
    """

    def test_poise_to_pa_s_string(self):
        result = units.poise(1).to(units.pascal_second)
        self.assertAlmostEqual(result.quantity, 0.1, places=5)

    def test_stokes_to_square_meter_per_second_string(self):
        result = units.stokes(1).to(units.square_meter_per_second)
        self.assertAlmostEqual(result.quantity, 1e-4, places=9)

    def test_galileo_to_meter_per_second_squared_string(self):
        result = units.galileo(1).to(units.meter_per_second_squared)
        self.assertAlmostEqual(result.quantity, 0.01, places=5)

    def test_kayser_to_reciprocal_meter_string(self):
        result = units.kayser(1).to(units.reciprocal_meter)
        self.assertAlmostEqual(result.quantity, 100, places=2)

    def test_langley_to_joule_per_square_meter_string(self):
        result = units.langley(1).to(units.joule_per_square_meter)
        self.assertAlmostEqual(result.quantity, 41840, places=0)

    def test_reyn_to_pascal_second_string(self):
        result = units.reyn(1).to(units.pascal_second)
        self.assertAlmostEqual(result.quantity, 6894.757, places=2)


class TestUnitProductAsUnit(unittest.TestCase):
    """UnitProduct.as_unit() extraction."""

    def test_trivial_product_returns_unit(self):
        from ucon.core import UnitProduct
        prod = UnitProduct.from_unit(units.meter)
        self.assertEqual(prod.as_unit(), units.meter)

    def test_scaled_product_returns_none(self):
        from ucon.core import UnitProduct, UnitFactor, Scale
        prod = UnitProduct({UnitFactor(units.meter, Scale.kilo): 1})
        self.assertIsNone(prod.as_unit())

    def test_multi_factor_product_returns_none(self):
        from ucon.core import UnitProduct, UnitFactor, Scale
        prod = UnitProduct({
            UnitFactor(units.meter, Scale.one): 1,
            UnitFactor(units.second, Scale.one): -1,
        })
        self.assertIsNone(prod.as_unit())

    def test_exponent_product_returns_none(self):
        from ucon.core import UnitProduct, UnitFactor, Scale
        prod = UnitProduct({UnitFactor(units.meter, Scale.one): 2})
        self.assertIsNone(prod.as_unit())


class TestCGSEMUDimensionIsolation(unittest.TestCase):
    """CGS-EMU dimensions are distinct from SI, CGS, and ESU counterparts."""

    def test_emu_units_have_cgs_emu_basis(self):
        for unit in (
            units.biot, units.abcoulomb, units.abvolt,
            units.abohm, units.abfarad, units.abhenry,
        ):
            self.assertEqual(
                unit.dimension.basis, CGS_EMU,
                f"{unit.name} should have CGS-EMU basis, got {unit.dimension.basis.name}",
            )

    def test_emu_dimensions_have_4_components(self):
        for dim in (
            CGS_EMU_CURRENT, CGS_EMU_CHARGE, CGS_EMU_VOLTAGE,
            CGS_EMU_RESISTANCE, CGS_EMU_CAPACITANCE, CGS_EMU_INDUCTANCE,
        ):
            self.assertEqual(
                len(dim.vector.components), 4,
                f"{dim.name} should have 4-component vector",
            )

    def test_emu_dimensions_use_phi_component(self):
        """EMU EM dimensions should have non-zero Φ component."""
        for dim in (
            CGS_EMU_CURRENT, CGS_EMU_CHARGE, CGS_EMU_VOLTAGE,
            CGS_EMU_RESISTANCE, CGS_EMU_CAPACITANCE, CGS_EMU_INDUCTANCE,
        ):
            self.assertNotEqual(
                dim.vector.components[3], 0,
                f"{dim.name} should use the Φ component (4th), got all-zero",
            )

    def test_emu_current_is_not_si_current(self):
        self.assertNotEqual(units.biot.dimension, CURRENT)

    def test_emu_charge_is_not_si_charge(self):
        self.assertNotEqual(units.abcoulomb.dimension, CHARGE)

    def test_emu_voltage_is_not_si_voltage(self):
        self.assertNotEqual(units.abvolt.dimension, VOLTAGE)

    def test_emu_resistance_is_not_si_resistance(self):
        self.assertNotEqual(units.abohm.dimension, RESISTANCE)

    def test_emu_current_is_not_esu_current(self):
        self.assertNotEqual(CGS_EMU_CURRENT, CGS_ESU_CURRENT)

    def test_emu_charge_is_not_esu_charge(self):
        self.assertNotEqual(CGS_EMU_CHARGE, CGS_ESU_CHARGE)


class TestCGSEMUConversions(unittest.TestCase):
    """Cross-basis CGS-EMU ↔ SI electromagnetic conversions."""

    def setUp(self):
        self.graph = get_default_graph()

    def test_biot_to_ampere(self):
        m = self.graph.convert(src=units.biot, dst=units.ampere)
        self.assertAlmostEqual(m(1), 10, places=5)

    def test_abcoulomb_to_coulomb(self):
        m = self.graph.convert(src=units.abcoulomb, dst=units.coulomb)
        self.assertAlmostEqual(m(1), 10, places=5)

    def test_abvolt_to_volt(self):
        m = self.graph.convert(src=units.abvolt, dst=units.volt)
        self.assertAlmostEqual(m(1), 1e-8, places=13)

    def test_abohm_to_ohm(self):
        m = self.graph.convert(src=units.abohm, dst=units.ohm)
        self.assertAlmostEqual(m(1), 1e-9, places=14)

    def test_abfarad_to_farad(self):
        m = self.graph.convert(src=units.abfarad, dst=units.farad)
        self.assertAlmostEqual(m(1), 1e9, places=0)

    def test_abhenry_to_henry(self):
        m = self.graph.convert(src=units.abhenry, dst=units.henry)
        self.assertAlmostEqual(m(1), 1e-9, places=14)

    def test_biot_roundtrip(self):
        """1 A → Bi → A round-trip preserves value."""
        fwd = self.graph.convert(src=units.ampere, dst=units.biot)
        rev = self.graph.convert(src=units.biot, dst=units.ampere)
        self.assertAlmostEqual(rev(fwd(1)), 1.0, places=10)


class TestESUtoEMUConversions(unittest.TestCase):
    """Direct ESU ↔ EMU conversions via the speed-of-light bridge."""

    c_cgs = 29979245800  # speed of light in cm/s

    def setUp(self):
        self.graph = get_default_graph()

    def test_statcoulomb_to_abcoulomb(self):
        m = self.graph.convert(src=units.statcoulomb, dst=units.abcoulomb)
        expected = 1 / self.c_cgs
        self.assertAlmostEqual(m(1) / expected, 1.0, places=5)

    def test_statampere_to_biot(self):
        m = self.graph.convert(src=units.statampere, dst=units.biot)
        expected = 1 / self.c_cgs
        self.assertAlmostEqual(m(1) / expected, 1.0, places=5)

    def test_statvolt_to_abvolt(self):
        m = self.graph.convert(src=units.statvolt, dst=units.abvolt)
        expected = self.c_cgs
        self.assertAlmostEqual(m(1) / expected, 1.0, places=5)

    def test_statohm_to_abohm(self):
        m = self.graph.convert(src=units.statohm, dst=units.abohm)
        expected = self.c_cgs ** 2
        self.assertAlmostEqual(m(1) / expected, 1.0, places=5)

    def test_statfarad_to_abfarad(self):
        m = self.graph.convert(src=units.statfarad, dst=units.abfarad)
        expected = 1 / self.c_cgs ** 2
        self.assertAlmostEqual(m(1) / expected, 1.0, places=5)


class TestESUEMURoundtrip(unittest.TestCase):
    """SI → ESU → EMU → SI round-trips preserve values."""

    def setUp(self):
        self.graph = get_default_graph()

    def test_ampere_via_statampere_and_biot(self):
        """1 A → statA → Bi → A round-trip."""
        a_to_stat = self.graph.convert(src=units.ampere, dst=units.statampere)
        stat_to_bi = self.graph.convert(src=units.statampere, dst=units.biot)
        bi_to_a = self.graph.convert(src=units.biot, dst=units.ampere)
        result = bi_to_a(stat_to_bi(a_to_stat(1)))
        self.assertAlmostEqual(result, 1.0, places=5)

    def test_volt_via_statvolt_and_abvolt(self):
        """1 V → statV → abV → V round-trip."""
        v_to_stat = self.graph.convert(src=units.volt, dst=units.statvolt)
        stat_to_ab = self.graph.convert(src=units.statvolt, dst=units.abvolt)
        ab_to_v = self.graph.convert(src=units.abvolt, dst=units.volt)
        result = ab_to_v(stat_to_ab(v_to_stat(1)))
        self.assertAlmostEqual(result, 1.0, places=5)


class TestPlanckDimensionIsolation(unittest.TestCase):
    """Planck dimensions are distinct from SI counterparts."""

    def test_planck_energy_is_not_si_energy(self):
        self.assertNotEqual(PLANCK_ENERGY, ENERGY)

    def test_planck_energy_has_planck_basis(self):
        self.assertEqual(PLANCK_ENERGY.basis, PLANCK)

    def test_planck_basis_has_one_component(self):
        self.assertEqual(len(PLANCK_ENERGY.vector.components), 1)

    def test_planck_units_have_planck_basis(self):
        for unit in (
            units.planck_energy, units.planck_mass, units.planck_temperature,
        ):
            self.assertEqual(
                unit.dimension.basis, PLANCK,
                f"{unit.name} should have PLANCK basis, got {unit.dimension.basis.name}",
            )
            self.assertEqual(unit.dimension, PLANCK_ENERGY)

    def test_planck_length_units_have_planck_basis(self):
        for unit in (units.planck_length, units.planck_time):
            self.assertEqual(
                unit.dimension.basis, PLANCK,
                f"{unit.name} should have PLANCK basis, got {unit.dimension.basis.name}",
            )
            self.assertEqual(unit.dimension, PLANCK_LENGTH)


class TestPlanckConversions(unittest.TestCase):
    """Cross-basis Planck ↔ SI conversions."""

    def setUp(self):
        self.graph = get_default_graph()

    def test_planck_energy_to_joule(self):
        m = self.graph.convert(src=units.planck_energy, dst=units.joule)
        self.assertAlmostEqual(m(1) / 1.9561e9, 1.0, places=3)

    def test_planck_mass_to_kilogram(self):
        m = self.graph.convert(src=units.planck_mass, dst=units.kilogram)
        self.assertAlmostEqual(m(1) / 2.17643e-8, 1.0, places=3)

    def test_planck_length_to_meter(self):
        m = self.graph.convert(src=units.planck_length, dst=units.meter)
        self.assertAlmostEqual(m(1) / 1.61626e-35, 1.0, places=3)

    def test_planck_time_to_second(self):
        m = self.graph.convert(src=units.planck_time, dst=units.second)
        self.assertAlmostEqual(m(1) / 5.39124e-44, 1.0, places=3)

    def test_planck_temperature_to_kelvin(self):
        m = self.graph.convert(src=units.planck_temperature, dst=units.kelvin)
        self.assertAlmostEqual(m(1) / 1.41678e32, 1.0, places=3)

    def test_planck_energy_roundtrip(self):
        """1 J → E_P → J round-trip preserves value."""
        fwd = self.graph.convert(src=units.joule, dst=units.planck_energy)
        rev = self.graph.convert(src=units.planck_energy, dst=units.joule)
        self.assertAlmostEqual(rev(fwd(1)), 1.0, places=5)


class TestAtomicDimensionIsolation(unittest.TestCase):
    """Atomic dimensions are distinct from SI counterparts."""

    def test_atomic_energy_is_not_si_energy(self):
        self.assertNotEqual(ATOMIC_ENERGY, ENERGY)

    def test_atomic_energy_has_atomic_basis(self):
        self.assertEqual(ATOMIC_ENERGY.basis, ATOMIC)

    def test_atomic_basis_has_one_component(self):
        self.assertEqual(len(ATOMIC_ENERGY.vector.components), 1)

    def test_hartree_has_atomic_energy_dimension(self):
        self.assertEqual(units.hartree.dimension, ATOMIC_ENERGY)

    def test_bohr_radius_has_atomic_length_dimension(self):
        self.assertEqual(units.bohr_radius.dimension, ATOMIC_LENGTH)

    def test_electron_mass_has_atomic_energy_dimension(self):
        self.assertEqual(units.electron_mass.dimension, ATOMIC_ENERGY)

    def test_atomic_time_has_atomic_length_dimension(self):
        self.assertEqual(units.atomic_time.dimension, ATOMIC_LENGTH)


class TestAtomicConversions(unittest.TestCase):
    """Cross-basis Atomic ↔ SI conversions."""

    def setUp(self):
        self.graph = get_default_graph()

    def test_hartree_to_joule(self):
        m = self.graph.convert(src=units.hartree, dst=units.joule)
        self.assertAlmostEqual(m(1), 4.3597447222071e-18, places=30)

    def test_rydberg_to_joule(self):
        m = self.graph.convert(src=units.rydberg, dst=units.joule)
        self.assertAlmostEqual(m(1), 2.1798723611035e-18, places=30)

    def test_bohr_radius_to_meter(self):
        m = self.graph.convert(src=units.bohr_radius, dst=units.meter)
        self.assertAlmostEqual(m(1) / 5.29177210903e-11, 1.0, places=5)

    def test_atomic_time_to_second(self):
        m = self.graph.convert(src=units.atomic_time, dst=units.second)
        self.assertAlmostEqual(m(1) / 2.4188843265857e-17, 1.0, places=5)

    def test_electron_mass_to_kilogram(self):
        m = self.graph.convert(src=units.electron_mass, dst=units.kilogram)
        self.assertAlmostEqual(m(1) / 9.1093837015e-31, 1.0, places=5)

    def test_hartree_rydberg_ratio(self):
        """1 Eh = 2 Ry by definition."""
        eh_to_j = self.graph.convert(src=units.hartree, dst=units.joule)
        ry_to_j = self.graph.convert(src=units.rydberg, dst=units.joule)
        self.assertAlmostEqual(eh_to_j(1) / ry_to_j(1), 2.0, places=10)


class TestInterBasisIsomorphisms(unittest.TestCase):
    """Cross-basis isomorphism conversions between Natural, Planck, and Atomic."""

    def setUp(self):
        self.graph = get_default_graph()

    def test_ev_to_planck_energy(self):
        """Natural → Planck: eV → E_P."""
        m = self.graph.convert(src=units.electron_volt, dst=units.planck_energy)
        expected = 1 / 1.22089e28
        self.assertAlmostEqual(m(1) / expected, 1.0, places=3)

    def test_planck_energy_to_ev(self):
        """Planck → Natural: E_P → eV."""
        m = self.graph.convert(src=units.planck_energy, dst=units.electron_volt)
        self.assertAlmostEqual(m(1) / 1.22089e28, 1.0, places=3)

    def test_ev_to_hartree(self):
        """Natural → Atomic: eV → Eh."""
        m = self.graph.convert(src=units.electron_volt, dst=units.hartree)
        expected = 1 / 27.211386245988
        self.assertAlmostEqual(m(1), expected, places=8)

    def test_hartree_to_ev(self):
        """Atomic → Natural: Eh → eV."""
        m = self.graph.convert(src=units.hartree, dst=units.electron_volt)
        self.assertAlmostEqual(m(1), 27.211386245988, places=4)

    def test_planck_energy_to_hartree(self):
        """Planck → Atomic: E_P → Eh."""
        m = self.graph.convert(src=units.planck_energy, dst=units.hartree)
        expected = 1.9561e9 / 4.3597447222071e-18  # E_P / Eh ≈ 4.4867e26
        self.assertAlmostEqual(m(1) / expected, 1.0, places=3)

    def test_full_roundtrip_joule_planck_ev_hartree_joule(self):
        """Full round-trip: J → E_P → eV → Eh → J → 1.0.

        Inter-basis factors are derived from the same SI bridge constants,
        so intermediate values cancel algebraically and the round-trip is
        exact to floating-point precision.
        """
        j_to_ep = self.graph.convert(src=units.joule, dst=units.planck_energy)
        ep_to_ev = self.graph.convert(src=units.planck_energy, dst=units.electron_volt)
        ev_to_eh = self.graph.convert(src=units.electron_volt, dst=units.hartree)
        eh_to_j = self.graph.convert(src=units.hartree, dst=units.joule)
        result = eh_to_j(ev_to_eh(ep_to_ev(j_to_ep(1))))
        self.assertAlmostEqual(result, 1.0, places=10)


if __name__ == '__main__':
    unittest.main()
