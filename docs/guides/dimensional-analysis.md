# Dimensional Analysis

Dimensional analysis (also called "factor-label" or "railroad track" method) is a systematic approach for unit conversions. ucon's `compute` tool automates this with dimensional validation at each step.

## The Method

Write conversion factors as fractions where units cancel:

```
 154 lb   |   1 kg    |  15 mg
---------x-----------x---------  = 1048 mg
    1     | 2.205 lb  |   kg
```

Units cancel: `lb` in numerator cancels with `lb` in denominator, `kg` cancels with `kg`, leaving `mg`.

## Using `compute`

The MCP server's `compute` tool automates this:

```python
compute(
    initial_value=154,
    initial_unit="lb",
    factors=[
        {"value": 1, "numerator": "kg", "denominator": "2.205 lb"},
        {"value": 15, "numerator": "mg", "denominator": "kg"},
    ]
)
```

**Result:**

```json
{
  "quantity": 1047.6,
  "unit": "mg",
  "dimension": "mass",
  "steps": [
    {"factor": "154 lb", "dimension": "mass", "unit": "lb"},
    {"factor": "× (1 kg / 2.205 lb)", "dimension": "mass", "unit": "kg"},
    {"factor": "× (15 mg / kg)", "dimension": "mass", "unit": "mg"}
  ]
}
```

## Anatomy of a Factor

Each factor has three parts:

| Field | Description | Example |
|-------|-------------|---------|
| `value` | Numeric coefficient (goes in numerator) | `15` |
| `numerator` | Unit string for the top | `"mg"` |
| `denominator` | Unit string for the bottom (can include number) | `"kg"` or `"2.205 lb"` |

The factor applies as: `result × (value × numerator / denominator)`

## Reading the Step Trace

The `steps` array shows dimensional consistency at each point:

1. **Start:** 154 lb (mass)
2. **After factor 1:** Still mass, but in kg
3. **After factor 2:** Still mass, now in mg

If dimensions don't track correctly, you've made an error.

## Example: Weight-Based Dosing

A 154 lb patient needs a drug dosed at 15 mg/kg/day, given in 3 doses:

```python
compute(
    initial_value=154,
    initial_unit="lb",
    factors=[
        {"value": 1, "numerator": "kg", "denominator": "2.205 lb"},
        {"value": 15, "numerator": "mg", "denominator": "kg*day"},
        {"value": 1, "numerator": "day", "denominator": "3 ea"},
    ]
)
```

**Result:** 349.2 mg/dose

The step trace shows:

1. 154 lb → mass
2. → 69.8 kg → mass
3. → 1048 mg/day → mass/time
4. → 349.2 mg/ea → mass/count

## Example: Unit Price Conversion

Convert $2.50/gallon to cents/liter:

```python
compute(
    initial_value=2.50,
    initial_unit="USD/gal",
    factors=[
        {"value": 100, "numerator": "cent", "denominator": "USD"},
        {"value": 1, "numerator": "gal", "denominator": "3.785 L"},
    ]
)
```

**Result:** 66.0 cents/L

## Error Handling

If a factor has wrong dimensions, `compute` returns an error with the failing step:

```python
compute(
    initial_value=100,
    initial_unit="m",
    factors=[
        {"value": 1, "numerator": "s", "denominator": "m"},  # Valid: m → m/s... wait
        {"value": 1, "numerator": "kg", "denominator": "s"},  # Nonsense!
    ]
)
```

The step trace helps identify where the calculation went wrong.

## Typo Recovery

If you misspell a unit:

```python
compute(
    initial_value=100,
    initial_unit="meter",
    factors=[
        {"value": 1, "numerator": "kilomter", "denominator": "1000 m"},  # typo!
    ]
)
```

**Error:**

```json
{
  "error": "Unknown unit: 'kilomter'",
  "error_type": "unknown_unit",
  "parameter": "factors[0].numerator",
  "step": 0,
  "likely_fix": "Did you mean 'kilometer'?"
}
```

## Tips

1. **Work left to right** - each factor should cancel one unit and introduce another
2. **Check the step trace** - dimensions should make physical sense at each point
3. **Use explicit denominators** - `"2.205 lb"` is clearer than computing the ratio separately
4. **Name composite units** - `"kg*day"` instead of separate factors when they belong together
