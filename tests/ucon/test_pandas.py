# tests/ucon/test_pandas.py
#
# Tests for NumberSeries and pandas integration.

import unittest
import math

try:
    import pandas as pd
    import numpy as np
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


@unittest.skipUnless(HAS_PANDAS, "Pandas not installed")
class TestNumberSeriesBasic(unittest.TestCase):
    """Test NumberSeries construction and basic properties."""

    def setUp(self):
        from ucon import units
        self.meter = units.meter
        self.foot = units.foot
        self.second = units.second

    def test_create_from_series(self):
        from ucon.integrations.pandas import NumberSeries
        s = pd.Series([1.0, 2.0, 3.0])
        ns = NumberSeries(s, unit=self.meter)
        self.assertEqual(len(ns), 3)
        self.assertEqual(ns.unit, self.meter)

    def test_create_from_list(self):
        from ucon.integrations.pandas import NumberSeries
        ns = NumberSeries([1.0, 2.0, 3.0], unit=self.meter)
        self.assertEqual(len(ns), 3)
        self.assertIsInstance(ns.series, pd.Series)

    def test_default_unit_is_dimensionless(self):
        from ucon.integrations.pandas import NumberSeries
        from ucon.quantity import _none
        ns = NumberSeries(pd.Series([1.0, 2.0]))
        self.assertEqual(ns.unit, _none)

    def test_uniform_uncertainty(self):
        from ucon.integrations.pandas import NumberSeries
        ns = NumberSeries(pd.Series([1.0, 2.0, 3.0]), unit=self.meter, uncertainty=0.1)
        self.assertEqual(ns.uncertainty, 0.1)

    def test_per_element_uncertainty(self):
        from ucon.integrations.pandas import NumberSeries
        unc = pd.Series([0.1, 0.2, 0.3])
        ns = NumberSeries(pd.Series([1.0, 2.0, 3.0]), unit=self.meter, uncertainty=unc)
        pd.testing.assert_series_equal(ns.uncertainty, unc)

    def test_uncertainty_length_mismatch_raises(self):
        from ucon.integrations.pandas import NumberSeries
        with self.assertRaises(ValueError) as ctx:
            NumberSeries(pd.Series([1.0, 2.0, 3.0]), unit=self.meter,
                        uncertainty=pd.Series([0.1, 0.2]))
        self.assertIn("length", str(ctx.exception))

    def test_index_property(self):
        from ucon.integrations.pandas import NumberSeries
        idx = pd.Index(['a', 'b', 'c'])
        s = pd.Series([1.0, 2.0, 3.0], index=idx)
        ns = NumberSeries(s, unit=self.meter)
        pd.testing.assert_index_equal(ns.index, idx)


@unittest.skipUnless(HAS_PANDAS, "Pandas not installed")
class TestNumberSeriesIndexing(unittest.TestCase):
    """Test NumberSeries indexing and iteration."""

    def setUp(self):
        from ucon import units
        self.meter = units.meter

    def test_scalar_index_returns_number(self):
        from ucon.integrations.pandas import NumberSeries
        from ucon.quantity import Number
        ns = NumberSeries(pd.Series([1.0, 2.0, 3.0]), unit=self.meter)
        elem = ns[0]
        self.assertIsInstance(elem, Number)
        self.assertEqual(elem.quantity, 1.0)

    def test_slice_returns_numberseries(self):
        from ucon.integrations.pandas import NumberSeries
        ns = NumberSeries(pd.Series([1.0, 2.0, 3.0, 4.0]), unit=self.meter)
        sliced = ns[1:3]
        self.assertIsInstance(sliced, NumberSeries)
        self.assertEqual(len(sliced), 2)

    def test_label_index(self):
        from ucon.integrations.pandas import NumberSeries
        from ucon.quantity import Number
        s = pd.Series([1.0, 2.0, 3.0], index=['a', 'b', 'c'])
        ns = NumberSeries(s, unit=self.meter)
        elem = ns['b']
        self.assertIsInstance(elem, Number)
        self.assertEqual(elem.quantity, 2.0)

    def test_iteration_yields_numbers(self):
        from ucon.integrations.pandas import NumberSeries
        from ucon.quantity import Number
        ns = NumberSeries(pd.Series([1.0, 2.0, 3.0]), unit=self.meter)
        elements = list(ns)
        self.assertEqual(len(elements), 3)
        for elem in elements:
            self.assertIsInstance(elem, Number)


@unittest.skipUnless(HAS_PANDAS, "Pandas not installed")
class TestNumberSeriesArithmetic(unittest.TestCase):
    """Test NumberSeries arithmetic operations."""

    def setUp(self):
        from ucon import units
        self.meter = units.meter
        self.second = units.second

    def test_multiply_by_scalar(self):
        from ucon.integrations.pandas import NumberSeries
        ns = NumberSeries(pd.Series([1.0, 2.0, 3.0]), unit=self.meter)
        result = ns * 2
        pd.testing.assert_series_equal(
            result.series, pd.Series([2.0, 4.0, 6.0]), check_names=False
        )
        self.assertEqual(result.unit, self.meter)

    def test_multiply_by_scalar_with_uncertainty(self):
        from ucon.integrations.pandas import NumberSeries
        ns = NumberSeries(pd.Series([1.0, 2.0]), unit=self.meter, uncertainty=0.1)
        result = ns * 2
        self.assertEqual(result.uncertainty, 0.2)

    def test_rmul(self):
        from ucon.integrations.pandas import NumberSeries
        ns = NumberSeries(pd.Series([1.0, 2.0, 3.0]), unit=self.meter)
        result = 2 * ns
        pd.testing.assert_series_equal(
            result.series, pd.Series([2.0, 4.0, 6.0]), check_names=False
        )

    def test_divide_by_scalar(self):
        from ucon.integrations.pandas import NumberSeries
        ns = NumberSeries(pd.Series([2.0, 4.0, 6.0]), unit=self.meter)
        result = ns / 2
        pd.testing.assert_series_equal(
            result.series, pd.Series([1.0, 2.0, 3.0]), check_names=False
        )

    def test_multiply_numberseries(self):
        from ucon.integrations.pandas import NumberSeries
        a = NumberSeries(pd.Series([1.0, 2.0]), unit=self.meter)
        b = NumberSeries(pd.Series([3.0, 4.0]), unit=self.second)
        result = a * b
        pd.testing.assert_series_equal(
            result.series, pd.Series([3.0, 8.0]), check_names=False
        )

    def test_multiply_length_mismatch(self):
        from ucon.integrations.pandas import NumberSeries
        a = NumberSeries(pd.Series([1.0, 2.0, 3.0]), unit=self.meter)
        b = NumberSeries(pd.Series([1.0, 2.0]), unit=self.meter)
        with self.assertRaises(ValueError) as ctx:
            a * b
        self.assertIn("Length mismatch", str(ctx.exception))

    def test_add_same_unit(self):
        from ucon.integrations.pandas import NumberSeries
        a = NumberSeries(pd.Series([1.0, 2.0]), unit=self.meter)
        b = NumberSeries(pd.Series([0.5, 0.5]), unit=self.meter)
        result = a + b
        pd.testing.assert_series_equal(
            result.series, pd.Series([1.5, 2.5]), check_names=False
        )

    def test_add_different_unit_raises(self):
        from ucon.integrations.pandas import NumberSeries
        a = NumberSeries(pd.Series([1.0, 2.0]), unit=self.meter)
        b = NumberSeries(pd.Series([1.0, 2.0]), unit=self.second)
        with self.assertRaises(ValueError) as ctx:
            a + b
        self.assertIn("different units", str(ctx.exception))

    def test_subtract(self):
        from ucon.integrations.pandas import NumberSeries
        a = NumberSeries(pd.Series([3.0, 4.0]), unit=self.meter)
        b = NumberSeries(pd.Series([1.0, 1.0]), unit=self.meter)
        result = a - b
        pd.testing.assert_series_equal(
            result.series, pd.Series([2.0, 3.0]), check_names=False
        )

    def test_negation(self):
        from ucon.integrations.pandas import NumberSeries
        ns = NumberSeries(pd.Series([1.0, -2.0, 3.0]), unit=self.meter)
        result = -ns
        pd.testing.assert_series_equal(
            result.series, pd.Series([-1.0, 2.0, -3.0]), check_names=False
        )

    def test_abs(self):
        from ucon.integrations.pandas import NumberSeries
        ns = NumberSeries(pd.Series([-1.0, 2.0, -3.0]), unit=self.meter)
        result = abs(ns)
        pd.testing.assert_series_equal(
            result.series, pd.Series([1.0, 2.0, 3.0]), check_names=False
        )


@unittest.skipUnless(HAS_PANDAS, "Pandas not installed")
class TestNumberSeriesArithmeticExtended(unittest.TestCase):
    """Extended arithmetic tests for coverage."""

    def setUp(self):
        from ucon import units
        self.meter = units.meter
        self.second = units.second

    def test_divide_by_number(self):
        """Test NumberSeries / Number."""
        from ucon.integrations.pandas import NumberSeries
        from ucon.quantity import Number
        ns = NumberSeries(pd.Series([10.0, 20.0, 30.0]), unit=self.meter)
        n = Number(quantity=2.0, unit=self.second)
        result = ns / n
        pd.testing.assert_series_equal(
            result.series, pd.Series([5.0, 10.0, 15.0]), check_names=False
        )

    def test_divide_by_number_with_uncertainty(self):
        """Test NumberSeries / Number with uncertainty."""
        from ucon.integrations.pandas import NumberSeries
        from ucon.quantity import Number
        ns = NumberSeries(pd.Series([10.0, 20.0]), unit=self.meter, uncertainty=1.0)
        n = Number(quantity=2.0, unit=self.second, uncertainty=0.1)
        result = ns / n
        self.assertIsNotNone(result.uncertainty)

    def test_divide_numberseries_with_uncertainty(self):
        """Test NumberSeries / NumberSeries with uncertainty."""
        from ucon.integrations.pandas import NumberSeries
        a = NumberSeries(pd.Series([10.0, 20.0]), unit=self.meter, uncertainty=1.0)
        b = NumberSeries(pd.Series([2.0, 4.0]), unit=self.second, uncertainty=0.1)
        result = a / b
        self.assertIsNotNone(result.uncertainty)

    def test_add_number(self):
        """Test NumberSeries + Number."""
        from ucon.integrations.pandas import NumberSeries
        from ucon.quantity import Number
        ns = NumberSeries(pd.Series([1.0, 2.0, 3.0]), unit=self.meter)
        n = Number(quantity=10.0, unit=self.meter)
        result = ns + n
        pd.testing.assert_series_equal(
            result.series, pd.Series([11.0, 12.0, 13.0]), check_names=False
        )

    def test_add_number_with_uncertainty(self):
        """Test NumberSeries + Number with uncertainty."""
        from ucon.integrations.pandas import NumberSeries
        from ucon.quantity import Number
        ns = NumberSeries(pd.Series([1.0, 2.0]), unit=self.meter, uncertainty=0.1)
        n = Number(quantity=10.0, unit=self.meter, uncertainty=0.2)
        result = ns + n
        expected_unc = math.sqrt(0.1**2 + 0.2**2)
        self.assertAlmostEqual(result.uncertainty, expected_unc)

    def test_sub_number(self):
        """Test NumberSeries - Number."""
        from ucon.integrations.pandas import NumberSeries
        from ucon.quantity import Number
        ns = NumberSeries(pd.Series([10.0, 20.0, 30.0]), unit=self.meter)
        n = Number(quantity=5.0, unit=self.meter)
        result = ns - n
        pd.testing.assert_series_equal(
            result.series, pd.Series([5.0, 15.0, 25.0]), check_names=False
        )

    def test_multiply_by_number(self):
        """Test NumberSeries * Number."""
        from ucon.integrations.pandas import NumberSeries
        from ucon.quantity import Number
        ns = NumberSeries(pd.Series([1.0, 2.0, 3.0]), unit=self.meter)
        n = Number(quantity=2.0, unit=self.second)
        result = ns * n
        pd.testing.assert_series_equal(
            result.series, pd.Series([2.0, 4.0, 6.0]), check_names=False
        )

    def test_multiply_by_number_with_uncertainty(self):
        """Test NumberSeries * Number with uncertainty."""
        from ucon.integrations.pandas import NumberSeries
        from ucon.quantity import Number
        ns = NumberSeries(pd.Series([10.0, 20.0]), unit=self.meter, uncertainty=1.0)
        n = Number(quantity=2.0, unit=self.second, uncertainty=0.1)
        result = ns * n
        self.assertIsNotNone(result.uncertainty)

    def test_divide_numberseries_length_mismatch(self):
        """Test division with length mismatch."""
        from ucon.integrations.pandas import NumberSeries
        a = NumberSeries(pd.Series([1.0, 2.0, 3.0]), unit=self.meter)
        b = NumberSeries(pd.Series([1.0, 2.0]), unit=self.second)
        with self.assertRaises(ValueError) as ctx:
            a / b
        self.assertIn("Length mismatch", str(ctx.exception))

    def test_add_length_mismatch(self):
        """Test addition with length mismatch."""
        from ucon.integrations.pandas import NumberSeries
        a = NumberSeries(pd.Series([1.0, 2.0, 3.0]), unit=self.meter)
        b = NumberSeries(pd.Series([1.0, 2.0]), unit=self.meter)
        with self.assertRaises(ValueError) as ctx:
            a + b
        self.assertIn("Length mismatch", str(ctx.exception))


@unittest.skipUnless(HAS_PANDAS, "Pandas not installed")
class TestNumberSeriesConversion(unittest.TestCase):
    """Test NumberSeries unit conversion."""

    def setUp(self):
        from ucon import units
        from ucon.core import Scale
        self.meter = units.meter
        self.foot = units.foot
        self.kilometer = Scale.kilo * units.meter

    def test_scale_only_conversion(self):
        from ucon.integrations.pandas import NumberSeries
        ns = NumberSeries(pd.Series([1.0, 2.0, 3.0]), unit=self.kilometer)
        result = ns.to(self.meter)
        pd.testing.assert_series_equal(
            result.series, pd.Series([1000.0, 2000.0, 3000.0]), check_names=False
        )
        self.assertEqual(result.unit, self.meter)

    def test_conversion_with_uncertainty(self):
        from ucon.integrations.pandas import NumberSeries
        ns = NumberSeries(pd.Series([1.0, 2.0]), unit=self.kilometer, uncertainty=0.1)
        result = ns.to(self.meter)
        self.assertAlmostEqual(result.uncertainty, 100.0)

    def test_graph_based_conversion(self):
        from ucon.integrations.pandas import NumberSeries
        ns = NumberSeries(pd.Series([1.0, 2.0, 3.0]), unit=self.meter)
        result = ns.to(self.foot)
        # 1 meter ~ 3.28084 feet
        expected = pd.Series([1.0, 2.0, 3.0]) * 3.28084
        pd.testing.assert_series_equal(
            result.series, expected, check_names=False, atol=0.001
        )


@unittest.skipUnless(HAS_PANDAS, "Pandas not installed")
class TestNumberSeriesComparison(unittest.TestCase):
    """Test comparison operators returning boolean Series."""

    def setUp(self):
        from ucon import units
        self.meter = units.meter
        self.second = units.second

    def test_eq_with_scalar(self):
        from ucon.integrations.pandas import NumberSeries
        ns = NumberSeries(pd.Series([1.0, 2.0, 3.0]), unit=self.meter)
        result = ns == 2.0
        pd.testing.assert_series_equal(result, pd.Series([False, True, False]))

    def test_eq_with_number(self):
        from ucon.integrations.pandas import NumberSeries
        from ucon.quantity import Number
        ns = NumberSeries(pd.Series([1.0, 2.0, 3.0]), unit=self.meter)
        n = Number(quantity=2.0, unit=self.meter)
        result = ns == n
        pd.testing.assert_series_equal(result, pd.Series([False, True, False]))

    def test_eq_with_numberseries(self):
        from ucon.integrations.pandas import NumberSeries
        a = NumberSeries(pd.Series([1.0, 2.0, 3.0]), unit=self.meter)
        b = NumberSeries(pd.Series([1.0, 5.0, 3.0]), unit=self.meter)
        result = a == b
        pd.testing.assert_series_equal(result, pd.Series([True, False, True]))

    def test_ne_with_scalar(self):
        from ucon.integrations.pandas import NumberSeries
        ns = NumberSeries(pd.Series([1.0, 2.0, 3.0]), unit=self.meter)
        result = ns != 2.0
        pd.testing.assert_series_equal(result, pd.Series([True, False, True]))

    def test_lt_with_scalar(self):
        from ucon.integrations.pandas import NumberSeries
        ns = NumberSeries(pd.Series([1.0, 2.0, 3.0]), unit=self.meter)
        result = ns < 2.0
        pd.testing.assert_series_equal(result, pd.Series([True, False, False]))

    def test_le_with_scalar(self):
        from ucon.integrations.pandas import NumberSeries
        ns = NumberSeries(pd.Series([1.0, 2.0, 3.0]), unit=self.meter)
        result = ns <= 2.0
        pd.testing.assert_series_equal(result, pd.Series([True, True, False]))

    def test_gt_with_scalar(self):
        from ucon.integrations.pandas import NumberSeries
        ns = NumberSeries(pd.Series([1.0, 2.0, 3.0]), unit=self.meter)
        result = ns > 2.0
        pd.testing.assert_series_equal(result, pd.Series([False, False, True]))

    def test_ge_with_scalar(self):
        from ucon.integrations.pandas import NumberSeries
        ns = NumberSeries(pd.Series([1.0, 2.0, 3.0]), unit=self.meter)
        result = ns >= 2.0
        pd.testing.assert_series_equal(result, pd.Series([False, True, True]))

    def test_comparison_different_unit_raises(self):
        from ucon.integrations.pandas import NumberSeries
        a = NumberSeries(pd.Series([1.0, 2.0]), unit=self.meter)
        b = NumberSeries(pd.Series([1.0, 2.0]), unit=self.second)
        with self.assertRaises(ValueError) as ctx:
            a == b
        self.assertIn("different units", str(ctx.exception))

    def test_comparison_for_filtering(self):
        from ucon.integrations.pandas import NumberSeries
        ns = NumberSeries(pd.Series([1.0, 2.0, 3.0, 4.0, 5.0]), unit=self.meter)
        mask = ns > 2.5
        filtered = ns.series[mask]
        pd.testing.assert_series_equal(
            filtered.reset_index(drop=True),
            pd.Series([3.0, 4.0, 5.0])
        )


@unittest.skipUnless(HAS_PANDAS, "Pandas not installed")
class TestNumberSeriesReductions(unittest.TestCase):
    """Test reduction operations (sum, mean, etc.)."""

    def setUp(self):
        from ucon import units
        self.meter = units.meter

    def test_sum(self):
        from ucon.integrations.pandas import NumberSeries
        from ucon.quantity import Number
        ns = NumberSeries(pd.Series([1.0, 2.0, 3.0, 4.0]), unit=self.meter)
        total = ns.sum()
        self.assertIsInstance(total, Number)
        self.assertEqual(total.quantity, 10.0)
        self.assertEqual(total.unit, self.meter)

    def test_sum_with_uncertainty(self):
        from ucon.integrations.pandas import NumberSeries
        ns = NumberSeries(pd.Series([1.0, 2.0, 3.0, 4.0]), unit=self.meter, uncertainty=0.1)
        total = ns.sum()
        self.assertAlmostEqual(total.uncertainty, 0.1 * math.sqrt(4))

    def test_mean(self):
        from ucon.integrations.pandas import NumberSeries
        from ucon.quantity import Number
        ns = NumberSeries(pd.Series([2.0, 4.0, 6.0]), unit=self.meter)
        avg = ns.mean()
        self.assertIsInstance(avg, Number)
        self.assertEqual(avg.quantity, 4.0)

    def test_mean_with_uncertainty(self):
        from ucon.integrations.pandas import NumberSeries
        ns = NumberSeries(pd.Series([1.0, 2.0, 3.0, 4.0]), unit=self.meter, uncertainty=0.2)
        avg = ns.mean()
        self.assertAlmostEqual(avg.uncertainty, 0.2 / math.sqrt(4))

    def test_std(self):
        from ucon.integrations.pandas import NumberSeries
        ns = NumberSeries(pd.Series([2.0, 4.0, 6.0, 8.0]), unit=self.meter)
        s = ns.std()
        expected = pd.Series([2.0, 4.0, 6.0, 8.0]).std()
        self.assertAlmostEqual(s.quantity, expected)

    def test_min_max(self):
        from ucon.integrations.pandas import NumberSeries
        ns = NumberSeries(pd.Series([3.0, 1.0, 4.0, 1.0, 5.0]), unit=self.meter)
        self.assertEqual(ns.min().quantity, 1.0)
        self.assertEqual(ns.max().quantity, 5.0)


@unittest.skipUnless(HAS_PANDAS, "Pandas not installed")
class TestNumberSeriesRepr(unittest.TestCase):
    """Test string representation."""

    def setUp(self):
        from ucon import units
        self.meter = units.meter

    def test_small_series_repr(self):
        from ucon.integrations.pandas import NumberSeries
        ns = NumberSeries(pd.Series([1.0, 2.0, 3.0]), unit=self.meter)
        s = repr(ns)
        self.assertIn("NumberSeries", s)
        self.assertIn("m", s)

    def test_large_series_truncation(self):
        from ucon.integrations.pandas import NumberSeries
        ns = NumberSeries(pd.Series(range(100)), unit=self.meter)
        s = repr(ns)
        self.assertIn("...", s)

    def test_repr_with_uncertainty(self):
        from ucon.integrations.pandas import NumberSeries
        ns = NumberSeries(pd.Series([1.0, 2.0]), unit=self.meter, uncertainty=0.1)
        s = repr(ns)
        self.assertIn("\u00b1", s)


@unittest.skipUnless(HAS_PANDAS, "Pandas not installed")
class TestUconSeriesAccessor(unittest.TestCase):
    """Test the pandas Series accessor."""

    def setUp(self):
        from ucon import units
        self.meter = units.meter
        self.foot = units.foot

    def test_accessor_with_unit(self):
        from ucon.integrations.pandas import NumberSeries
        s = pd.Series([1.7, 1.8, 1.9])
        ns = s.ucon.with_unit(self.meter)
        self.assertIsInstance(ns, NumberSeries)
        self.assertEqual(ns.unit, self.meter)

    def test_accessor_callable(self):
        from ucon.integrations.pandas import NumberSeries
        s = pd.Series([1.7, 1.8, 1.9])
        ns = s.ucon(self.meter)
        self.assertIsInstance(ns, NumberSeries)
        self.assertEqual(ns.unit, self.meter)

    def test_accessor_with_uncertainty(self):
        from ucon.integrations.pandas import NumberSeries
        s = pd.Series([1.7, 1.8, 1.9])
        ns = s.ucon.with_unit(self.meter, uncertainty=0.01)
        self.assertEqual(ns.uncertainty, 0.01)

    def test_accessor_conversion_chain(self):
        from ucon.integrations.pandas import NumberSeries
        s = pd.Series([1.0, 2.0, 3.0])
        result = s.ucon(self.meter).to(self.foot)
        self.assertIsInstance(result, NumberSeries)
        self.assertEqual(result.unit, self.foot)
        # Check conversion factor
        self.assertAlmostEqual(result.series.iloc[0], 3.28084, places=3)


@unittest.skipUnless(HAS_PANDAS, "Pandas not installed")
class TestNumberSeriesToFrame(unittest.TestCase):
    """Test DataFrame conversion."""

    def setUp(self):
        from ucon import units
        self.meter = units.meter

    def test_to_frame_default_name(self):
        from ucon.integrations.pandas import NumberSeries
        ns = NumberSeries(pd.Series([1.0, 2.0, 3.0]), unit=self.meter)
        df = ns.to_frame()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df.columns), 1)
        self.assertIn('m', df.columns[0])

    def test_to_frame_custom_name(self):
        from ucon.integrations.pandas import NumberSeries
        ns = NumberSeries(pd.Series([1.0, 2.0, 3.0]), unit=self.meter)
        df = ns.to_frame(name='height')
        self.assertEqual(df.columns[0], 'height')


@unittest.skipUnless(HAS_PANDAS, "Pandas not installed")
class TestNumberSeriesNotImplemented(unittest.TestCase):
    """Test NotImplemented return for unsupported operand types."""

    def setUp(self):
        from ucon import units
        from ucon.integrations.pandas import NumberSeries
        self.meter = units.meter
        self.ns = NumberSeries(pd.Series([1.0, 2.0, 3.0]), unit=self.meter)

    def test_mul_unsupported(self):
        result = self.ns.__mul__("string")
        self.assertIs(result, NotImplemented)

    def test_truediv_unsupported(self):
        result = self.ns.__truediv__("string")
        self.assertIs(result, NotImplemented)

    def test_add_unsupported(self):
        result = self.ns.__add__("string")
        self.assertIs(result, NotImplemented)

    def test_sub_unsupported(self):
        result = self.ns.__sub__("string")
        self.assertIs(result, NotImplemented)

    def test_eq_unsupported(self):
        result = self.ns.__eq__("string")
        self.assertIs(result, NotImplemented)

    def test_lt_unsupported(self):
        result = self.ns.__lt__("string")
        self.assertIs(result, NotImplemented)

    def test_le_unsupported(self):
        result = self.ns.__le__("string")
        self.assertIs(result, NotImplemented)

    def test_gt_unsupported(self):
        result = self.ns.__gt__("string")
        self.assertIs(result, NotImplemented)

    def test_ge_unsupported(self):
        result = self.ns.__ge__("string")
        self.assertIs(result, NotImplemented)

    def test_ne_unsupported(self):
        result = self.ns.__ne__("string")
        self.assertIs(result, NotImplemented)


@unittest.skipUnless(HAS_PANDAS, "Pandas not installed")
class TestNumberSeriesUncertaintyEdgeCases(unittest.TestCase):
    """Test uncertainty propagation edge cases."""

    def setUp(self):
        from ucon import units
        self.meter = units.meter

    def test_mul_both_no_uncertainty(self):
        """Multiplying series with no uncertainty returns no uncertainty."""
        from ucon.integrations.pandas import NumberSeries
        a = NumberSeries(pd.Series([1.0, 2.0]), unit=self.meter)
        result = a * 2
        self.assertIsNone(result.uncertainty)

    def test_add_one_uncertainty_one_none(self):
        """Adding series where one has uncertainty propagates it."""
        from ucon.integrations.pandas import NumberSeries
        a = NumberSeries(pd.Series([1.0, 2.0]), unit=self.meter, uncertainty=0.1)
        b = NumberSeries(pd.Series([3.0, 4.0]), unit=self.meter)
        result = a + b
        self.assertIsNotNone(result.uncertainty)

    def test_repr_per_element_uncertainty(self):
        """Per-element uncertainty shows [...] in repr."""
        from ucon.integrations.pandas import NumberSeries
        ns = NumberSeries(pd.Series([1.0, 2.0]), unit=self.meter,
                          uncertainty=pd.Series([0.1, 0.2]))
        r = repr(ns)
        self.assertIn('[', r)


if __name__ == "__main__":
    unittest.main()
