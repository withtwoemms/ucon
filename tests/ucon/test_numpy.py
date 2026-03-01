# tests/ucon/test_numpy.py
#
# Tests for NumberArray and numpy integration.

import unittest
import math

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


@unittest.skipUnless(HAS_NUMPY, "NumPy not installed")
class TestNumberArrayBasic(unittest.TestCase):
    """Test NumberArray construction and basic properties."""

    def setUp(self):
        from ucon import units
        self.meter = units.meter
        self.foot = units.foot
        self.second = units.second

    def test_create_from_list(self):
        from ucon.numpy import NumberArray
        arr = NumberArray([1.0, 2.0, 3.0], unit=self.meter)
        self.assertEqual(len(arr), 3)
        self.assertEqual(arr.shape, (3,))
        self.assertEqual(arr.unit, self.meter)

    def test_create_from_ndarray(self):
        from ucon.numpy import NumberArray
        arr = NumberArray(np.array([1.0, 2.0, 3.0]), unit=self.meter)
        self.assertEqual(len(arr), 3)
        np.testing.assert_array_equal(arr.quantities, np.array([1.0, 2.0, 3.0]))

    def test_default_unit_is_dimensionless(self):
        from ucon.numpy import NumberArray
        from ucon.core import _none
        arr = NumberArray([1.0, 2.0])
        self.assertEqual(arr.unit, _none)

    def test_uniform_uncertainty(self):
        from ucon.numpy import NumberArray
        arr = NumberArray([1.0, 2.0, 3.0], unit=self.meter, uncertainty=0.1)
        self.assertEqual(arr.uncertainty, 0.1)

    def test_per_element_uncertainty(self):
        from ucon.numpy import NumberArray
        unc = [0.1, 0.2, 0.3]
        arr = NumberArray([1.0, 2.0, 3.0], unit=self.meter, uncertainty=unc)
        np.testing.assert_array_equal(arr.uncertainty, np.array(unc))

    def test_uncertainty_shape_mismatch_raises(self):
        from ucon.numpy import NumberArray
        with self.assertRaises(ValueError) as ctx:
            NumberArray([1.0, 2.0, 3.0], unit=self.meter, uncertainty=[0.1, 0.2])
        self.assertIn("shape", str(ctx.exception))

    def test_ndim_property(self):
        from ucon.numpy import NumberArray
        arr = NumberArray([1.0, 2.0, 3.0], unit=self.meter)
        self.assertEqual(arr.ndim, 1)

        arr_2d = NumberArray([[1, 2], [3, 4]], unit=self.meter)
        self.assertEqual(arr_2d.ndim, 2)

    def test_dtype_property(self):
        from ucon.numpy import NumberArray
        arr = NumberArray([1, 2, 3], unit=self.meter)
        self.assertEqual(arr.dtype, np.float64)


@unittest.skipUnless(HAS_NUMPY, "NumPy not installed")
class TestNumberArrayIndexing(unittest.TestCase):
    """Test NumberArray indexing and iteration."""

    def setUp(self):
        from ucon import units
        self.meter = units.meter

    def test_scalar_index_returns_number(self):
        from ucon.numpy import NumberArray
        from ucon.core import Number
        arr = NumberArray([1.0, 2.0, 3.0], unit=self.meter)
        elem = arr[0]
        self.assertIsInstance(elem, Number)
        self.assertEqual(elem.quantity, 1.0)
        self.assertEqual(elem.unit, self.meter)

    def test_slice_returns_numberarray(self):
        from ucon.numpy import NumberArray
        arr = NumberArray([1.0, 2.0, 3.0, 4.0], unit=self.meter)
        sliced = arr[1:3]
        self.assertIsInstance(sliced, NumberArray)
        self.assertEqual(len(sliced), 2)
        np.testing.assert_array_equal(sliced.quantities, np.array([2.0, 3.0]))

    def test_index_with_uncertainty(self):
        from ucon.numpy import NumberArray
        arr = NumberArray([1.0, 2.0], unit=self.meter, uncertainty=0.1)
        elem = arr[0]
        self.assertEqual(elem.uncertainty, 0.1)

    def test_index_with_per_element_uncertainty(self):
        from ucon.numpy import NumberArray
        arr = NumberArray([1.0, 2.0], unit=self.meter, uncertainty=[0.1, 0.2])
        self.assertEqual(arr[0].uncertainty, 0.1)
        self.assertEqual(arr[1].uncertainty, 0.2)

    def test_iteration_yields_numbers(self):
        from ucon.numpy import NumberArray
        from ucon.core import Number
        arr = NumberArray([1.0, 2.0, 3.0], unit=self.meter)
        elements = list(arr)
        self.assertEqual(len(elements), 3)
        for elem in elements:
            self.assertIsInstance(elem, Number)


@unittest.skipUnless(HAS_NUMPY, "NumPy not installed")
class TestNumberArrayArithmetic(unittest.TestCase):
    """Test NumberArray arithmetic operations."""

    def setUp(self):
        from ucon import units
        self.meter = units.meter
        self.second = units.second

    def test_multiply_by_scalar(self):
        from ucon.numpy import NumberArray
        arr = NumberArray([1.0, 2.0, 3.0], unit=self.meter)
        result = arr * 2
        np.testing.assert_array_equal(result.quantities, np.array([2.0, 4.0, 6.0]))
        self.assertEqual(result.unit, self.meter)

    def test_multiply_by_scalar_with_uncertainty(self):
        from ucon.numpy import NumberArray
        arr = NumberArray([1.0, 2.0], unit=self.meter, uncertainty=0.1)
        result = arr * 2
        self.assertEqual(result.uncertainty, 0.2)

    def test_rmul(self):
        from ucon.numpy import NumberArray
        arr = NumberArray([1.0, 2.0, 3.0], unit=self.meter)
        result = 2 * arr
        np.testing.assert_array_equal(result.quantities, np.array([2.0, 4.0, 6.0]))

    def test_divide_by_scalar(self):
        from ucon.numpy import NumberArray
        arr = NumberArray([2.0, 4.0, 6.0], unit=self.meter)
        result = arr / 2
        np.testing.assert_array_equal(result.quantities, np.array([1.0, 2.0, 3.0]))

    def test_multiply_numberarrays(self):
        from ucon.numpy import NumberArray
        a = NumberArray([1.0, 2.0], unit=self.meter)
        b = NumberArray([3.0, 4.0], unit=self.second)
        result = a * b
        np.testing.assert_array_equal(result.quantities, np.array([3.0, 8.0]))
        # Check combined unit
        self.assertIn('m', str(result.unit))
        self.assertIn('s', str(result.unit))

    def test_multiply_numberarrays_shape_mismatch(self):
        from ucon.numpy import NumberArray
        a = NumberArray([1.0, 2.0, 3.0], unit=self.meter)
        b = NumberArray([1.0, 2.0], unit=self.meter)
        with self.assertRaises(ValueError) as ctx:
            a * b
        self.assertIn("Shape mismatch", str(ctx.exception))

    def test_add_same_unit(self):
        from ucon.numpy import NumberArray
        a = NumberArray([1.0, 2.0], unit=self.meter)
        b = NumberArray([0.5, 0.5], unit=self.meter)
        result = a + b
        np.testing.assert_array_equal(result.quantities, np.array([1.5, 2.5]))

    def test_add_different_unit_raises(self):
        from ucon.numpy import NumberArray
        a = NumberArray([1.0, 2.0], unit=self.meter)
        b = NumberArray([1.0, 2.0], unit=self.second)
        with self.assertRaises(ValueError) as ctx:
            a + b
        self.assertIn("different units", str(ctx.exception))

    def test_subtract(self):
        from ucon.numpy import NumberArray
        a = NumberArray([3.0, 4.0], unit=self.meter)
        b = NumberArray([1.0, 1.0], unit=self.meter)
        result = a - b
        np.testing.assert_array_equal(result.quantities, np.array([2.0, 3.0]))

    def test_negation(self):
        from ucon.numpy import NumberArray
        arr = NumberArray([1.0, -2.0, 3.0], unit=self.meter)
        result = -arr
        np.testing.assert_array_equal(result.quantities, np.array([-1.0, 2.0, -3.0]))

    def test_abs(self):
        from ucon.numpy import NumberArray
        arr = NumberArray([-1.0, 2.0, -3.0], unit=self.meter)
        result = abs(arr)
        np.testing.assert_array_equal(result.quantities, np.array([1.0, 2.0, 3.0]))


@unittest.skipUnless(HAS_NUMPY, "NumPy not installed")
class TestNumberArrayConversion(unittest.TestCase):
    """Test NumberArray unit conversion."""

    def setUp(self):
        from ucon import units
        from ucon.core import Scale
        self.meter = units.meter
        self.foot = units.foot
        self.kilometer = Scale.kilo * units.meter
        self.centimeter = Scale.centi * units.meter

    def test_scale_only_conversion(self):
        from ucon.numpy import NumberArray
        arr = NumberArray([1.0, 2.0, 3.0], unit=self.kilometer)
        result = arr.to(self.meter)
        np.testing.assert_array_almost_equal(
            result.quantities, np.array([1000.0, 2000.0, 3000.0])
        )
        self.assertEqual(result.unit, self.meter)

    def test_conversion_with_uncertainty(self):
        from ucon.numpy import NumberArray
        arr = NumberArray([1.0, 2.0], unit=self.kilometer, uncertainty=0.1)
        result = arr.to(self.meter)
        # Uncertainty should scale by same factor
        self.assertAlmostEqual(result.uncertainty, 100.0)

    def test_graph_based_conversion(self):
        from ucon.numpy import NumberArray
        arr = NumberArray([1.0, 2.0, 3.0], unit=self.meter)
        result = arr.to(self.foot)
        # 1 meter ≈ 3.28084 feet
        expected = np.array([1.0, 2.0, 3.0]) * 3.28084
        np.testing.assert_array_almost_equal(result.quantities, expected, decimal=3)


@unittest.skipUnless(HAS_NUMPY, "NumPy not installed")
class TestNumberArrayUncertaintyPropagation(unittest.TestCase):
    """Test uncertainty propagation through arithmetic."""

    def setUp(self):
        from ucon import units
        self.meter = units.meter

    def test_multiplication_uncertainty(self):
        from ucon.numpy import NumberArray
        from ucon.core import Number
        # a = [10, 20] ± 1
        # b = 2 ± 0.1
        # For c = a * b:
        # δc/c = sqrt((δa/a)² + (δb/b)²)
        arr = NumberArray([10.0, 20.0], unit=self.meter, uncertainty=1.0)
        scalar = Number(quantity=2.0, unit=self.meter, uncertainty=0.1)
        result = arr * scalar

        # For first element: c = 20, δc/c = sqrt((1/10)² + (0.1/2)²)
        rel_unc = math.sqrt((1/10)**2 + (0.1/2)**2)
        expected_unc_1 = 20 * rel_unc
        self.assertAlmostEqual(result.uncertainty[0], expected_unc_1, places=5)

    def test_addition_uncertainty_quadrature(self):
        from ucon.numpy import NumberArray
        # δ(a+b) = sqrt(δa² + δb²)
        a = NumberArray([1.0, 2.0], unit=self.meter, uncertainty=0.1)
        b = NumberArray([1.0, 2.0], unit=self.meter, uncertainty=0.2)
        result = a + b
        expected_unc = math.sqrt(0.1**2 + 0.2**2)
        np.testing.assert_array_almost_equal(
            result.uncertainty, np.array([expected_unc, expected_unc])
        )


@unittest.skipUnless(HAS_NUMPY, "NumPy not installed")
class TestCallableSyntax(unittest.TestCase):
    """Test unit callable syntax with arrays."""

    def setUp(self):
        from ucon import units
        self.meter = units.meter
        self.second = units.second

    def test_unit_callable_with_list(self):
        from ucon.numpy import NumberArray
        arr = self.meter([1.0, 2.0, 3.0])
        self.assertIsInstance(arr, NumberArray)
        self.assertEqual(len(arr), 3)
        self.assertEqual(arr.unit, self.meter)

    def test_unit_callable_with_ndarray(self):
        from ucon.numpy import NumberArray
        arr = self.meter(np.array([1.0, 2.0, 3.0]))
        self.assertIsInstance(arr, NumberArray)

    def test_unit_callable_scalar_still_returns_number(self):
        from ucon.core import Number
        n = self.meter(5.0)
        self.assertIsInstance(n, Number)

    def test_unitproduct_callable_with_list(self):
        from ucon.numpy import NumberArray
        velocity_unit = self.meter / self.second
        arr = velocity_unit([10, 20, 30])
        self.assertIsInstance(arr, NumberArray)
        self.assertEqual(len(arr), 3)

    def test_unit_callable_with_uncertainty(self):
        from ucon.numpy import NumberArray
        arr = self.meter([1.0, 2.0, 3.0], uncertainty=0.1)
        self.assertIsInstance(arr, NumberArray)
        self.assertEqual(arr.uncertainty, 0.1)


@unittest.skipUnless(HAS_NUMPY, "NumPy not installed")
class TestMapArraySupport(unittest.TestCase):
    """Test that Maps work with array inputs."""

    def test_linearmap_with_array(self):
        from ucon.maps import LinearMap
        m = LinearMap(2.0)
        arr = np.array([1.0, 2.0, 3.0])
        result = m(arr)
        np.testing.assert_array_equal(result, np.array([2.0, 4.0, 6.0]))

    def test_affinemap_with_array(self):
        from ucon.maps import AffineMap
        m = AffineMap(2.0, 10.0)  # y = 2*x + 10
        arr = np.array([0.0, 5.0, 10.0])
        result = m(arr)
        np.testing.assert_array_equal(result, np.array([10.0, 20.0, 30.0]))

    def test_logmap_with_array(self):
        from ucon.maps import LogMap
        m = LogMap(scale=10, base=10)  # 10 * log10(x) - dB power
        arr = np.array([1.0, 10.0, 100.0])
        result = m(arr)
        np.testing.assert_array_almost_equal(result, np.array([0.0, 10.0, 20.0]))

    def test_expmap_with_array(self):
        from ucon.maps import ExpMap
        m = ExpMap(scale=0.1, base=10)  # 10^(0.1*x) - inverse of dB
        arr = np.array([0.0, 10.0, 20.0])
        result = m(arr)
        np.testing.assert_array_almost_equal(result, np.array([1.0, 10.0, 100.0]))

    def test_linearmap_derivative_with_array(self):
        from ucon.maps import LinearMap
        m = LinearMap(2.0)
        arr = np.array([1.0, 2.0, 3.0])
        deriv = m.derivative(arr)
        # LinearMap derivative is constant
        self.assertEqual(deriv, 2.0)

    def test_logmap_derivative_with_array(self):
        from ucon.maps import LogMap
        m = LogMap(scale=10, base=10)
        arr = np.array([1.0, 10.0, 100.0])
        deriv = m.derivative(arr)
        # d/dx [10 * log10(x)] = 10 / (x * ln(10))
        expected = 10 / (arr * math.log(10))
        np.testing.assert_array_almost_equal(deriv, expected)


@unittest.skipUnless(HAS_NUMPY, "NumPy not installed")
class TestNumberArrayReductions(unittest.TestCase):
    """Test reduction operations (sum, mean, etc.)."""

    def setUp(self):
        from ucon import units
        self.meter = units.meter

    def test_sum(self):
        from ucon.numpy import NumberArray
        from ucon.core import Number
        arr = NumberArray([1.0, 2.0, 3.0, 4.0], unit=self.meter)
        total = arr.sum()
        self.assertIsInstance(total, Number)
        self.assertEqual(total.quantity, 10.0)
        self.assertEqual(total.unit, self.meter)

    def test_sum_with_uncertainty(self):
        from ucon.numpy import NumberArray
        arr = NumberArray([1.0, 2.0, 3.0, 4.0], unit=self.meter, uncertainty=0.1)
        total = arr.sum()
        # σ_sum = σ * sqrt(n) for uniform uncertainty
        self.assertAlmostEqual(total.uncertainty, 0.1 * math.sqrt(4))

    def test_mean(self):
        from ucon.numpy import NumberArray
        from ucon.core import Number
        arr = NumberArray([2.0, 4.0, 6.0], unit=self.meter)
        avg = arr.mean()
        self.assertIsInstance(avg, Number)
        self.assertEqual(avg.quantity, 4.0)

    def test_mean_with_uncertainty(self):
        from ucon.numpy import NumberArray
        arr = NumberArray([1.0, 2.0, 3.0, 4.0], unit=self.meter, uncertainty=0.2)
        avg = arr.mean()
        # σ_mean = σ / sqrt(n) for uniform uncertainty
        self.assertAlmostEqual(avg.uncertainty, 0.2 / math.sqrt(4))

    def test_std(self):
        from ucon.numpy import NumberArray
        arr = NumberArray([2.0, 4.0, 6.0, 8.0], unit=self.meter)
        s = arr.std()
        expected = np.std([2.0, 4.0, 6.0, 8.0])
        self.assertAlmostEqual(s.quantity, expected)

    def test_min_max(self):
        from ucon.numpy import NumberArray
        arr = NumberArray([3.0, 1.0, 4.0, 1.0, 5.0], unit=self.meter)
        self.assertEqual(arr.min().quantity, 1.0)
        self.assertEqual(arr.max().quantity, 5.0)


@unittest.skipUnless(HAS_NUMPY, "NumPy not installed")
class TestNumberArrayRepr(unittest.TestCase):
    """Test string representation."""

    def setUp(self):
        from ucon import units
        self.meter = units.meter

    def test_small_array_repr(self):
        from ucon.numpy import NumberArray
        arr = NumberArray([1.0, 2.0, 3.0], unit=self.meter)
        s = repr(arr)
        self.assertIn("m", s)
        self.assertIn("1", s)
        self.assertIn("3", s)

    def test_large_array_truncation(self):
        from ucon.numpy import NumberArray
        arr = NumberArray(list(range(100)), unit=self.meter)
        s = repr(arr)
        self.assertIn("...", s)

    def test_repr_with_uncertainty(self):
        from ucon.numpy import NumberArray
        arr = NumberArray([1.0, 2.0], unit=self.meter, uncertainty=0.1)
        s = repr(arr)
        self.assertIn("±", s)


if __name__ == "__main__":
    unittest.main()
