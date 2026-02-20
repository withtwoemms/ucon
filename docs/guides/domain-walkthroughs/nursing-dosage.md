# Nursing Dosage Calculations

This walkthrough demonstrates dimensional analysis for medication dosing—a domain where unit errors can be fatal.

Each example shows two approaches:

- **Python API** — Direct use of ucon in your code
- **MCP Server** — Via AI agents like Claude

## Why Dimensional Analysis Matters

Medication errors kill thousands of patients annually. Common mistakes:

- Confusing mg with mcg (1000× error)
- Using lb instead of kg for weight-based dosing (2.2× error)
- Miscalculating IV drip rates

Dimensional analysis catches these errors by tracking units through every step.

---

## Weight-Based Dosing

**Problem:** A 154 lb patient needs a drug dosed at 15 mg/kg/day, given every 8 hours (3 doses/day). What's the dose per administration?

### Python API

```python
from ucon import units, Scale

mg = Scale.milli * units.gram
kg = Scale.kilo * units.gram

# Step 1: Convert weight
weight = units.pound(154).to(kg)
print(weight)  # <69.84... kg>

# Step 2: Calculate daily dose
daily_dose = mg(weight.quantity * 15)
print(daily_dose)  # <1047.6... mg>

# Step 3: Divide by doses per day
dose_per_admin = daily_dose.quantity / 3
print(f"{dose_per_admin:.1f} mg per dose")  # 349.2 mg per dose
```

### MCP Server

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

**Step trace:**

| Step | Factor | Dimension | Result |
|------|--------|-----------|--------|
| 0 | 154 lb | mass | 154 lb |
| 1 | × (1 kg / 2.205 lb) | mass | 69.84 kg |
| 2 | × (15 mg / kg·day) | mass/time | 1047.6 mg/day |
| 3 | × (1 day / 3 ea) | mass/count | **349.2 mg/ea** |

---

## IV Drip Rate Calculations

**Problem:** Infuse 1000 mL over 8 hours using a drip set that delivers 15 drops/mL. What's the drip rate in drops/minute?

### Python API

```python
from ucon import units, Scale, Dimension
from ucon.core import Unit

mL = Scale.milli * units.liter

# Define custom unit for drops (not in standard library)
drop = Unit("drop", "gtt", Dimension.count, aliases=("gtt", "drop"))

# Calculate
total_drops = 1000 * 15  # 1000 mL × 15 drops/mL
total_minutes = 8 * 60   # 8 hours × 60 min/hr
rate = total_drops / total_minutes

print(f"{rate:.1f} drops/min")  # 31.2 drops/min
```

### MCP Server

First, define the `drop` unit:

```python
define_unit(name="drop", dimension="count", aliases=["gtt", "drop"])
```

Then calculate:

```python
compute(
    initial_value=1000,
    initial_unit="mL",
    factors=[
        {"value": 15, "numerator": "drop", "denominator": "mL"},
        {"value": 1, "numerator": "1", "denominator": "8 hr"},
        {"value": 1, "numerator": "hr", "denominator": "60 min"},
    ]
)
```

**Result:** 31.25 drops/min (round to 31 gtt/min)

!!! note "Custom Units in MCP"
    The `drop` unit isn't in ucon's standard library. Use `define_unit` to register it for the session before calling `compute`.

---

## Concentration Conversions

**Problem:** A 1% solution means 1 g per 100 mL. Express this as mg/mL.

### Python API

```python
from ucon import units, Scale

mg = Scale.milli * units.gram
mL = Scale.milli * units.liter

# 1% = 1 g / 100 mL = 0.01 g/mL
concentration_g = units.gram(1) / mL(100)
print(concentration_g)  # <0.01 g/mL>

# Convert to mg/mL: 0.01 g = 10 mg
concentration_mg = mg(10) / mL(1)
print(concentration_mg)  # <10 mg/mL>
```

### MCP Server

```python
convert(value=1, from_unit="g/100mL", to_unit="mg/mL")
# → {"quantity": 10.0, "unit": "mg/mL", "dimension": "mass/volume"}
```

---

## Dimensional Safety

ucon prevents nonsensical conversions in both interfaces.

### Python API

```python
from ucon import units, Scale
from ucon.graph import ConversionNotFound

mg = Scale.milli * units.gram
mL = Scale.milli * units.liter

dose = mg(500)
try:
    dose.to(mL)  # mg → mL makes no sense!
except ConversionNotFound:
    print("Cannot convert mass to volume without concentration")
```

### MCP Server

```python
convert(value=500, from_unit="mg", to_unit="mL")
# → {
#     "error": "Dimension mismatch: mass ≠ volume",
#     "error_type": "dimension_mismatch",
#     "likely_fix": "Use a mass unit, or provide concentration to bridge mass↔volume"
# }
```

### Bridging Mass and Volume

You need concentration to convert between them:

```python
# Python API
concentration = (mg / mL)(10)  # 10 mg/mL
dose_mg = mg(500)
volume = dose_mg / concentration
print(volume)  # <50.0 mL>
```

---

## Full Example: Complex Dosing

**Problem:** A 68 kg patient needs vancomycin 15 mg/kg every 12 hours, diluted to a concentration of 5 mg/mL, infused over 60 minutes. Calculate:

1. Dose per administration (mg)
2. Volume of diluted solution (mL)
3. Infusion rate (mL/hr)

### Python API

```python
from ucon import units, Scale

mg = Scale.milli * units.gram
mL = Scale.milli * units.liter
kg = Scale.kilo * units.gram

# Given
weight = kg(68)
dose_rate = 15  # mg/kg
concentration = 5  # mg/mL
infusion_time = 1  # hour (60 minutes)

# 1. Dose calculation
dose = mg(weight.quantity * dose_rate)
print(f"Dose: {dose}")  # <1020 mg>

# 2. Volume calculation
volume = mL(dose.quantity / concentration)
print(f"Volume: {volume}")  # <204 mL>

# 3. Infusion rate
rate = volume.quantity / infusion_time
print(f"Rate: {rate} mL/hr")  # 204 mL/hr
```

### MCP Server

All three calculations in one chain:

```python
compute(
    initial_value=68,
    initial_unit="kg",
    factors=[
        {"value": 15, "numerator": "mg", "denominator": "kg"},
        {"value": 1, "numerator": "mL", "denominator": "5 mg"},
        {"value": 1, "numerator": "1", "denominator": "1 hr"},
    ]
)
```

**Step trace:**

| Step | Factor | Result |
|------|--------|--------|
| 0 | 68 kg | 68 kg |
| 1 | × (15 mg / kg) | 1020 mg |
| 2 | × (1 mL / 5 mg) | 204 mL |
| 3 | × (1 / 1 hr) | **204 mL/hr** |

---

## Key Takeaways

1. **Always track units** through every calculation step
2. **Both approaches validate dimensions** — errors are caught, not silently computed
3. **Mass ≠ Volume** — you need concentration to bridge them
4. **MCP step traces** provide an audit trail for AI-assisted calculations
5. **Python API** gives you full control for integration into applications
