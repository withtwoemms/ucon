# ADR-006: Pydantic Integration Pattern

**Status:** Accepted
**Date:** 2025-02-02
**Context:** v0.6.0 Pydantic + Serialization

## Context

ucon needs Pydantic v2 integration so users can include `Number` in Pydantic models for API validation and JSON serialization. The challenge is that `Number` contains fields of type `Unit | UnitProduct`, which are custom classes Pydantic doesn't know how to handle.

## Decision

Use an `Annotated` type alias with a custom annotation class that implements `__get_pydantic_core_schema__`:

```python
class _NumberPydanticAnnotation:
    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type, _handler):
        return core_schema.no_info_plain_validator_function(
            _validate_number,
            serialization=core_schema.plain_serializer_function_ser_schema(
                _serialize_number,
                info_arg=False,
                return_schema=core_schema.dict_schema(),
            ),
        )

Number = Annotated[_Number, _NumberPydanticAnnotation]
```

Users import from a separate module:
```python
from ucon.pydantic import Number
```

## Alternatives Considered

### 1. Simple `BeforeValidator` / `PlainSerializer`

```python
Number = Annotated[
    _Number,
    BeforeValidator(_validate_number),
    PlainSerializer(_serialize_number),
]
```

**Rejected because:** Pydantic still introspects `_Number`'s fields, encounters `Unit | UnitProduct`, and raises `PydanticSchemaGenerationError` asking for `arbitrary_types_allowed=True` or `__get_pydantic_core_schema__`.

### 2. Monkey-patch `__get_pydantic_core_schema__` onto `Number`

```python
# In ucon/pydantic.py
from ucon.core import Number
Number.__get_pydantic_core_schema__ = classmethod(_schema_fn)
```

**Rejected because:** Implicit mutation of core classes is surprising. Users who don't use Pydantic shouldn't have their classes modified.

### 3. Make `Number` inherit from `pydantic.BaseModel`

**Rejected because:**
- Forces Pydantic as a required dependency
- Changes the class hierarchy and behavior
- Breaks existing code that relies on `Number` being a dataclass

### 4. Use `arbitrary_types_allowed=True` in user models

```python
class Measurement(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    value: Number
```

**Rejected because:** Pushes complexity to users, loses JSON schema generation, and serialization still wouldn't work without custom serializers.

## Consequences

### Positive
- Pydantic remains a truly optional dependency
- Core classes unchanged; no import-time overhead when Pydantic unused
- Explicit opt-in via `from ucon.pydantic import Number`
- Full control over validation and serialization
- JSON schema generated for OpenAPI documentation

### Negative
- Users must import `Number` from `ucon.pydantic` instead of `ucon` when using Pydantic
- Two `Number` symbols exist (core and pydantic-wrapped), which could cause confusion
- Requires understanding Pydantic v2's schema generation internals

### Neutral
- Pattern is consistent with how other libraries (e.g., SQLAlchemy) handle Pydantic integration
