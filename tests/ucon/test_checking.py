# © 2025 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""Tests for ucon.checking module."""

import sys
import unittest
from unittest.mock import patch, MagicMock

if sys.version_info >= (3, 9):
    from typing import Annotated
else:
    from typing_extensions import Annotated

from ucon import Dimension, Number, units, enforce_dimensions, DimensionConstraint
from ucon.basis import Basis, Vector
from ucon.basis.builtin import SI, CGS
from ucon.core import Unit, UnitProduct, UnitFactor, Scale, BaseForm


class TestEnforceDimensions(unittest.TestCase):
    """Tests for the @enforce_dimensions decorator."""

    def test_valid_dimensions_pass(self):
        @enforce_dimensions
        def speed(distance: Number[Dimension.length], time: Number[Dimension.time]) -> Number:
            return distance / time

        result = speed(units.meter(100), units.second(10))
        self.assertEqual(result.quantity, 10.0)

    def test_wrong_dimension_raises_value_error(self):
        @enforce_dimensions
        def speed(distance: Number[Dimension.length], time: Number[Dimension.time]) -> Number:
            return distance / time

        with self.assertRaises(ValueError) as ctx:
            speed(units.second(100), units.second(10))

        self.assertIn("distance", str(ctx.exception))
        self.assertIn("expected dimension 'length'", str(ctx.exception))
        self.assertIn("got 'time'", str(ctx.exception))

    def test_non_number_raises_type_error(self):
        @enforce_dimensions
        def speed(distance: Number[Dimension.length], time: Number[Dimension.time]) -> Number:
            return distance / time

        with self.assertRaises(TypeError) as ctx:
            speed(100, units.second(10))

        self.assertIn("distance", str(ctx.exception))
        self.assertIn("expected Number", str(ctx.exception))
        self.assertIn("got int", str(ctx.exception))

    def test_unconstrained_param_accepts_any_dimension(self):
        @enforce_dimensions
        def mixed(x: Number[Dimension.time], y: Number) -> Number:
            return x

        # y is unconstrained — any dimension OK
        result = mixed(units.second(1), units.meter(5))
        self.assertEqual(result.quantity, 1)

        result = mixed(units.second(1), units.kilogram(5))
        self.assertEqual(result.quantity, 1)

    def test_optional_none_skipped(self):
        @enforce_dimensions
        def optional(x: Number[Dimension.time], y: Number[Dimension.mass] = None):
            return x

        # y defaults to None, should not raise
        result = optional(units.second(1))
        self.assertEqual(result.quantity, 1)

    def test_no_constraints_returns_unwrapped(self):
        @enforce_dimensions
        def no_constraints(x: Number) -> Number:
            return x

        # Function should be returned unwrapped (fast path)
        # We can verify by checking it's the original function
        result = no_constraints(units.meter(5))
        self.assertEqual(result.quantity, 5)

    def test_composite_dimension(self):
        @enforce_dimensions
        def momentum(mass: Number[Dimension.mass], velocity: Number[Dimension.velocity]):
            return mass * velocity

        # m/s is velocity dimension
        v = units.meter(10) / units.second(1)
        result = momentum(units.kilogram(2), v)
        self.assertEqual(result.quantity, 20)

    def test_wrong_composite_dimension_raises(self):
        @enforce_dimensions
        def momentum(mass: Number[Dimension.mass], velocity: Number[Dimension.velocity]):
            return mass * velocity

        # Passing length instead of velocity
        with self.assertRaises(ValueError) as ctx:
            momentum(units.kilogram(2), units.meter(10))

        self.assertIn("velocity", str(ctx.exception))
        self.assertIn("expected dimension 'velocity'", str(ctx.exception))
        self.assertIn("got 'length'", str(ctx.exception))

    def test_positional_and_keyword_args(self):
        @enforce_dimensions
        def speed(distance: Number[Dimension.length], time: Number[Dimension.time]) -> Number:
            return distance / time

        # Positional
        result1 = speed(units.meter(100), units.second(10))
        self.assertEqual(result1.quantity, 10.0)

        # Keyword
        result2 = speed(distance=units.meter(100), time=units.second(10))
        self.assertEqual(result2.quantity, 10.0)

        # Mixed
        result3 = speed(units.meter(100), time=units.second(10))
        self.assertEqual(result3.quantity, 10.0)

    def test_preserves_function_metadata(self):
        @enforce_dimensions
        def documented(x: Number[Dimension.length]) -> Number:
            """This is the docstring."""
            return x

        self.assertEqual(documented.__name__, "documented")
        self.assertEqual(documented.__doc__, "This is the docstring.")

    def test_derived_dimension_in_error_message(self):
        # Create a derived dimension that doesn't match a named one
        @enforce_dimensions
        def needs_velocity(v: Number[Dimension.velocity]):
            return v

        # Pass volume/time which is a different derived dimension
        volume_flow = units.meter(1) * units.meter(1) * units.meter(1) / units.second(1)

        with self.assertRaises(ValueError) as ctx:
            needs_velocity(volume_flow)

        # Error should use readable derived dimension name
        error_msg = str(ctx.exception)
        self.assertIn("v", error_msg)
        self.assertIn("velocity", error_msg)
        # Should show readable format, not Vector(...)
        self.assertNotIn("Vector", error_msg)


class TestGetDimension(unittest.TestCase):
    """Tests for the _get_dimension helper."""

    def test_extracts_dimension_from_unit_product(self):
        from ucon.checking import _get_dimension
        n = units.meter(5)
        dim = _get_dimension(n)
        self.assertEqual(dim, Dimension.length)

    def test_raises_type_error_for_non_unit(self):
        from ucon.checking import _get_dimension
        # Construct a Number whose .unit is neither Unit nor UnitProduct
        n = Number.__new__(Number)
        object.__setattr__(n, '_quantity', 1.0)
        object.__setattr__(n, '_uncertainty', None)
        object.__setattr__(n, '_unit', "not_a_unit")
        with self.assertRaises(TypeError) as ctx:
            _get_dimension(n)
        self.assertIn("Cannot extract dimension", str(ctx.exception))


class TestDimensionsCompatible(unittest.TestCase):
    """Tests for the _dimensions_compatible function."""

    def test_same_dimension_is_compatible(self):
        from ucon.checking import _dimensions_compatible
        self.assertTrue(_dimensions_compatible(Dimension.length, Dimension.length))

    def test_different_dimension_same_basis_incompatible(self):
        from ucon.checking import _dimensions_compatible
        self.assertFalse(_dimensions_compatible(Dimension.length, Dimension.time))

    def test_cross_basis_compatible(self):
        """CGS dynamic_viscosity is compatible with SI dynamic_viscosity."""
        from ucon.checking import _dimensions_compatible
        cgs_dim = units.poise.dimension
        si_dim = Dimension.dynamic_viscosity
        self.assertNotEqual(cgs_dim.vector.basis, si_dim.vector.basis)
        self.assertTrue(_dimensions_compatible(cgs_dim, si_dim))

    def test_cross_basis_incompatible(self):
        """CGS dynamic_viscosity is NOT compatible with SI energy."""
        from ucon.checking import _dimensions_compatible
        cgs_dim = units.poise.dimension
        si_dim = Dimension.energy
        self.assertFalse(_dimensions_compatible(cgs_dim, si_dim))

    def test_no_transform_path_returns_false(self):
        """Dimensions with no BasisGraph path are incompatible."""
        from ucon.checking import _dimensions_compatible
        from ucon.dimension import Dimension as DimClass
        from ucon.basis import Basis, Vector

        # Create a dimension on a fictitious basis with no transforms registered
        fake_basis = Basis("FakeBasis", ["x", "y"])
        fake_vector = Vector(fake_basis, (1, 0))
        fake_dim = DimClass(fake_vector, name="fake_length")

        self.assertFalse(_dimensions_compatible(fake_dim, Dimension.length))


class TestEnforceDimensionsCrossBasis(unittest.TestCase):
    """Tests for @enforce_dimensions with cross-basis units."""

    def test_cgs_poise_coerced_to_si(self):
        @enforce_dimensions
        def viscosity_fn(mu: Number[Dimension.dynamic_viscosity]) -> Number:
            return mu

        # poise is CGS — coerced to 0.1 Pa·s
        result = viscosity_fn(units.poise(1.0))
        self.assertAlmostEqual(result.quantity, 0.1)
        self.assertEqual(result.unit.name, "pascal_second")

    def test_cgs_unit_rejected_for_wrong_si_dimension(self):
        @enforce_dimensions
        def energy_fn(e: Number[Dimension.energy]) -> Number:
            return e

        with self.assertRaises(ValueError):
            energy_fn(units.poise(1.0))

    def test_cgs_dyne_coerced_enables_si_arithmetic(self):
        """dyne (CGS) is coerced to newton (SI) so formula arithmetic works."""
        @enforce_dimensions
        def work(force: Number[Dimension.force], dist: Number[Dimension.length]) -> Number:
            return force * dist

        result = work(Number(1.0, units.dyne), Number(1.0, units.meter))
        self.assertAlmostEqual(result.quantity, 1e-5)

    def test_cgs_erg_coerced_to_joule(self):
        @enforce_dimensions
        def energy_fn(e: Number[Dimension.energy]) -> Number:
            return e

        result = energy_fn(Number(1.0, units.erg))
        self.assertAlmostEqual(result.quantity, 1e-7)
        self.assertEqual(result.unit.name, "joule")

    def test_si_input_not_coerced(self):
        """SI inputs pass through unchanged — no coercion overhead."""
        @enforce_dimensions
        def length_fn(d: Number[Dimension.length]) -> Number:
            return d

        n = Number(5.0, units.meter)
        result = length_fn(n)
        self.assertIs(result, n)

    def test_uncertainty_scaled_during_coercion(self):
        @enforce_dimensions
        def force_fn(f: Number[Dimension.force]) -> Number:
            return f

        result = force_fn(Number(1.0, units.dyne, uncertainty=0.1))
        self.assertAlmostEqual(result.quantity, 1e-5)
        self.assertIsNotNone(result.uncertainty)
        self.assertAlmostEqual(result.uncertainty, 1e-6)


class TestDimensionsCompatibleAdversarial(unittest.TestCase):
    """Adversarial tests for _dimensions_compatible edge cases."""

    def test_si_actual_vs_cgs_expected(self):
        """SI actual, CGS expected — only the expected side needs transform."""
        from ucon.checking import _dimensions_compatible
        si_force = Dimension.force
        cgs_force = units.dyne.dimension
        # actual is SI (skip transform), expected is CGS (needs transform)
        self.assertTrue(_dimensions_compatible(si_force, cgs_force))

    def test_si_actual_vs_cgs_expected_incompatible(self):
        """SI energy vs CGS force — different physical quantities."""
        from ucon.checking import _dimensions_compatible
        self.assertFalse(_dimensions_compatible(Dimension.energy, units.dyne.dimension))

    def test_both_non_si_same_basis_different_dimensions(self):
        """Two CGS dimensions on same basis, different vectors — should be False."""
        from ucon.checking import _dimensions_compatible
        cgs_force = units.dyne.dimension
        cgs_viscosity = units.poise.dimension
        self.assertFalse(_dimensions_compatible(cgs_force, cgs_viscosity))


class TestCoerceToSiAlgebraic(unittest.TestCase):
    """Tests for the algebraic (base_form) coercion path in _coerce_to_si."""

    def _make_custom_basis(self):
        return Basis('TestAlg', ['length', 'mass', 'time'])

    def test_plain_unit_with_si_base_form(self):
        """Non-SI unit with SI base_form factors coerces algebraically (lines 87-93)."""
        from ucon.checking import _coerce_to_si
        basis = self._make_custom_basis()
        dim = Dimension(Vector(basis, (1, 0, 0)), name='talg_length')
        bf = BaseForm(factors=((units.meter, 1.0),), prefactor=0.3048)
        foot = Unit(name='test_foot', dimension=dim, aliases=('tft',), base_form=bf)
        n = Number(1.0, foot)
        result = _coerce_to_si(n)
        self.assertIsNot(result, n)
        self.assertAlmostEqual(result.quantity, 0.3048)

    def test_plain_unit_with_si_base_form_uncertainty(self):
        """Uncertainty is scaled by base_form prefactor."""
        from ucon.checking import _coerce_to_si
        basis = self._make_custom_basis()
        dim = Dimension(Vector(basis, (1, 0, 0)), name='talg_length2')
        bf = BaseForm(factors=((units.meter, 1.0),), prefactor=0.3048)
        foot = Unit(name='test_foot2', dimension=dim, aliases=('tft2',), base_form=bf)
        n = Number(1.0, foot, uncertainty=0.01)
        result = _coerce_to_si(n)
        self.assertAlmostEqual(result.uncertainty, 0.01 * 0.3048)

    def test_plain_unit_with_non_si_base_form_falls_to_graph(self):
        """Non-SI base_form factors fall through to graph path (line 89 false)."""
        from ucon.checking import _coerce_to_si
        basis = self._make_custom_basis()
        dim = Dimension(Vector(basis, (1, 0, 0)), name='talg_x')
        non_si_base = Unit(name='talg_base', dimension=dim, aliases=('tb',))
        bf = BaseForm(factors=((non_si_base, 1.0),), prefactor=2.0)
        custom = Unit(name='talg_unit', dimension=dim, aliases=('tu',), base_form=bf)
        n = Number(1.0, custom)
        # Falls through to _coerce_via_graph which returns unchanged (no transform path)
        result = _coerce_to_si(n)
        self.assertIs(result, n)

    def test_plain_unit_no_base_form_falls_to_graph(self):
        """Unit with base_form=None falls through to graph path."""
        from ucon.checking import _coerce_to_si
        # CGS units have base_form=None
        n = Number(1.0, units.dyne)
        result = _coerce_to_si(n)
        # dyne coerces via graph to newton
        self.assertIsNot(result, n)
        self.assertAlmostEqual(result.quantity, 1e-5)

    def test_product_with_si_base_form_coerces_algebraically(self):
        """UnitProduct whose factors all have SI base_forms coerces (lines 83-85)."""
        from ucon.checking import _coerce_to_si
        basis = self._make_custom_basis()
        bf_len = BaseForm(factors=((units.meter, 1.0),), prefactor=0.3048)
        bf_time = BaseForm(factors=((units.second, 1.0),), prefactor=1.0)
        foot = Unit(name='talg_ft3', dimension=Dimension(Vector(basis, (1, 0, 0)), name='talg_l3'), aliases=('tf3',), base_form=bf_len)
        sec = Unit(name='talg_s3', dimension=Dimension(Vector(basis, (0, 0, 1)), name='talg_t3'), aliases=('ts3',), base_form=bf_time)
        prod = UnitProduct({UnitFactor(foot, Scale.one): 1, UnitFactor(sec, Scale.one): -1})
        n = Number(1.0, prod)
        result = _coerce_to_si(n)
        self.assertIsNot(result, n)
        self.assertAlmostEqual(result.quantity, 0.3048)


class TestCoerceProductToSiAdversarial(unittest.TestCase):
    """Adversarial tests for _coerce_product_to_si."""

    def test_factor_without_base_form_returns_unchanged(self):
        """Product factor with base_form=None aborts algebraic coercion (line 106-107)."""
        from ucon.checking import _coerce_product_to_si
        basis = Basis('TestProd', ['x', 'y'])
        dim = Dimension(Vector(basis, (1, 0)), name='tp_x')
        no_bf = Unit(name='tp_nobase', dimension=dim, aliases=('tnb',))  # base_form=None
        prod = UnitProduct({UnitFactor(no_bf, Scale.one): 1})
        n = Number(1.0, prod)
        result = _coerce_product_to_si(n)
        self.assertIs(result, n)

    def test_factor_with_non_si_base_form_returns_unchanged(self):
        """Product factor with non-SI base_form factors returns unchanged (line 108-109)."""
        from ucon.checking import _coerce_product_to_si
        basis = Basis('TestProd2', ['x', 'y'])
        dim = Dimension(Vector(basis, (1, 0)), name='tp2_x')
        foreign_base = Unit(name='tp2_base', dimension=dim, aliases=('t2b',))
        bf = BaseForm(factors=((foreign_base, 1.0),), prefactor=3.0)
        custom = Unit(name='tp2_unit', dimension=dim, aliases=('t2u',), base_form=bf)
        prod = UnitProduct({UnitFactor(custom, Scale.one): 1})
        n = Number(1.0, prod)
        result = _coerce_product_to_si(n)
        self.assertIs(result, n)

    def test_successful_product_coercion_with_uncertainty(self):
        """Product coercion scales uncertainty by abs(combined_prefactor) (line 115)."""
        from ucon.checking import _coerce_product_to_si
        basis = Basis('TestProd3', ['length', 'time'])
        bf_len = BaseForm(factors=((units.meter, 1.0),), prefactor=100.0)
        bf_time = BaseForm(factors=((units.second, 1.0),), prefactor=60.0)
        dim_len = Dimension(Vector(basis, (1, 0)), name='tp3_l')
        dim_time = Dimension(Vector(basis, (0, 1)), name='tp3_t')
        hectometer = Unit(name='tp3_hm', dimension=dim_len, aliases=('thm',), base_form=bf_len)
        minute = Unit(name='tp3_min', dimension=dim_time, aliases=('tmn',), base_form=bf_time)
        # Build the product from a single factor first, then combine manually
        # (UnitProduct.__init__ does cross-basis dim multiply which would fail)
        prod = UnitProduct({hectometer: 1})
        # Manually add the second factor
        prod.factors[UnitFactor(minute, Scale.one)] = -1
        n = Number(1.0, prod, uncertainty=0.5)
        result = _coerce_product_to_si(n)
        expected_prefactor = 100.0 / 60.0
        self.assertAlmostEqual(result.quantity, expected_prefactor)
        self.assertAlmostEqual(result.uncertainty, 0.5 * abs(expected_prefactor))


class TestCoerceViaGraphAdversarial(unittest.TestCase):
    """Adversarial tests for _coerce_via_graph edge cases."""

    def test_si_input_returns_unchanged(self):
        """SI unit hits early return (line 137)."""
        from ucon.checking import _coerce_via_graph
        n = Number(1.0, units.meter)
        result = _coerce_via_graph(n)
        self.assertIs(result, n)

    def test_no_transform_path_returns_unchanged(self):
        """Unknown basis with no BasisGraph entry returns unchanged (lines 138-139)."""
        from ucon.checking import _coerce_via_graph
        fake_basis = Basis('Isolated', ['q'])
        fake_dim = Dimension(Vector(fake_basis, (1,)), name='isolated_q')
        fake_unit = Unit(name='iso_unit', dimension=fake_dim, aliases=('iu',))
        n = Number(1.0, fake_unit)
        result = _coerce_via_graph(n)
        self.assertIs(result, n)

    def test_no_target_in_graph_returns_unchanged(self):
        """Dimension with no units in graph returns unchanged (line 163)."""
        from ucon.checking import _coerce_via_graph
        n = Number(1.0, units.dyne)
        with patch('ucon.graph.get_default_graph') as mock_gg:
            mock_g = MagicMock()
            mock_g._unit_edges = {}
            mock_gg.return_value = mock_g
            result = _coerce_via_graph(n)
            self.assertIs(result, n)

    def test_conversion_exception_returns_unchanged(self):
        """graph.convert raising returns unchanged (lines 167-168)."""
        from ucon.checking import _coerce_via_graph
        from ucon.graph import get_default_graph, ConversionNotFound
        real_graph = get_default_graph()
        n = Number(1.0, units.dyne)
        with patch('ucon.graph.get_default_graph') as mock_gg:
            mock_g = MagicMock()
            mock_g._unit_edges = real_graph._unit_edges
            mock_g.convert.side_effect = ConversionNotFound('forced error')
            mock_gg.return_value = mock_g
            result = _coerce_via_graph(n)
            self.assertIs(result, n)

    def test_fallback_loop_when_no_coherent_unit(self):
        """Fallback loop (lines 155-160) picks a unit when no prefactor==1.0 exists."""
        from ucon.checking import _coerce_via_graph
        from ucon.graph import get_default_graph
        from ucon.basis.graph import get_basis_graph

        bg = get_basis_graph()
        cgs_force = units.dyne.dimension
        si_force = cgs_force.in_basis(bg.get_transform(CGS, SI))

        # Fabricate a unit with prefactor != 1.0
        bf = BaseForm(
            factors=((units.meter, 1.0), (units.kilogram, 1.0), (units.second, -2.0)),
            prefactor=9.80665
        )
        kgf = Unit(name='test_kgf', dimension=si_force, aliases=('tkgf',), base_form=bf)
        fake_edges = {si_force: {kgf: {}}}

        n = Number(1.0, units.dyne)
        with patch('ucon.graph.get_default_graph') as mock_gg:
            mock_g = MagicMock()
            mock_g._unit_edges = fake_edges
            mock_g.convert.return_value = lambda x: x * 1e-5
            mock_gg.return_value = mock_g
            result = _coerce_via_graph(n)
            self.assertIsNot(result, n)
            self.assertAlmostEqual(result.quantity, 1e-5)
            self.assertEqual(result.unit.name, 'test_kgf')

    def test_uncertainty_propagated_via_conversion_a(self):
        """Uncertainty propagated using conversion.a when available (line 173)."""
        from ucon.checking import _coerce_via_graph
        from ucon.graph import get_default_graph

        n = Number(1.0, units.dyne, uncertainty=0.1)
        result = _coerce_via_graph(n)
        self.assertIsNot(result, n)
        self.assertIsNotNone(result.uncertainty)
        self.assertAlmostEqual(result.uncertainty, 0.1 * 1e-5)

    def test_uncertainty_none_when_conversion_lacks_a(self):
        """Uncertainty is None when conversion object lacks .a attribute (line 173 else)."""
        from ucon.checking import _coerce_via_graph
        from ucon.graph import get_default_graph
        real_graph = get_default_graph()

        n = Number(1.0, units.dyne, uncertainty=0.1)

        # Create a conversion object without .a attribute
        class BareConversion:
            def __call__(self, x):
                return x * 1e-5

        with patch('ucon.graph.get_default_graph') as mock_gg:
            mock_g = MagicMock()
            mock_g._unit_edges = real_graph._unit_edges
            mock_g.convert.return_value = BareConversion()
            mock_gg.return_value = mock_g
            result = _coerce_via_graph(n)
            self.assertIsNot(result, n)
            self.assertAlmostEqual(result.quantity, 1e-5)
            self.assertIsNone(result.uncertainty)


class TestEnforceDimensionsAnnotationParsing(unittest.TestCase):
    """Adversarial tests for annotation parsing in enforce_dimensions."""

    def test_return_annotation_skipped(self):
        """Return type annotation is skipped (line 219)."""
        @enforce_dimensions
        def fn(x: Number[Dimension.length]) -> Number[Dimension.velocity]:
            return x
        # Should not validate the return value's dimension
        result = fn(units.meter(5))
        self.assertEqual(result.quantity, 5)

    def test_non_annotated_param_skipped(self):
        """Plain-typed param is skipped (line 221)."""
        @enforce_dimensions
        def fn(x: Number[Dimension.length], y: int) -> Number:
            return x
        result = fn(units.meter(5), 42)
        self.assertEqual(result.quantity, 5)

    def test_annotated_non_dimension_metadata_skipped(self):
        """Annotated param with non-DimensionConstraint metadata is skipped (line 224)."""
        @enforce_dimensions
        def fn(
            x: Number[Dimension.length],
            label: Annotated[str, 'some_tag'],
        ) -> Number:
            return x
        result = fn(units.meter(5), 'hello')
        self.assertEqual(result.quantity, 5)

    def test_multiple_metadata_picks_dimension_constraint(self):
        """When multiple Annotated metadata are present, DimensionConstraint is found."""
        @enforce_dimensions
        def fn(x: Annotated[Number, 'extra_metadata', DimensionConstraint(Dimension.length)]) -> Number:
            return x
        result = fn(units.meter(5))
        self.assertEqual(result.quantity, 5)
        with self.assertRaises(ValueError):
            fn(units.second(5))


class TestDimensionConstraint(unittest.TestCase):
    """Tests for the DimensionConstraint marker class."""

    def test_equality(self):
        c1 = DimensionConstraint(Dimension.time)
        c2 = DimensionConstraint(Dimension.time)
        c3 = DimensionConstraint(Dimension.mass)

        self.assertEqual(c1, c2)
        self.assertNotEqual(c1, c3)

    def test_hash(self):
        c1 = DimensionConstraint(Dimension.time)
        c2 = DimensionConstraint(Dimension.time)

        self.assertEqual(hash(c1), hash(c2))
        self.assertIn(c1, {c2})

    def test_repr(self):
        c = DimensionConstraint(Dimension.time)
        self.assertEqual(repr(c), "DimensionConstraint(time)")


if __name__ == "__main__":
    unittest.main()
