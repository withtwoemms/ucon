# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Tests for pickle serialization of ucon types.

Verifies that Number, Unit, UnitProduct, and related types
can be serialized and deserialized via pickle.
"""

import pickle
import unittest

from ucon import Number, Scale, units
from ucon.core import Unit, UnitProduct, UnitFactor, Dimension


class TestPickleNumber(unittest.TestCase):
    """Test pickle round-trip for Number."""

    def test_simple_number(self):
        """Test pickle of Number with simple unit."""
        n = Number(quantity=5, unit=units.meter)
        pickled = pickle.dumps(n)
        restored = pickle.loads(pickled)
        self.assertEqual(n, restored)

    def test_number_with_uncertainty(self):
        """Test pickle of Number with uncertainty."""
        n = Number(quantity=1.234, unit=units.kilogram, uncertainty=0.005)
        pickled = pickle.dumps(n)
        restored = pickle.loads(pickled)
        self.assertEqual(n.quantity, restored.quantity)
        self.assertEqual(n.uncertainty, restored.uncertainty)

    def test_number_with_unit_product(self):
        """Test pickle of Number with composite unit."""
        velocity = units.meter / units.second
        n = Number(quantity=10, unit=velocity)
        pickled = pickle.dumps(n)
        restored = pickle.loads(pickled)
        self.assertEqual(n, restored)

    def test_number_with_scaled_unit(self):
        """Test pickle of Number with scaled unit."""
        km = Scale.kilo * units.meter
        n = Number(quantity=5, unit=km)
        pickled = pickle.dumps(n)
        restored = pickle.loads(pickled)
        self.assertEqual(n, restored)

    def test_number_dimensionless(self):
        """Test pickle of dimensionless Number."""
        n = Number(quantity=3.14)
        pickled = pickle.dumps(n)
        restored = pickle.loads(pickled)
        self.assertEqual(n.quantity, restored.quantity)

    def test_number_with_complex_unit(self):
        """Test pickle of Number with complex composite unit."""
        # kg*m/s^2 (force)
        force_unit = units.kilogram * units.meter / (units.second ** 2)
        n = Number(quantity=9.8, unit=force_unit)
        pickled = pickle.dumps(n)
        restored = pickle.loads(pickled)
        self.assertEqual(n, restored)


class TestPickleUnit(unittest.TestCase):
    """Test pickle round-trip for Unit."""

    def test_simple_unit(self):
        """Test pickle of simple Unit."""
        pickled = pickle.dumps(units.meter)
        restored = pickle.loads(pickled)
        self.assertEqual(units.meter, restored)

    def test_multiple_units(self):
        """Test pickle of various units."""
        for unit in [units.second, units.kilogram, units.ampere, units.kelvin]:
            with self.subTest(unit=unit.name):
                pickled = pickle.dumps(unit)
                restored = pickle.loads(pickled)
                self.assertEqual(unit, restored)

    def test_unit_preserves_dimension(self):
        """Test that pickled unit preserves dimension."""
        pickled = pickle.dumps(units.meter)
        restored = pickle.loads(pickled)
        self.assertEqual(restored.dimension, Dimension.length)

    def test_unit_preserves_aliases(self):
        """Test that pickled unit preserves aliases."""
        pickled = pickle.dumps(units.meter)
        restored = pickle.loads(pickled)
        self.assertIn('m', restored.aliases)


class TestPickleUnitProduct(unittest.TestCase):
    """Test pickle round-trip for UnitProduct."""

    def test_simple_product(self):
        """Test pickle of simple UnitProduct."""
        up = units.meter / units.second
        pickled = pickle.dumps(up)
        restored = pickle.loads(pickled)
        self.assertEqual(up, restored)

    def test_complex_product(self):
        """Test pickle of complex UnitProduct."""
        up = units.kilogram * units.meter / (units.second ** 2)
        pickled = pickle.dumps(up)
        restored = pickle.loads(pickled)
        self.assertEqual(up, restored)

    def test_scaled_product(self):
        """Test pickle of scaled UnitProduct."""
        km = Scale.kilo * units.meter
        pickled = pickle.dumps(km)
        restored = pickle.loads(pickled)
        self.assertEqual(km, restored)

    def test_product_preserves_dimension(self):
        """Test that pickled UnitProduct preserves dimension."""
        velocity = units.meter / units.second
        pickled = pickle.dumps(velocity)
        restored = pickle.loads(pickled)
        self.assertEqual(restored.dimension, Dimension.velocity)

    def test_product_preserves_scale(self):
        """Test that pickled UnitProduct preserves scale factor."""
        km = Scale.kilo * units.meter
        pickled = pickle.dumps(km)
        restored = pickle.loads(pickled)
        self.assertAlmostEqual(km.fold_scale(), restored.fold_scale())


class TestPickleUnitFactor(unittest.TestCase):
    """Test pickle round-trip for UnitFactor."""

    def test_simple_factor(self):
        """Test pickle of UnitFactor with Scale.one."""
        uf = UnitFactor(units.meter, Scale.one)
        pickled = pickle.dumps(uf)
        restored = pickle.loads(pickled)
        self.assertEqual(uf, restored)

    def test_scaled_factor(self):
        """Test pickle of UnitFactor with scale prefix."""
        uf = UnitFactor(units.meter, Scale.kilo)
        pickled = pickle.dumps(uf)
        restored = pickle.loads(pickled)
        self.assertEqual(uf, restored)

    def test_factor_preserves_unit(self):
        """Test that pickled UnitFactor preserves unit."""
        uf = UnitFactor(units.gram, Scale.milli)
        pickled = pickle.dumps(uf)
        restored = pickle.loads(pickled)
        self.assertEqual(restored.unit, units.gram)

    def test_factor_preserves_scale(self):
        """Test that pickled UnitFactor preserves scale."""
        uf = UnitFactor(units.gram, Scale.milli)
        pickled = pickle.dumps(uf)
        restored = pickle.loads(pickled)
        self.assertEqual(restored.scale, Scale.milli)


class TestPickleScale(unittest.TestCase):
    """Test pickle round-trip for Scale enum."""

    def test_scale_values(self):
        """Test pickle of various Scale values."""
        for scale in [Scale.one, Scale.kilo, Scale.milli, Scale.mega, Scale.micro]:
            with self.subTest(scale=scale.name):
                pickled = pickle.dumps(scale)
                restored = pickle.loads(pickled)
                self.assertEqual(scale, restored)


class TestPickleDimension(unittest.TestCase):
    """Test pickle round-trip for Dimension enum."""

    def test_dimension_values(self):
        """Test pickle of various Dimension values."""
        for dim in [Dimension.length, Dimension.mass, Dimension.time,
                    Dimension.velocity, Dimension.force]:
            with self.subTest(dim=dim.name):
                pickled = pickle.dumps(dim)
                restored = pickle.loads(pickled)
                self.assertEqual(dim, restored)


if __name__ == '__main__':
    unittest.main()
