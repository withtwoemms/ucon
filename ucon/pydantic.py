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

from typing import Annotated, Any

try:
    from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
    from pydantic.json_schema import JsonSchemaValue
    from pydantic_core import CoreSchema, core_schema
except ImportError as e:
    raise ImportError(
        "Pydantic v2 is required for ucon.pydantic. "
        "Install with: pip install ucon[pydantic]"
    ) from e

from ucon.core import Number as _Number
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


class _NumberPydanticAnnotation:
    """
    Pydantic annotation helper for ucon Number type.

    This class provides the schema generation hooks that Pydantic v2 needs
    to properly validate and serialize Number instances without introspecting
    the internal Unit/UnitProduct types.
    """

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        """
        Generate Pydantic core schema for Number validation/serialization.

        Uses no_info_plain_validator_function to bypass Pydantic's default
        introspection of the Number class fields.
        """
        return core_schema.no_info_plain_validator_function(
            _validate_number,
            serialization=core_schema.plain_serializer_function_ser_schema(
                _serialize_number,
                info_arg=False,
                return_schema=core_schema.dict_schema(),
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        _core_schema: CoreSchema,
        handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        """Generate JSON schema for OpenAPI documentation."""
        return {
            "type": "object",
            "properties": {
                "quantity": {"type": "number"},
                "unit": {"type": "string", "nullable": True},
                "uncertainty": {"type": "number", "nullable": True},
            },
            "required": ["quantity"],
        }


Number = Annotated[_Number, _NumberPydanticAnnotation]
"""
Pydantic-compatible Number type.

Use this as a type hint in Pydantic models to enable automatic validation
and JSON serialization of ucon Number instances.

Example::

    from pydantic import BaseModel
    from ucon.pydantic import Number

    class Measurement(BaseModel):
        value: Number

    # From dict
    m = Measurement(value={"quantity": 5, "unit": "m"})

    # From Number instance
    from ucon import units
    m2 = Measurement(value=units.meter(10))

    # Serialize to JSON
    print(m.model_dump_json())
"""

__all__ = ["Number"]
