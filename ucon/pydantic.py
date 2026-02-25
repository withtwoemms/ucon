# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
ucon.pydantic
=============

Pydantic v2 integration for ucon.

Provides type-annotated wrappers for use in Pydantic models with full
JSON serialization support.

Usage
-----
>>> from pydantic import BaseModel
>>> from ucon.pydantic import Number
>>>
>>> class Measurement(BaseModel):
...     value: Number
...
>>> m = Measurement(value={"quantity": 5, "unit": "km"})
>>> print(m.value)
<5 km>
>>> print(m.model_dump_json())
{"value": {"quantity": 5.0, "unit": "km", "uncertainty": null}}

Installation
------------
Requires Pydantic v2. Install with::

    pip install ucon[pydantic]

"""

import sys
from typing import Annotated, Any, Generic, Optional, TypeVar

try:
    from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
    from pydantic.json_schema import JsonSchemaValue
    from pydantic_core import CoreSchema, core_schema
except ImportError as e:
    raise ImportError(
        "Pydantic v2 is required for ucon.pydantic. "
        "Install with: pip install ucon[pydantic]"
    ) from e

from ucon.core import Dimension, Number as _Number
from ucon.units import UnknownUnitError, get_unit_by_name


def _validate_number(v: Any) -> _Number:
    """
    Validate and convert input to Number.

    Accepts:
    - Number instance (passthrough)
    - dict with 'quantity' and optional 'unit', 'uncertainty'

    Raises:
        ValueError: If input cannot be converted to Number.
    """
    if isinstance(v, _Number):
        return v

    if isinstance(v, dict):
        quantity = v.get("quantity")
        if quantity is None:
            raise ValueError("Number dict must have 'quantity' field")

        unit_str = v.get("unit")
        uncertainty = v.get("uncertainty")

        # Parse unit if provided
        if unit_str:
            try:
                unit = get_unit_by_name(unit_str)
            except UnknownUnitError as e:
                raise ValueError(f"Unknown unit: {unit_str!r}") from e
        else:
            unit = None

        return _Number(
            quantity=quantity,
            unit=unit,
            uncertainty=uncertainty,
        )

    raise ValueError(
        f"Cannot parse Number from {type(v).__name__}. "
        "Expected Number instance or dict with 'quantity' field."
    )


def _serialize_number(n: _Number) -> dict:
    """
    Serialize Number to JSON-compatible dict.

    Output format::

        {
            "quantity": <float>,
            "unit": <str | null>,
            "uncertainty": <float | null>
        }
    """
    # Get unit shorthand
    if n.unit is None:
        unit_str = None
    elif hasattr(n.unit, 'shorthand'):
        unit_str = n.unit.shorthand
        # Empty shorthand means dimensionless
        if unit_str == "":
            unit_str = None
    else:
        unit_str = None

    return {
        "quantity": float(n.quantity),
        "unit": unit_str,
        "uncertainty": float(n.uncertainty) if n.uncertainty is not None else None,
    }


def _make_dimension_validator(dimension: Dimension):
    """Create a validator function for a specific dimension."""
    def validate_dimension(n: _Number) -> _Number:
        actual_dim = n.unit.dimension if n.unit else Dimension.none
        if actual_dim != dimension:
            raise ValueError(
                f"expected dimension '{dimension.name}', got '{actual_dim.name}'"
            )
        return n
    return validate_dimension


class _NumberPydanticAnnotation:
    """
    Pydantic annotation helper for ucon Number type.

    This class provides the schema generation hooks that Pydantic v2 needs
    to properly validate and serialize Number instances without introspecting
    the internal Unit/UnitProduct types.
    """

    dimension: Optional[Dimension] = None

    def __init__(self, dimension: Optional[Dimension] = None):
        self.dimension = dimension

    def __get_pydantic_core_schema__(
        self,
        _source_type: Any,
        _handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        """
        Generate Pydantic core schema for Number validation/serialization.

        Uses no_info_plain_validator_function to bypass Pydantic's default
        introspection of the Number class fields.
        """
        if self.dimension is not None:
            # Chain dimension validation after number parsing
            dim_validator = _make_dimension_validator(self.dimension)
            def validate_with_dimension(v: Any) -> _Number:
                n = _validate_number(v)
                return dim_validator(n)
            validator = validate_with_dimension
        else:
            validator = _validate_number

        return core_schema.no_info_plain_validator_function(
            validator,
            serialization=core_schema.plain_serializer_function_ser_schema(
                _serialize_number,
                info_arg=False,
                return_schema=core_schema.dict_schema(),
            ),
        )

    def __get_pydantic_json_schema__(
        self,
        _core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        """Generate JSON schema for OpenAPI documentation."""
        schema = {
            "type": "object",
            "properties": {
                "quantity": {"type": "number"},
                "unit": {"type": "string", "nullable": True},
                "uncertainty": {"type": "number", "nullable": True},
            },
            "required": ["quantity"],
        }
        if self.dimension is not None:
            schema["description"] = f"Number with dimension '{self.dimension.name}'"
        return schema


class _NumberType:
    """
    Subscriptable Number type for Pydantic models.

    Supports both unconstrained and dimension-constrained usage:

        value: Number                    # Any dimension
        length: Number[Dimension.length] # Must be length dimension

    When subscripted with a Dimension, validation will fail if the
    parsed Number has a different dimension.
    """
    _extra_validators: tuple = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Subclasses can add validators

    @classmethod
    def __class_getitem__(cls, dimension: Dimension) -> type:
        """Return an Annotated type with dimension validation."""
        if not isinstance(dimension, Dimension):
            raise TypeError(
                f"Number[...] requires a Dimension, got {type(dimension).__name__}"
            )
        # Build the Annotated type with base annotation + extra validators
        annotations = [_NumberPydanticAnnotation(dimension)] + list(cls._extra_validators)
        if sys.version_info >= (3, 11):
            # Python 3.11+ supports unpacking in Annotated[...]
            return Annotated[_Number, *annotations]
        else:
            # Python 3.9-3.10: use __class_getitem__ directly
            return Annotated.__class_getitem__((_Number,) + tuple(annotations))

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        """
        Generate Pydantic core schema when Number is used without subscript.

        This allows both:
            value: Number                    # Any dimension
            length: Number[Dimension.length] # Constrained dimension
        """
        annotation = _NumberPydanticAnnotation()
        return annotation.__get_pydantic_core_schema__(_source_type, _handler)


def constrained_number(*validators):
    """
    Factory to create subscriptable Number types with additional validators.

    Usage::

        from pydantic.functional_validators import AfterValidator

        def must_be_positive(n):
            if n.quantity <= 0:
                raise ValueError("must be positive")
            return n

        PositiveNumber = constrained_number(AfterValidator(must_be_positive))

        class Model(BaseModel):
            value: PositiveNumber[Dimension.time]  # positive time value
    """
    class ConstrainedNumber(_NumberType):
        _extra_validators = validators
    return ConstrainedNumber


# Export Number as the subscriptable type
Number = _NumberType
"""
Pydantic-compatible Number type with optional dimension constraints.

Use this as a type hint in Pydantic models to enable automatic validation
and JSON serialization of ucon Number instances.

Basic usage (any dimension)::

    from pydantic import BaseModel
    from ucon.pydantic import Number

    class Measurement(BaseModel):
        value: Number

    m = Measurement(value={"quantity": 5, "unit": "km"})
    print(m.value)  # <5 km>

With dimension constraint::

    from ucon import Dimension
    from ucon.pydantic import Number

    class Vehicle(BaseModel):
        mass: Number[Dimension.mass]
        speed: Number[Dimension.velocity]

    # Valid
    v = Vehicle(
        mass={"quantity": 1500, "unit": "kg"},
        speed={"quantity": 100, "unit": "km/h"}
    )

    # Invalid - wrong dimension
    Vehicle(
        mass={"quantity": 5, "unit": "m"},  # ValueError: expected 'mass', got 'length'
        speed={"quantity": 100, "unit": "km/h"}
    )

From Number instance::

    from ucon import units
    m2 = Measurement(value=units.meter(10))

Serialize to JSON::

    print(m.model_dump_json())
    # {"value": {"quantity": 5.0, "unit": "km", "uncertainty": null}}
"""

__all__ = ["Number", "constrained_number"]
