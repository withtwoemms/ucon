# Recursive Descent Unit Parser

**As a** user entering unit strings with complex notation
**I want** parentheses, chained division, and nested expressions to parse correctly
**So I** can use standard engineering notation like `W/(m²*K)` and `mg/kg/d`

---

## Acceptance Criteria

- [x] GIVEN `get_unit_by_name("W/(m²*K)")`
      WHEN called
      THEN it must return a UnitProduct equivalent to W·m⁻²·K⁻¹.

- [x] GIVEN `get_unit_by_name("mol/(L*s)")`
      WHEN called
      THEN it must return a UnitProduct equivalent to mol·L⁻¹·s⁻¹.

- [x] GIVEN `get_unit_by_name("J/(mol*K)")`
      WHEN called
      THEN it must return a UnitProduct for molar heat capacity.

- [x] GIVEN `get_unit_by_name("mg/kg/d")`
      WHEN called (chained division)
      THEN it must return a UnitProduct with correct scale factor.
      **Note:** mg and kg cancel dimensionally (mass/mass), leaving 1/d with
      residual scale 1e-6 (milli/kilo). This is correct dimensional analysis.

- [x] GIVEN `get_unit_by_name("µg/kg/min")`
      WHEN called
      THEN it must return a UnitProduct with correct scale factor (1e-9).

- [x] GIVEN `get_unit_by_name("m/s²")` (Unicode superscript)
      WHEN called
      THEN it must return a UnitProduct with dimension acceleration.

- [x] GIVEN `get_unit_by_name("m/s^2")` (ASCII caret)
      WHEN called
      THEN it must return a UnitProduct identical to `m/s²`.

- [x] GIVEN `get_unit_by_name("s⁻¹")` (negative superscript)
      WHEN called
      THEN it must return a UnitProduct with dimension frequency.

- [x] GIVEN `get_unit_by_name("kg*m/s^2")`
      WHEN called
      THEN it must return a UnitProduct with dimension force.

- [x] GIVEN `get_unit_by_name("(kg*m)/(s^2)")`
      WHEN called (nested parentheses)
      THEN it must return a UnitProduct with dimension force.

- [x] GIVEN `get_unit_by_name("W/(m²*K")`
      WHEN called (unbalanced parentheses)
      THEN it must raise a ValueError with position information.

- [x] GIVEN `get_unit_by_name("m")` (simple unit)
      WHEN called
      THEN it must return `units.meter` (backward compatibility).

- [x] GIVEN `get_unit_by_name("kg")` (scaled unit)
      WHEN called
      THEN it must return `Scale.kilo * units.gram` (backward compatibility).

- [x] GIVEN `get_unit_by_name("min")`
      WHEN called
      THEN it must return minute (time), not milli-inch (priority alias).

---

## Implementation Notes

### Grammar

```
unit_expr  := term (('*' | '·' | '/' | '⋅') term)*
term       := factor ('^' exponent)?
factor     := '(' unit_expr ')' | scale_unit
scale_unit := SCALE? UNIT
exponent   := INTEGER | '-' INTEGER | '⁻'? SUPERSCRIPT+
```

### Precedence (highest to lowest)

1. Parentheses
2. Exponentiation (`^`, superscripts)
3. Multiplication/Division (left-to-right)

### Tokenizer

Produces tokens: `IDENT`, `NUMBER`, `MUL`, `DIV`, `POW`, `LPAREN`, `RPAREN`, `EOF`

Handles:
- Unicode operators: `·`, `⋅`, `×`
- Unicode superscripts: `⁰¹²³⁴⁵⁶⁷⁸⁹⁻`
- ASCII equivalents: `*`, `^`, `-`

### Parser

Recursive descent with methods:
- `_parse_expr()` — handles `*` and `/`
- `_parse_term()` — handles `^` exponents
- `_parse_factor()` — handles `()` and unit atoms
- `_parse_unit_atom()` — resolves IDENT to Unit/UnitProduct

### Resolution Order in `get_unit_by_name()`

1. Exact unit name match
2. Priority alias match (`min`, `mcg`)
3. Scale + unit decomposition (`km`, `mg`)
4. Full recursive descent parser (composite expressions)

### New File

`ucon/parsing.py` — Tokenizer and UnitParser classes

---

## Status

**Complete** (v0.6.x)

## Files Changed

- `ucon/parsing.py` — New file with `Tokenizer`, `UnitParser`, `ParseError`
- `ucon/units.py` — Updated `_parse_composite()` to use new parser
- `ucon/core.py` — Fixed residual scale preservation for nested UnitProducts
- `tests/ucon/test_unit_parsing.py` — Added `TestRecursiveDescentParser` class

---

## Closure Note (2026-07-12)

**Closed: done.** Ticket body already marked Complete (v0.6.x) with all
acceptance criteria checked. Parser now lives in `ucon/parsing/` after the
v2.0 restructuring.
