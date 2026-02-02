# © 2025 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Tests for Pydantic v2 integration.

Verifies that ucon types can be used as Pydantic model fields
and that validation and serialization work correctly.

These tests are skipped if pydantic is not installed.
"""

import json
import unittest

from ucon import units
from ucon.core import Number as CoreNumber


class TestPydanticIntegration(unittest.TestCase):
    """Test basic Pydantic v2 integration."""

    @classmethod
    def setUpClass(cls):
        try:
            from pydantic import BaseModel, ValidationError
            from ucon.pydantic import Number
            cls.BaseModel = BaseModel
            cls.ValidationError = ValidationError
            cls.Number = Number
            cls.skip_tests = False
        except ImportError:
            cls.skip_tests = True

    def setUp(self):
        if self.skip_tests:
            self.skipTest("pydantic not installed")

    def test_number_from_dict(self):
        """Test creating Number from dict in Pydantic model."""
        class Model(self.BaseModel):
            value: self.Number

        m = Model(value={"quantity": 5, "unit": "m"})
        self.assertEqual(m.value.quantity, 5)
        self.assertIsInstance(m.value, CoreNumber)

    def test_number_from_instance(self):
        """Test using Number instance directly in Pydantic model."""
        class Model(self.BaseModel):
            value: self.Number

        m = Model(value=units.meter(10))
        self.assertEqual(m.value.quantity, 10)

    def test_number_quantity_only(self):
        """Test Number with quantity only (no unit)."""
        class Model(self.BaseModel):
            value: self.Number

        m = Model(value={"quantity": 42})
        self.assertEqual(m.value.quantity, 42)

    def test_number_with_uncertainty(self):
        """Test Number with uncertainty field."""
        class Model(self.BaseModel):
            value: self.Number

        m = Model(value={"quantity": 1.234, "unit": "kg", "uncertainty": 0.005})
        self.assertEqual(m.value.quantity, 1.234)
        self.assertEqual(m.value.uncertainty, 0.005)


class TestPydanticSerialization(unittest.TestCase):
    """Test Pydantic serialization of Number."""

    @classmethod
    def setUpClass(cls):
        try:
            from pydantic import BaseModel, ValidationError
            from ucon.pydantic import Number
            cls.BaseModel = BaseModel
            cls.ValidationError = ValidationError
            cls.Number = Number
            cls.skip_tests = False
        except ImportError:
            cls.skip_tests = True

    def setUp(self):
        if self.skip_tests:
            self.skipTest("pydantic not installed")

    def test_serialize_simple(self):
        """Test model_dump() produces correct dict."""
        class Model(self.BaseModel):
            value: self.Number

        m = Model(value={"quantity": 5, "unit": "m"})
        dumped = m.model_dump()
        self.assertEqual(dumped["value"]["quantity"], 5.0)
        self.assertEqual(dumped["value"]["unit"], "m")
        self.assertIsNone(dumped["value"]["uncertainty"])

    def test_serialize_json(self):
        """Test model_dump_json() produces valid JSON."""
        class Model(self.BaseModel):
            value: self.Number

        m = Model(value={"quantity": 5, "unit": "m"})
        json_str = m.model_dump_json()
        parsed = json.loads(json_str)
        self.assertEqual(parsed["value"]["quantity"], 5.0)
        self.assertEqual(parsed["value"]["unit"], "m")

    def test_serialize_with_uncertainty(self):
        """Test serialization includes uncertainty."""
        class Model(self.BaseModel):
            value: self.Number

        m = Model(value={"quantity": 1.0, "unit": "kg", "uncertainty": 0.1})
        dumped = m.model_dump()
        self.assertEqual(dumped["value"]["uncertainty"], 0.1)

    def test_serialize_dimensionless_null_unit(self):
        """Test dimensionless quantities serialize with null unit."""
        class Model(self.BaseModel):
            value: self.Number

        m = Model(value={"quantity": 42})
        dumped = m.model_dump()
        self.assertIsNone(dumped["value"]["unit"])


class TestPydanticRoundtrip(unittest.TestCase):
    """Test round-trip serialization/deserialization."""

    @classmethod
    def setUpClass(cls):
        try:
            from pydantic import BaseModel, ValidationError
            from ucon.pydantic import Number
            cls.BaseModel = BaseModel
            cls.ValidationError = ValidationError
            cls.Number = Number
            cls.skip_tests = False
        except ImportError:
            cls.skip_tests = True

    def setUp(self):
        if self.skip_tests:
            self.skipTest("pydantic not installed")

    def test_roundtrip_simple(self):
        """Test JSON round-trip preserves values."""
        class Model(self.BaseModel):
            value: self.Number

        original = Model(value={"quantity": 3.14, "unit": "m"})
        json_str = original.model_dump_json()
        restored = Model.model_validate_json(json_str)

        self.assertAlmostEqual(restored.value.quantity, 3.14)

    def test_roundtrip_with_uncertainty(self):
        """Test round-trip preserves uncertainty."""
        class Model(self.BaseModel):
            value: self.Number

        original = Model(value={"quantity": 1.234, "unit": "kg", "uncertainty": 0.005})
        json_str = original.model_dump_json()
        restored = Model.model_validate_json(json_str)

        self.assertAlmostEqual(restored.value.quantity, 1.234)
        self.assertAlmostEqual(restored.value.uncertainty, 0.005)

    def test_roundtrip_scaled_unit(self):
        """Test round-trip with scaled unit."""
        class Model(self.BaseModel):
            value: self.Number

        original = Model(value={"quantity": 100, "unit": "km"})
        json_str = original.model_dump_json()
        restored = Model.model_validate_json(json_str)

        self.assertAlmostEqual(restored.value.quantity, 100)


class TestPydanticScaledUnits(unittest.TestCase):
    """Test Pydantic integration with scaled units."""

    @classmethod
    def setUpClass(cls):
        try:
            from pydantic import BaseModel, ValidationError
            from ucon.pydantic import Number
            cls.BaseModel = BaseModel
            cls.ValidationError = ValidationError
            cls.Number = Number
            cls.skip_tests = False
        except ImportError:
            cls.skip_tests = True

    def setUp(self):
        if self.skip_tests:
            self.skipTest("pydantic not installed")

    def test_kilometer(self):
        """Test parsing kilometer."""
        class Model(self.BaseModel):
            value: self.Number

        m = Model(value={"quantity": 5, "unit": "km"})
        self.assertEqual(m.value.quantity, 5)
        self.assertAlmostEqual(m.value.unit.fold_scale(), 1000.0)

    def test_milligram(self):
        """Test parsing milligram."""
        class Model(self.BaseModel):
            value: self.Number

        m = Model(value={"quantity": 100, "unit": "mg"})
        self.assertEqual(m.value.quantity, 100)
        self.assertAlmostEqual(m.value.unit.fold_scale(), 0.001)

    def test_megabyte(self):
        """Test parsing megabyte."""
        class Model(self.BaseModel):
            value: self.Number

        m = Model(value={"quantity": 512, "unit": "MB"})
        self.assertEqual(m.value.quantity, 512)


class TestPydanticCompositeUnits(unittest.TestCase):
    """Test Pydantic integration with composite units."""

    @classmethod
    def setUpClass(cls):
        try:
            from pydantic import BaseModel, ValidationError
            from ucon.pydantic import Number
            cls.BaseModel = BaseModel
            cls.ValidationError = ValidationError
            cls.Number = Number
            cls.skip_tests = False
        except ImportError:
            cls.skip_tests = True

    def setUp(self):
        if self.skip_tests:
            self.skipTest("pydantic not installed")

    def test_velocity(self):
        """Test parsing velocity unit."""
        class Model(self.BaseModel):
            value: self.Number

        m = Model(value={"quantity": 60, "unit": "m/s"})
        self.assertEqual(m.value.quantity, 60)

    def test_acceleration_unicode(self):
        """Test parsing acceleration with Unicode superscript."""
        class Model(self.BaseModel):
            value: self.Number

        m = Model(value={"quantity": 9.8, "unit": "m/s²"})
        self.assertEqual(m.value.quantity, 9.8)

    def test_acceleration_ascii(self):
        """Test parsing acceleration with ASCII exponent."""
        class Model(self.BaseModel):
            value: self.Number

        m = Model(value={"quantity": 9.8, "unit": "m/s^2"})
        self.assertEqual(m.value.quantity, 9.8)

    def test_force_unicode(self):
        """Test parsing force unit with Unicode notation."""
        class Model(self.BaseModel):
            value: self.Number

        m = Model(value={"quantity": 10, "unit": "kg·m/s²"})
        self.assertEqual(m.value.quantity, 10)

    def test_force_ascii(self):
        """Test parsing force unit with ASCII notation."""
        class Model(self.BaseModel):
            value: self.Number

        m = Model(value={"quantity": 10, "unit": "kg*m/s^2"})
        self.assertEqual(m.value.quantity, 10)

    def test_ascii_equals_unicode(self):
        """Test that ASCII and Unicode notations produce equal units."""
        class Model(self.BaseModel):
            value: self.Number

        unicode_model = Model(value={"quantity": 1, "unit": "kg·m/s²"})
        ascii_model = Model(value={"quantity": 1, "unit": "kg*m/s^2"})

        self.assertEqual(unicode_model.value.unit, ascii_model.value.unit)


class TestPydanticValidationErrors(unittest.TestCase):
    """Test Pydantic validation error handling."""

    @classmethod
    def setUpClass(cls):
        try:
            from pydantic import BaseModel, ValidationError
            from ucon.pydantic import Number
            cls.BaseModel = BaseModel
            cls.ValidationError = ValidationError
            cls.Number = Number
            cls.skip_tests = False
        except ImportError:
            cls.skip_tests = True

    def setUp(self):
        if self.skip_tests:
            self.skipTest("pydantic not installed")

    def test_unknown_unit_raises(self):
        """Test that unknown unit raises ValidationError."""
        class Model(self.BaseModel):
            value: self.Number

        with self.assertRaises(self.ValidationError):
            Model(value={"quantity": 5, "unit": "foobar"})

    def test_missing_quantity_raises(self):
        """Test that missing quantity raises ValidationError."""
        class Model(self.BaseModel):
            value: self.Number

        with self.assertRaises(self.ValidationError):
            Model(value={"unit": "m"})

    def test_invalid_type_raises(self):
        """Test that invalid type raises ValidationError."""
        class Model(self.BaseModel):
            value: self.Number

        with self.assertRaises(self.ValidationError):
            Model(value="not a number")


if __name__ == '__main__':
    unittest.main()
