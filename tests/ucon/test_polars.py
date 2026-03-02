# tests/ucon/test_polars.py
#
# Tests for NumberColumn and polars integration.

import unittest
import math

try:
    import polars as pl
    HAS_POLARS = True
except ImportError:
    HAS_POLARS = False


@unittest.skipUnless(HAS_POLARS, "Polars not installed")
class TestNumberColumnBasic(unittest.TestCase):
    """Test NumberColumn construction and basic properties."""

    def setUp(self):
        from ucon import units
        self.meter = units.meter
        self.foot = units.foot
        self.second = units.second

    def test_create_from_series(self):
        from ucon.polars import NumberColumn
        s = pl.Series([1.0, 2.0, 3.0])
        nc = NumberColumn(s, unit=self.meter)
        self.assertEqual(len(nc), 3)
        self.assertEqual(nc.unit, self.meter)

    def test_create_from_list(self):
        from ucon.polars import NumberColumn
        nc = NumberColumn([1.0, 2.0, 3.0], unit=self.meter)
        self.assertEqual(len(nc), 3)
        self.assertIsInstance(nc.series, pl.Series)

    def test_default_unit_is_dimensionless(self):
        from ucon.polars import NumberColumn
        from ucon.core import _none
        nc = NumberColumn(pl.Series([1.0, 2.0]))
        self.assertEqual(nc.unit, _none)

    def test_uniform_uncertainty(self):
        from ucon.polars import NumberColumn
        nc = NumberColumn(pl.Series([1.0, 2.0, 3.0]), unit=self.meter, uncertainty=0.1)
        self.assertEqual(nc.uncertainty, 0.1)

    def test_per_element_uncertainty(self):
        from ucon.polars import NumberColumn
        unc = pl.Series([0.1, 0.2, 0.3])
        nc = NumberColumn(pl.Series([1.0, 2.0, 3.0]), unit=self.meter, uncertainty=unc)
        self.assertEqual(len(nc.uncertainty), 3)

    def test_uncertainty_length_mismatch_raises(self):
        from ucon.polars import NumberColumn
        with self.assertRaises(ValueError) as ctx:
            NumberColumn(pl.Series([1.0, 2.0, 3.0]), unit=self.meter,
                        uncertainty=pl.Series([0.1, 0.2]))
        self.assertIn("length", str(ctx.exception))


@unittest.skipUnless(HAS_POLARS, "Polars not installed")
class TestNumberColumnIndexing(unittest.TestCase):
    """Test NumberColumn indexing and iteration."""

    def setUp(self):
        from ucon import units
        self.meter = units.meter

    def test_scalar_index_returns_number(self):
        from ucon.polars import NumberColumn
        from ucon.core import Number
        nc = NumberColumn(pl.Series([1.0, 2.0, 3.0]), unit=self.meter)
        elem = nc[0]
        self.assertIsInstance(elem, Number)
        self.assertEqual(elem.quantity, 1.0)

    def test_slice_returns_numbercolumn(self):
        from ucon.polars import NumberColumn
        nc = NumberColumn(pl.Series([1.0, 2.0, 3.0, 4.0]), unit=self.meter)
        sliced = nc[1:3]
        self.assertIsInstance(sliced, NumberColumn)
        self.assertEqual(len(sliced), 2)

    def test_iteration_yields_numbers(self):
        from ucon.polars import NumberColumn
        from ucon.core import Number
        nc = NumberColumn(pl.Series([1.0, 2.0, 3.0]), unit=self.meter)
        elements = list(nc)
        self.assertEqual(len(elements), 3)
        for elem in elements:
            self.assertIsInstance(elem, Number)


@unittest.skipUnless(HAS_POLARS, "Polars not installed")
class TestNumberColumnArithmetic(unittest.TestCase):
    """Test NumberColumn arithmetic operations."""

    def setUp(self):
        from ucon import units
        self.meter = units.meter
        self.second = units.second

    def test_multiply_by_scalar(self):
        from ucon.polars import NumberColumn
        nc = NumberColumn(pl.Series([1.0, 2.0, 3.0]), unit=self.meter)
        result = nc * 2
        self.assertEqual(result.series.to_list(), [2.0, 4.0, 6.0])
        self.assertEqual(result.unit, self.meter)

    def test_multiply_by_scalar_with_uncertainty(self):
        from ucon.polars import NumberColumn
        nc = NumberColumn(pl.Series([1.0, 2.0]), unit=self.meter, uncertainty=0.1)
        result = nc * 2
        self.assertEqual(result.uncertainty, 0.2)

    def test_rmul(self):
        from ucon.polars import NumberColumn
        nc = NumberColumn(pl.Series([1.0, 2.0, 3.0]), unit=self.meter)
        result = 2 * nc
        self.assertEqual(result.series.to_list(), [2.0, 4.0, 6.0])

    def test_divide_by_scalar(self):
        from ucon.polars import NumberColumn
        nc = NumberColumn(pl.Series([2.0, 4.0, 6.0]), unit=self.meter)
        result = nc / 2
        self.assertEqual(result.series.to_list(), [1.0, 2.0, 3.0])

    def test_multiply_numbercolumns(self):
        from ucon.polars import NumberColumn
        a = NumberColumn(pl.Series([1.0, 2.0]), unit=self.meter)
        b = NumberColumn(pl.Series([3.0, 4.0]), unit=self.second)
        result = a * b
        self.assertEqual(result.series.to_list(), [3.0, 8.0])

    def test_multiply_length_mismatch(self):
        from ucon.polars import NumberColumn
        a = NumberColumn(pl.Series([1.0, 2.0, 3.0]), unit=self.meter)
        b = NumberColumn(pl.Series([1.0, 2.0]), unit=self.meter)
        with self.assertRaises(ValueError) as ctx:
            a * b
        self.assertIn("Length mismatch", str(ctx.exception))

    def test_add_same_unit(self):
        from ucon.polars import NumberColumn
        a = NumberColumn(pl.Series([1.0, 2.0]), unit=self.meter)
        b = NumberColumn(pl.Series([0.5, 0.5]), unit=self.meter)
        result = a + b
        self.assertEqual(result.series.to_list(), [1.5, 2.5])

    def test_add_different_unit_raises(self):
        from ucon.polars import NumberColumn
        a = NumberColumn(pl.Series([1.0, 2.0]), unit=self.meter)
        b = NumberColumn(pl.Series([1.0, 2.0]), unit=self.second)
        with self.assertRaises(ValueError) as ctx:
            a + b
        self.assertIn("different units", str(ctx.exception))

    def test_subtract(self):
        from ucon.polars import NumberColumn
        a = NumberColumn(pl.Series([3.0, 4.0]), unit=self.meter)
        b = NumberColumn(pl.Series([1.0, 1.0]), unit=self.meter)
        result = a - b
        self.assertEqual(result.series.to_list(), [2.0, 3.0])

    def test_negation(self):
        from ucon.polars import NumberColumn
        nc = NumberColumn(pl.Series([1.0, -2.0, 3.0]), unit=self.meter)
        result = -nc
        self.assertEqual(result.series.to_list(), [-1.0, 2.0, -3.0])

    def test_abs(self):
        from ucon.polars import NumberColumn
        nc = NumberColumn(pl.Series([-1.0, 2.0, -3.0]), unit=self.meter)
        result = abs(nc)
        self.assertEqual(result.series.to_list(), [1.0, 2.0, 3.0])


@unittest.skipUnless(HAS_POLARS, "Polars not installed")
class TestNumberColumnConversion(unittest.TestCase):
    """Test NumberColumn unit conversion."""

    def setUp(self):
        from ucon import units
        from ucon.core import Scale
        self.meter = units.meter
        self.foot = units.foot
        self.kilometer = Scale.kilo * units.meter

    def test_scale_only_conversion(self):
        from ucon.polars import NumberColumn
        nc = NumberColumn(pl.Series([1.0, 2.0, 3.0]), unit=self.kilometer)
        result = nc.to(self.meter)
        self.assertEqual(result.series.to_list(), [1000.0, 2000.0, 3000.0])
        self.assertEqual(result.unit, self.meter)

    def test_conversion_with_uncertainty(self):
        from ucon.polars import NumberColumn
        nc = NumberColumn(pl.Series([1.0, 2.0]), unit=self.kilometer, uncertainty=0.1)
        result = nc.to(self.meter)
        self.assertAlmostEqual(result.uncertainty, 100.0)

    def test_graph_based_conversion(self):
        from ucon.polars import NumberColumn
        nc = NumberColumn(pl.Series([1.0, 2.0, 3.0]), unit=self.meter)
        result = nc.to(self.foot)
        # 1 meter ~ 3.28084 feet
        expected = [v * 3.28084 for v in [1.0, 2.0, 3.0]]
        for i, (actual, exp) in enumerate(zip(result.series.to_list(), expected)):
            self.assertAlmostEqual(actual, exp, places=3)


@unittest.skipUnless(HAS_POLARS, "Polars not installed")
class TestNumberColumnReductions(unittest.TestCase):
    """Test reduction operations (sum, mean, etc.)."""

    def setUp(self):
        from ucon import units
        self.meter = units.meter

    def test_sum(self):
        from ucon.polars import NumberColumn
        from ucon.core import Number
        nc = NumberColumn(pl.Series([1.0, 2.0, 3.0, 4.0]), unit=self.meter)
        total = nc.sum()
        self.assertIsInstance(total, Number)
        self.assertEqual(total.quantity, 10.0)
        self.assertEqual(total.unit, self.meter)

    def test_sum_with_uncertainty(self):
        from ucon.polars import NumberColumn
        nc = NumberColumn(pl.Series([1.0, 2.0, 3.0, 4.0]), unit=self.meter, uncertainty=0.1)
        total = nc.sum()
        self.assertAlmostEqual(total.uncertainty, 0.1 * math.sqrt(4))

    def test_mean(self):
        from ucon.polars import NumberColumn
        from ucon.core import Number
        nc = NumberColumn(pl.Series([2.0, 4.0, 6.0]), unit=self.meter)
        avg = nc.mean()
        self.assertIsInstance(avg, Number)
        self.assertEqual(avg.quantity, 4.0)

    def test_mean_with_uncertainty(self):
        from ucon.polars import NumberColumn
        nc = NumberColumn(pl.Series([1.0, 2.0, 3.0, 4.0]), unit=self.meter, uncertainty=0.2)
        avg = nc.mean()
        self.assertAlmostEqual(avg.uncertainty, 0.2 / math.sqrt(4))

    def test_std(self):
        from ucon.polars import NumberColumn
        nc = NumberColumn(pl.Series([2.0, 4.0, 6.0, 8.0]), unit=self.meter)
        s = nc.std()
        expected = pl.Series([2.0, 4.0, 6.0, 8.0]).std()
        self.assertAlmostEqual(s.quantity, expected)

    def test_min_max(self):
        from ucon.polars import NumberColumn
        nc = NumberColumn(pl.Series([3.0, 1.0, 4.0, 1.0, 5.0]), unit=self.meter)
        self.assertEqual(nc.min().quantity, 1.0)
        self.assertEqual(nc.max().quantity, 5.0)


@unittest.skipUnless(HAS_POLARS, "Polars not installed")
class TestNumberColumnRepr(unittest.TestCase):
    """Test string representation."""

    def setUp(self):
        from ucon import units
        self.meter = units.meter

    def test_small_column_repr(self):
        from ucon.polars import NumberColumn
        nc = NumberColumn(pl.Series([1.0, 2.0, 3.0]), unit=self.meter)
        s = repr(nc)
        self.assertIn("NumberColumn", s)
        self.assertIn("m", s)

    def test_large_column_truncation(self):
        from ucon.polars import NumberColumn
        nc = NumberColumn(pl.Series(list(range(100))), unit=self.meter)
        s = repr(nc)
        self.assertIn("...", s)

    def test_repr_with_uncertainty(self):
        from ucon.polars import NumberColumn
        nc = NumberColumn(pl.Series([1.0, 2.0]), unit=self.meter, uncertainty=0.1)
        s = repr(nc)
        self.assertIn("\u00b1", s)


@unittest.skipUnless(HAS_POLARS, "Polars not installed")
class TestNumberColumnToList(unittest.TestCase):
    """Test to_list conversion."""

    def setUp(self):
        from ucon import units
        self.meter = units.meter

    def test_to_list(self):
        from ucon.polars import NumberColumn
        from ucon.core import Number
        nc = NumberColumn(pl.Series([1.0, 2.0, 3.0]), unit=self.meter)
        numbers = nc.to_list()
        self.assertEqual(len(numbers), 3)
        for n in numbers:
            self.assertIsInstance(n, Number)
            self.assertEqual(n.unit, self.meter)


if __name__ == "__main__":
    unittest.main()
