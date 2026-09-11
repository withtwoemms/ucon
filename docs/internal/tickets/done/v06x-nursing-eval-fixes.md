# Ticket: Nursing Eval Fixes

**Priority:** High
**Theme:** Medical/clinical domain support
**Version:** v0.6.x
**Source:** `docs/evals/nurse-dosages.eval.md` results

---

## Summary

Address 5 bugs found during nursing dosage eval (16/19 passing). Critical for medical applications where unit notation conventions differ from SI.

---

## Bugs Found

| Issue | Severity | Current | Expected |
|-------|----------|---------|----------|
| `min` → milli-inch | **Critical** | `m` + `in` = length | `minute` = time |
| `mcg` not recognized | High | `UnknownUnitError` | microgram alias |
| Parenthetical grouping | Medium | `µg/(kg*min)` fails | Parse as `µg/(kg·min)` |
| Chained division | Medium | `mg/kg/d` fails | Parse as `mg/(kg·d)` |
| Ratio unit output | Low | `mg/kg → µg/kg` = `100` | `100 µg/kg` |

---

## Bug 1: `min` Parses as Milli-Inch (Critical)

### Problem

```python
get_unit_by_name("min")
# Returns: Scale.milli * inch (length)
# Expected: minute (time)
```

The parser greedily splits `min` as `m` (milli) + `in` (inch).

### Solution

Add `min` as alias for `minute` and prioritize exact alias matches over scale+unit decomposition in `get_unit_by_name()`.

```python
# In ucon/units.py
minute = Unit(
    name='minute',
    dimension=Dimension.time,
    shorthand='min',  # Change from 'minute' to 'min'
    aliases=('min', 'minutes'),
)
```

```python
# In get_unit_by_name() - check aliases BEFORE scale decomposition
def get_unit_by_name(name: str) -> Unit | UnitProduct:
    # 1. Exact unit name match
    # 2. Exact alias match  <-- NEW: check this before scale parsing
    # 3. Scale + unit decomposition
    # 4. Composite unit parsing
```

### Tests

```python
def test_min_is_minute_not_milli_inch():
    unit = get_unit_by_name("min")
    assert unit.dimension == Dimension.time

def test_mL_per_min():
    result = convert(120, "mL/h", "mL/min")
    assert result.quantity == 2.0
```

---

## Bug 2: `mcg` Not Recognized (High)

### Problem

Medical convention uses `mcg` for microgram (to avoid handwriting confusion with `mg`). Currently not supported.

### Solution

Add `mcg` as alias for microgram unit, or as recognized scale+gram combination.

```python
# Option A: Add to microgram aliases (if microgram exists as Unit)
microgram = Unit(
    name='microgram',
    dimension=Dimension.mass,
    shorthand='µg',
    aliases=('mcg', 'ug'),
)

# Option B: Handle in parser as special case
# "mcg" → Scale.micro * gram
```

### Tests

```python
def test_mcg_is_microgram():
    unit = get_unit_by_name("mcg")
    assert unit.dimension == Dimension.mass
    # Check scale factor equals micro

def test_mcg_to_mg():
    result = convert(500, "mcg", "mg")
    assert result.quantity == 0.5
```

---

## Bug 3: Parenthetical Grouping (Medium)

### Problem

```python
get_unit_by_name("µg/(kg*min)")
# UnknownUnitError: Unknown unit: '(kg'
```

Parser doesn't handle parentheses for grouping denominators.

### Solution

Enhance `get_unit_by_name()` to:
1. Detect parentheses
2. Parse inner expression recursively
3. Apply as grouped denominator

```python
# Parse: µg/(kg*min)
# Step 1: Split on `/` → ["µg", "(kg*min)"]
# Step 2: Detect parens, strip → "kg*min"
# Step 3: Parse inner → kg * min
# Step 4: Result → µg / (kg * min)
```

### Tests

```python
def test_parenthetical_denominator():
    unit = get_unit_by_name("µg/(kg*min)")
    # Should be µg·kg⁻¹·min⁻¹
    assert unit.dimension == Dimension.mass / Dimension.mass / Dimension.time
```

---

## Bug 4: Chained Division (Medium)

### Problem

```python
get_unit_by_name("mg/kg/d")
# UnknownUnitError: Unknown unit: 'kg/d'
```

Parser only handles single division.

### Solution

Parse chained divisions left-to-right:
- `a/b/c` → `(a/b)/c` → `a·b⁻¹·c⁻¹`

```python
# Parse: mg/kg/d
# Step 1: Split on `/` → ["mg", "kg", "d"]
# Step 2: First is numerator, rest are denominators
# Step 3: Result → mg·kg⁻¹·d⁻¹
```

### Tests

```python
def test_chained_division():
    unit = get_unit_by_name("mg/kg/d")
    # mg per kg per day
    assert "mass" in str(unit.dimension)  # mass/mass/time simplifies

def test_triple_division():
    unit = get_unit_by_name("µg/kg/min")
    result = convert(5, "µg/kg/min", "mg/kg/h")
    assert result.quantity == 0.3
```

---

## Bug 5: Ratio Unit Output (Low)

### Problem

```python
result = convert(0.1, "mg/kg", "µg/kg")
# Returns: quantity=100, unit="" (empty)
# Expected: quantity=100, unit="µg/kg"
```

When dimensions cancel (mass/mass = dimensionless), the unit string is lost even though the ratio semantics should be preserved.

### Analysis

This is in `Number.__truediv__` or unit simplification logic. When `mg/kg` converts to `µg/kg`, the mass dimensions cancel but the unit ratio should remain for display.

### Solution Options

1. **Preserve ratio units explicitly** - Don't simplify to dimensionless when both sides have same dimension but different scales
2. **Return the target unit string** - In MCP `convert()`, always return `to_unit` string for output

### Tests

```python
def test_ratio_unit_preserved():
    result = convert(0.1, "mg/kg", "µg/kg")
    assert result.unit == "µg/kg"
    assert result.quantity == 100
```

---

## Implementation Priority

| Bug | Fix Complexity | Impact | Order |
|-----|---------------|--------|-------|
| `min` alias | Low (alias + parser tweak) | Critical | 1 |
| `mcg` alias | Low (add alias) | High | 2 |
| Ratio unit output | Low (MCP response fix) | Low | 3 |
| Chained division | Medium (parser logic) | Medium | 4 |
| Parenthetical grouping | Medium (parser logic) | Medium | 5 |

---

## Acceptance Criteria

- [ ] `min` resolves to minute (time), not milli-inch
- [ ] `mcg` resolves to microgram
- [ ] `mg/kg → µg/kg` returns unit string `µg/kg`
- [ ] `mg/kg/d` parses as mass per mass per time
- [ ] `µg/(kg*min)` parses with grouped denominator
- [ ] All 19 nursing eval tests pass

---

## References

- Eval file: `docs/evals/nurse-dosages.eval.md`
- Unit parser: `ucon/units.py` (`get_unit_by_name`)
- MCP convert: `ucon/mcp/server.py`

---

## Closure Note (2026-07-12)

**Closed: done.** All five bugs verified fixed against v2.1.1:
- `min`/`mcg` resolve via priority aliases (`ucon/resolver.py` — see
  `register_priority_scaled_alias` and the priority-alias resolution order);
  `minute` carries the `min` alias in `comprehensive.ucon.toml`.
- Parenthetical grouping and chained division handled by the recursive
  descent parser (see `v06x-recursive-descent-parser.md`, Complete).
- Ratio-unit scale preserved via `UnitProduct.canonical_scale` (v2.0.0).
