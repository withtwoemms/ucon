# Finance

This walkthrough demonstrates dimensional analysis for financial calculations---a domain where dimensionless ratios (basis points, percentages, fractions) and rate-time chains demand careful unit tracking.

Each example shows two approaches:

- **Python API** --- Direct use of ucon in your code
- **MCP Server** --- Via AI agents like Claude

## Why Dimensional Analysis Matters

Financial calculations routinely mix ratios expressed in different scales: a 50 basis point rate hike is 0.5%, which is 0.005 as a fraction. These are all the same quantity---just expressed in different units. Meanwhile, rates have time dimensions (per year, per month, per day) that must be tracked through every calculation step. Confusing an annual rate with a monthly rate is a 12x error.

---

## Ratio Isolation

**Problem:** Convert 50 basis points to percent and to a fractional value.

ucon models basis points, percent, permille, ppm, and fractions as units of the `RATIO` pseudo-dimension. They are mutually convertible but isolated from other dimensionless quantities like angles.

### Python API

```python
from ucon import units

# 50 basis points
rate = units.basis_point(50)

# Convert to percent
rate_pct = rate.to(units.percent)
print(rate_pct)  # <0.5 %>

# Convert to fraction
rate_frac = rate.to(units.fraction)
print(rate_frac)  # <0.005 frac>
```

### MCP Server

```python
convert(value=50, from_unit="bp", to_unit="%")
# -> {"quantity": 0.5, "unit": "%", "dimension": "ratio"}

convert(value=50, from_unit="bp", to_unit="fraction")
# -> {"quantity": 0.005, "unit": "fraction", "dimension": "ratio"}
```

### Pseudo-Dimension Safety

Basis points are *ratios*, not *angles*. ucon prevents the conversion:

```python
from ucon import units

rate = units.basis_point(50)
try:
    rate.to(units.radian)  # ratio -> angle is a dimension error
except Exception:
    print("Cannot convert ratio to angle --- different pseudo-dimensions")
```

```python
# MCP
convert(value=50, from_unit="bp", to_unit="rad")
# -> {
#     "error": "Dimension mismatch: ratio != angle",
#     "error_type": "dimension_mismatch"
# }
```

!!! note "Pseudo-Dimensions"
    Both `RATIO` and `ANGLE` are dimensionless in the SI sense (both have a zero exponent vector). ucon's pseudo-dimension mechanism gives them distinct identities so that basis points cannot accidentally become radians.

---

## Salary Chain

**Problem:** An employee earns $85,000 per year. What is the hourly rate, assuming 52 weeks/year and 40 hours/week?

### Python API

```python
from ucon import units, Scale

# Define a currency unit (not in standard library)
from ucon.core import Unit, Dimension

dollar = Unit(name="dollar", dimension=Dimension.count, aliases=("USD", "$"))

# Annual salary as a rate
annual = (dollar / units.day)(85_000 / 365.25)

# Build the chain manually: $/yr x yr/wk x wk/hr
yearly_salary = dollar(85_000)
weeks_per_year = units.each(52)
hours_per_week = units.each(40)

hourly = yearly_salary / weeks_per_year / hours_per_week
print(f"${hourly.quantity:.2f}/hr")  # $40.87/hr
```

### MCP Server

```python
define_unit(name="dollar", dimension="count", aliases=["USD", "$"])

compute(
    initial_value=85_000,
    initial_unit="dollar",
    factors=[
        {"value": 1, "numerator": "yr", "denominator": "52 wk"},
        {"value": 1, "numerator": "wk", "denominator": "40 hr"},
    ],
    custom_units=[
        {"name": "dollar", "dimension": "count", "aliases": ["USD", "$"]},
    ]
)
```

**Step trace:**

| Step | Factor | Dimension | Result |
|------|--------|-----------|--------|
| 0 | 85,000 dollar | count | 85,000 dollar |
| 1 | x (1 yr / 52 wk) | count/time | 1,634.6 dollar/wk |
| 2 | x (1 wk / 40 hr) | count/time | **40.87 dollar/hr** |

---

## Interest Rate Conversion

**Problem:** Convert a 5.25% annual percentage rate (APR) to a monthly rate and a daily rate.

### Python API

```python
from ucon import units

# APR as a ratio
apr = units.percent(5.25)
apr_frac = apr.to(units.fraction)
print(f"APR: {apr_frac.quantity}")  # 0.0525

# Simple division for nominal rates
monthly_rate = apr_frac.quantity / 12
daily_rate = apr_frac.quantity / 365

print(f"Monthly: {monthly_rate:.6f}")  # 0.004375
print(f"Daily:   {daily_rate:.6f}")    # 0.000144
```

### MCP Server

```python
# Convert APR to fraction, then divide
convert(value=5.25, from_unit="%", to_unit="fraction")
# -> {"quantity": 0.0525, "unit": "fraction", "dimension": "ratio"}

# Nominal monthly: 0.0525 / 12 = 0.004375
compute(
    initial_value=5.25,
    initial_unit="%",
    factors=[
        {"value": 1, "numerator": "fraction", "denominator": "100 %"},
        {"value": 1, "numerator": "yr", "denominator": "12 mo"},
    ]
)
```

!!! note "Nominal vs Effective Rates"
    Dividing an annual rate by 12 gives the *nominal* monthly rate. The *effective* monthly rate accounts for compounding: `(1 + r)^(1/12) - 1`. The compounding calculation is nonlinear and requires application-level logic beyond unit conversion.

---

## Dimensional Safety

### Rate Dimensions Are Not Interchangeable

```python
from ucon import units

# A percentage is a ratio, not a time
rate = units.percent(5.25)
try:
    rate.to(units.second)
except Exception:
    print("Cannot convert ratio to time --- different dimensions")
```

### MCP Server

```python
convert(value=5.25, from_unit="%", to_unit="s")
# -> {
#     "error": "Dimension mismatch: ratio != time",
#     "error_type": "dimension_mismatch"
# }
```

---

## Advanced: Currency as a Basis Extension

The salary chain above models `dollar` as `Dimension.count`. That works for
simple chains, but it's semantically wrong --- dollars are not counts of
discrete items. The defect surfaces when you try it:

```python
from ucon import units

dollar = Unit(name="dollar", dimension=Dimension.count, aliases=("USD",))

# This succeeds --- but it shouldn't:
dollar(100).to(units.each)   # <100 ea>  (dollars became "items")
dollar(50) + units.each(3)   # <53 USD>  (added money to a count)
```

The root cause is the same degeneracy pattern the
[Domain-Specific Bases](../domain-bases/index.md) guides address: two
physically distinct quantities (`currency` and `count`) share the same SI
dimension (dimensionless / pseudo-count). The fix is to extend the basis
with a `currency` component.

### Extended Basis

```python
from ucon.basis import Basis, BasisComponent, Vector
from ucon.core import Dimension, Unit
from fractions import Fraction

FINANCIAL = Basis("Financial", [
    BasisComponent("time", "T"),
    BasisComponent("count", "N"),
    BasisComponent("currency", "C"),   # the hidden qualifier
])
```

### Dimensional Vectors

| Quantity | Vector | Example Unit |
|----------|--------|--------------|
| Time | T¹N⁰C⁰ | hour, year |
| Count | T⁰N¹C⁰ | each, shares |
| Currency | T⁰N⁰C¹ | USD, EUR |
| Wage rate | T⁻¹N⁰C¹ | $/hr |
| Price per unit | T⁰N⁻¹C¹ | $/share |
| Count rate | T⁻¹N¹C⁰ | shares/day |

### Implementation

```python
# Dimensions
currency_dim = Dimension(
    vector=Vector(FINANCIAL, (0, 0, 1)),
    name="currency"
)  # C¹

count_dim = Dimension(
    vector=Vector(FINANCIAL, (0, 1, 0)),
    name="count"
)  # N¹

wage_rate_dim = Dimension(
    vector=Vector(FINANCIAL, (-1, 0, 1)),
    name="wage_rate"
)  # C¹T⁻¹

price_per_unit_dim = Dimension(
    vector=Vector(FINANCIAL, (0, -1, 1)),
    name="price_per_unit"
)  # C¹N⁻¹

# Units
dollar = Unit(name="dollar", shorthand="USD", dimension=currency_dim)
share  = Unit(name="share",  shorthand="sh",  dimension=count_dim)
```

### Safety

Currency and count are now structurally distinct:

```python
dollar(100) + share(5)
# raises: incompatible dimensions (C¹ vs N¹)

dollar(100).to(units.each)
# raises: no conversion path (currency ≠ count)
```

### Wage Rate Chain

The salary chain now carries proper dimensions through every step:

```python
from ucon import units as u

annual_salary = dollar(85_000)          # C¹
hours_per_year = u.hour(52 * 40)        # T¹

hourly_rate = annual_salary / hours_per_year
# dimension: C¹ / T¹ = C¹T⁻¹ (wage_rate)
print(f"${hourly_rate.quantity:.2f}/hr")  # $40.87/hr
```

Mixing in a count-rate by accident is caught:

```python
# Shares traded per day
trade_rate = share(1000) / u.day(1)     # N¹T⁻¹ (count_rate)

hourly_rate + trade_rate
# raises: incompatible dimensions (C¹T⁻¹ vs N¹T⁻¹)
```

### When This Matters

| Scenario | Without Basis Extension | With Basis Extension |
|----------|------------------------|----------------------|
| `dollar(100) + each(5)` | Silently succeeds (53) | Dimension error |
| `dollar(100).to(each)` | Converts to 100 ea | No conversion path |
| `$/hr + shares/day` | Same dimension (count/time) | Distinct (C¹T⁻¹ vs N¹T⁻¹) |
| Portfolio: `price * shares` | count² | C¹N¹ (market value × position size) |

For quick calculations where currency is the only non-SI quantity, the
`Dimension.count` hack is adequate. For systems that mix currencies, share
counts, and time-denominated rates in the same pipeline, the basis extension
prevents a class of errors that dimensional analysis alone cannot catch.

---

## Key Takeaways

1. **Basis points, percent, and fractions are the same dimension** --- ucon converts between them automatically
2. **Pseudo-dimensions isolate ratios from angles** --- 50 bp cannot become 50 rad
3. **Salary chains track units through each step** --- $/yr x yr/wk x wk/hr = $/hr
4. **Currency is not count** --- for pipelines mixing money, shares, and rates, a basis extension with a `currency` component prevents silent conflation
5. **Custom units extend the graph** --- currencies, day count conventions, and other financial units load via `define_unit`
6. **Both interfaces validate dimensions** --- ratio != time, ratio != angle
