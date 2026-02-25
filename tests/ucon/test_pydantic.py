# © 2026 The Radiativity Company
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


class TestPydanticDimensionConstraints(unittest.TestCase):
    """Test dimension-constrained Number types."""

    @classmethod
    def setUpClass(cls):
        try:
            from pydantic import BaseModel, ValidationError
            from ucon.pydantic import Number
            from ucon.core import Dimension
            cls.BaseModel = BaseModel
            cls.ValidationError = ValidationError
            cls.Number = Number
            cls.Dimension = Dimension
            cls.skip_tests = False
        except ImportError:
            cls.skip_tests = True

    def setUp(self):
        if self.skip_tests:
            self.skipTest("pydantic not installed")

    def test_dimension_constraint_valid(self):
        """Test Number[Dimension.xxx] accepts correct dimension."""
        class Model(self.BaseModel):
            length: self.Number[self.Dimension.length]

        m = Model(length={"quantity": 5, "unit": "m"})
        self.assertEqual(m.length.quantity, 5)

    def test_dimension_constraint_invalid(self):
        """Test Number[Dimension.xxx] rejects wrong dimension."""
        class Model(self.BaseModel):
            length: self.Number[self.Dimension.length]

        with self.assertRaises(self.ValidationError) as ctx:
            Model(length={"quantity": 5, "unit": "kg"})
        self.assertIn("mass", str(ctx.exception))
        self.assertIn("length", str(ctx.exception))

    def test_dimension_constraint_multiple_fields(self):
        """Test model with multiple dimension-constrained fields."""
        class Vehicle(self.BaseModel):
            mass: self.Number[self.Dimension.mass]
            speed: self.Number[self.Dimension.velocity]

        v = Vehicle(
            mass={"quantity": 1500, "unit": "kg"},
            speed={"quantity": 100, "unit": "m/s"},
        )
        self.assertEqual(v.mass.quantity, 1500)
        self.assertEqual(v.speed.quantity, 100)

    def test_dimension_constraint_wrong_type_raises(self):
        """Test Number[non-Dimension] raises TypeError."""
        with self.assertRaises(TypeError) as ctx:
            class BadModel(self.BaseModel):
                value: self.Number["not_a_dimension"]
        self.assertIn("Dimension", str(ctx.exception))

    def test_dimension_constraint_serialization(self):
        """Test dimension-constrained Number serializes correctly."""
        class Model(self.BaseModel):
            length: self.Number[self.Dimension.length]

        m = Model(length={"quantity": 5, "unit": "km"})
        dumped = m.model_dump()
        self.assertEqual(dumped["length"]["quantity"], 5.0)
        self.assertEqual(dumped["length"]["unit"], "km")


class TestPydanticConstrainedNumber(unittest.TestCase):
    """Test constrained_number factory."""

    @classmethod
    def setUpClass(cls):
        try:
            from pydantic import BaseModel, ValidationError
            from pydantic.functional_validators import AfterValidator
            from ucon.pydantic import Number, constrained_number
            from ucon.core import Dimension
            cls.BaseModel = BaseModel
            cls.ValidationError = ValidationError
            cls.Number = Number
            cls.constrained_number = constrained_number
            cls.AfterValidator = AfterValidator
            cls.Dimension = Dimension
            cls.skip_tests = False
        except ImportError:
            cls.skip_tests = True

    def setUp(self):
        if self.skip_tests:
            self.skipTest("pydantic not installed")

    def test_constrained_number_with_dimension(self):
        """Test constrained_number with dimension constraint."""
        def must_be_positive(n):
            if n.quantity <= 0:
                raise ValueError("must be positive")
            return n

        PositiveNumber = self.constrained_number(
            self.AfterValidator(must_be_positive)
        )

        class Model(self.BaseModel):
            length: PositiveNumber[self.Dimension.length]

        # Valid: positive length
        m = Model(length={"quantity": 5, "unit": "m"})
        self.assertEqual(m.length.quantity, 5)

        # Invalid: negative length
        with self.assertRaises(self.ValidationError):
            Model(length={"quantity": -5, "unit": "m"})

        # Invalid: wrong dimension
        with self.assertRaises(self.ValidationError):
            Model(length={"quantity": 5, "unit": "kg"})


class TestPydanticJsonSchema(unittest.TestCase):
    """Test JSON schema generation."""

    @classmethod
    def setUpClass(cls):
        try:
            from pydantic import BaseModel
            from ucon.pydantic import Number
            from ucon.core import Dimension
            cls.BaseModel = BaseModel
            cls.Number = Number
            cls.Dimension = Dimension
            cls.skip_tests = False
        except ImportError:
            cls.skip_tests = True

    def setUp(self):
        if self.skip_tests:
            self.skipTest("pydantic not installed")

    def test_json_schema_with_dimension(self):
        """Test JSON schema includes dimension description."""
        class Model(self.BaseModel):
            length: self.Number[self.Dimension.length]

        schema = Model.model_json_schema()
        props = schema["properties"]["length"]
        self.assertIn("length", props.get("description", ""))


if __name__ == '__main__':
    unittest.main()
