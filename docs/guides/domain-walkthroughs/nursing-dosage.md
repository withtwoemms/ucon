# Nursing Dosage Calculations

This walkthrough demonstrates dimensional analysis for medication dosing—a domain where unit errors can be fatal.

## Why Dimensional Analysis Matters

Medication errors kill thousands of patients annually. Common mistakes:

- Confusing mg with mcg (1000× error)
- Using lb instead of kg for weight-based dosing (2.2× error)
- Miscalculating IV drip rates

Dimensional analysis catches these errors by tracking units through every step.

## Basic Conversions

### Mass Units

```python
from ucon import units, Scale

mg = Scale.milli * units.gram
mcg = Scale.micro * units.gram

# Convert 500 mcg to mg
dose = mcg(500)
print(dose.to(mg))  # <0.5 mg>
```

### Weight Conversion

```python
# Patient weight: 154 lb → kg
kilogram = Scale.kilo * units.gram
weight_lb = units.pound(154)
weight_kg = weight_lb.to(kilogram)
print(weight_kg)  # <69.85... kg>
```

## Weight-Based Dosing

**Problem:** A 154 lb patient needs a drug dosed at 15 mg/kg/day, given every 8 hours (3 doses/day). What's the dose per administration?

### Manual Calculation

```python
from ucon import units, Scale

mg = Scale.milli * units.gram
kg = Scale.kilo * units.gram

# Convert weight
weight = units.pound(154).to(kg)

# Calculate daily dose
daily_dose = weight.quantity * 15  # mg/day
dose_per_admin = daily_dose / 3    # mg per dose

print(f"{dose_per_admin:.1f} mg per dose")  # 349.2 mg per dose
```

### Using `compute`

The MCP `compute` tool tracks dimensions through each step:

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

1. `154 lb` → mass
2. `× (1 kg / 2.205 lb)` → mass (now in kg)
3. `× (15 mg / kg*day)` → mass/time
4. `× (1 day / 3 ea)` → mass/count

**Result:** 349.2 mg/dose

## IV Drip Rate Calculations

**Problem:** Infuse 1000 mL over 8 hours using a drip set that delivers 15 drops/mL. What's the drip rate in drops/minute?

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

## Concentration Conversions

**Problem:** A 1% solution means 1 g per 100 mL. Express this as mg/mL.

```python
from ucon import units, Scale

mg = Scale.milli * units.gram
mL = Scale.milli * units.liter

# 1% = 1 g / 100 mL
concentration = units.gram(1) / mL(100)
print(concentration)  # <0.01 g/mL>

# Convert g to mg: 0.01 g/mL = 10 mg/mL
# (1 g = 1000 mg, so 0.01 g = 10 mg)
```

## Dimensional Safety

ucon prevents nonsensical conversions:

```python
# This should fail: mg → mL makes no sense
mg = Scale.milli * units.gram
mL = Scale.milli * units.liter

dose = mg(500)
dose.to(mL)  # raises: ConversionNotFound
```

You need a concentration to bridge mass and volume:

```python
# With concentration: mg → mL
concentration = (mg / mL)(10)  # 10 mg/mL

dose_mg = mg(500)
volume = dose_mg / concentration
print(volume)  # <50.0 mL>
```

## Full Example: Complex Dosing

**Problem:** A 68 kg patient needs vancomycin 15 mg/kg every 12 hours, diluted in NS to a concentration of 5 mg/mL, infused over 60 minutes. Calculate:

1. Dose per administration (mg)
2. Volume of diluted solution (mL)
3. Infusion rate (mL/hr)

```python
from ucon import units, Scale

mg = Scale.milli * units.gram
mL = Scale.milli * units.liter

# 1. Dose calculation
weight_kg = 68
dose_rate = 15  # mg/kg
dose_mg = weight_kg * dose_rate
print(f"Dose: {dose_mg} mg")  # 1020 mg

# 2. Volume calculation
concentration = 5  # mg/mL
volume_mL = dose_mg / concentration
print(f"Volume: {volume_mL} mL")  # 204 mL

# 3. Infusion rate
infusion_time = 60  # minutes = 1 hour
rate_mL_hr = volume_mL / 1  # mL/hr
print(f"Rate: {rate_mL_hr} mL/hr")  # 204 mL/hr
```

With `compute`:

```python
compute(
    initial_value=68,
    initial_unit="kg",
    factors=[
        {"value": 15, "numerator": "mg", "denominator": "kg"},
    ]
)
# → 1020 mg per dose
```

## Key Takeaways

1. **Always track units** through every calculation step
2. **Use dimensional analysis** to catch errors before they reach patients
3. **Mass ≠ Volume** - you need concentration to convert between them
4. **The step trace** in `compute` provides an audit trail for verification
