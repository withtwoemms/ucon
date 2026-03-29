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

## Key Takeaways

1. **Basis points, percent, and fractions are the same dimension** --- ucon converts between them automatically
2. **Pseudo-dimensions isolate ratios from angles** --- 50 bp cannot become 50 rad
3. **Salary chains track units through each step** --- $/yr x yr/wk x wk/hr = $/hr
4. **Custom units extend the graph** --- currencies, day count conventions, and other financial units load via `define_unit`
5. **Both interfaces validate dimensions** --- ratio != time, ratio != angle
