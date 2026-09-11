# Ticket: MCP Error Suggestions

**Priority:** High
**Theme:** Developer experience / AI agent integration
**Version:** v0.6.x
**Branch:** `ucon#XXX-mcp-error-suggestions`

---

## User Story

**As an** AI agent using ucon-MCP tools,
**I want** error responses to include actionable suggestions and readable dimension names,
**So that** I can self-correct my inputs and retry without human intervention.

---

## Acceptance Criteria

- [ ] `ConversionError` response model with `error` and `suggestions` fields
- [ ] `_suggest_units()` using `difflib.get_close_matches`
- [ ] `_suggest_compatible_units()` for dimension mismatch recovery
- [ ] `convert()` catches and wraps `UnknownUnitError`
- [ ] `convert()` catches and wraps `DimensionMismatch`
- [ ] `convert()` catches and wraps `ConversionNotFound`
- [ ] `check_dimensions()` tool catches and wraps `UnknownUnitError`
- [ ] Derived dimension names render as readable expressions (e.g., `length^3/time`)
- [ ] Tests for each error scenario
- [ ] Suggestions are concise and actionable

---

## Motivation

Currently, MCP tool errors bubble up as raw exceptions:
- `UnknownUnitError: 'meetr'` — No hint about typos
- `DimensionMismatch` — No guidance on compatible alternatives
- `ConversionNotFound` — No explanation of pseudo-dimension isolation

AI agents perform better when errors include recovery hints. This ticket is part of the **dimensional validation loop** (see `ucon_type-directed-correction-loop.svg`): the agent calls a tool, receives a structured error with suggestions, corrects its inputs, and retries.

---

## Current Behavior

```python
convert(100, "meetr", "ft")
# → raises UnknownUnitError: Unknown unit: 'meetr'

convert(100, "meter", "second")
# → raises DimensionMismatch: Cannot convert length to time

convert(1, "radian", "percent")
# → raises ConversionNotFound: No path from radian to percent

# Derived dimensions are unreadable:
# → "Cannot convert derived(Vector(T=Fraction(-1,1), L=Fraction(3,1), ...)) to mass"
```

---

## Proposed Behavior

```python
convert(100, "meetr", "ft")
# → ConversionError(
#     error="Unknown unit: 'meetr'",
#     suggestions=[
#       "Did you mean: meter, metre, m",
#       "For scaled units, try: km, mg, MHz (see list_scales for prefixes)",
#       "For composite units, try: m/s, kg*m/s^2"
#     ]
#   )

convert(100, "meter", "second")
# → ConversionError(
#     error="Cannot convert length to time",
#     suggestions=[
#       "'meter' is length, 'second' is time",
#       "Compatible targets for meter: ft, in, mi, km, yd",
#       "Use check_dimensions() to verify compatibility first"
#     ]
#   )

convert(1, "radian", "percent")
# → ConversionError(
#     error="No conversion path from 'radian' to 'percent'",
#     suggestions=[
#       "These units are in isolated pseudo-dimensions",
#       "radian is angle; percent is ratio",
#       "Pseudo-dimensions (angle, ratio, solid_angle) do not interconvert"
#     ]
#   )

# Derived dimensions are now readable:
# → "Cannot convert derived(length^3/time) to mass"
```

---

## Implementation

### New Response Model

```python
class ConversionError(BaseModel):
    """Error response with helpful suggestions."""
    error: str
    suggestions: list[str]
```

### Helper Functions

```python
from difflib import get_close_matches

def _suggest_units(bad_name: str) -> list[str]:
    """Suggest similar unit names using fuzzy matching."""
    all_names = _get_unit_names()
    return get_close_matches(bad_name, all_names, n=3, cutoff=0.5)

def _suggest_compatible_units(dimension: Dimension, limit: int = 5) -> list[str]:
    """Suggest units with the same dimension."""
    ...
```

### Error Handling in `convert()`

```python
@mcp.tool()
def convert(value: float, from_unit: str, to_unit: str) -> ConversionResult | ConversionError:
    try:
        src = get_unit_by_name(from_unit)
    except UnknownUnitError:
        return ConversionError(
            error=f"Unknown unit: '{from_unit}'",
            suggestions=_build_unknown_unit_suggestions(from_unit)
        )
    # ... similar for dst, DimensionMismatch, ConversionNotFound
```

---

## Suggestion Categories

| Error Type | Suggestions |
|------------|-------------|
| `UnknownUnitError` | Fuzzy matches, scale prefix hint, composite unit hint |
| `DimensionMismatch` | Dimension names (readable), compatible units for source, `check_dimensions()` hint |
| `ConversionNotFound` | Pseudo-dimension explanation, dimension names, isolation warning |

---

## Affected Tools

| Tool | Error Types |
|------|-------------|
| `convert` | `UnknownUnitError`, `DimensionMismatch`, `ConversionNotFound` |
| `check_dimensions` | `UnknownUnitError` |
| `list_units` | Invalid dimension filter (could warn with suggestions) |

---

## Testing

```python
def test_unknown_unit_suggests_similar():
    result = convert(100, "meetr", "ft")
    assert isinstance(result, ConversionError)
    assert "meter" in result.suggestions[0]

def test_dimension_mismatch_suggests_compatible():
    result = convert(100, "meter", "second")
    assert isinstance(result, ConversionError)
    assert "length" in result.error
    assert any("ft" in s for s in result.suggestions)

def test_pseudo_dimension_isolation_explained():
    result = convert(1, "radian", "percent")
    assert isinstance(result, ConversionError)
    assert "angle" in str(result.suggestions)
    assert "ratio" in str(result.suggestions)

def test_derived_dimension_readable_in_error():
    # m³/s to kg should show "derived(length^3/time)" not Vector dump
    result = convert(1, "m^3/s", "kg")
    assert "length" in result.error or "derived(length" in result.error
    assert "Vector" not in result.error
```

---

## Future Enhancement: Schema-Level Dimension Constraints

With `Number[Dimension]` generics and `DimConstraint`, MCP tool schemas could expose expected dimensions per parameter:

```json
{
  "name": "compute_fib4",
  "parameters": {
    "age": {
      "type": "Number",
      "dimension": "time",
      "description": "Patient age"
    },
    "ast": {
      "type": "Number",
      "dimension": "frequency",
      "description": "AST enzyme level (U/L)"
    }
  }
}
```

**Benefits:**
- Agents can validate inputs *before* calling the tool
- Reduces round-trips in the correction loop
- Tool descriptions become self-documenting
- IDE-like hints for MCP tool parameters

**Implementation path:**
1. MCP tool functions use `@enforce_dimensions` decorator internally
2. Schema generator introspects `DimConstraint` from type hints
3. Dimension names rendered using `_vector_to_dim_expr` for derived dimensions
4. MCP schema includes `dimension` field for constrained parameters

This is out of scope for the current ticket but enabled by the v0.6.x dimensional type safety work.

---

## Open Questions

1. **Return type union vs exception**: Should tools return `ConversionResult | ConversionError` or raise with structured error data? (Proposed: return union for MCP, raise for library)
2. **Suggestion limit**: How many suggestions per error? (Proposed: 3)
3. **Fuzzy match threshold**: `cutoff=0.5` may need tuning

---

## Dependencies

- **Derived dimension naming** — Required for readable error messages on composite/derived dimensions
- Python 3.9+

## Dependents

- AI agent correction loops
- Future schema-level dimension constraints

---

## References

- Correction loop diagram: `ucon_type-directed-correction-loop.svg`
- UX impact: `docs/ucon_ux-dx_new-feature-impact.md`
- MCP server: `ucon/mcp/server.py`
- Unit registry: `ucon/units.py`
- Exceptions: `ucon/graph.py`
