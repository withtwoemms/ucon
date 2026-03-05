# Clinical Chemistry Basis

## The Degeneracy Problem

Several clinically distinct quantities share SI dimensions:

| Pair | Shared Dimension | Risk |
|------|------------------|------|
| Molarity vs Osmolarity | mol/L (NL⁻³) | Fluid/electrolyte errors |
| Becquerel vs Hertz | s⁻¹ (T⁻¹) | Radiation vs frequency confusion |
| Specific activity (enzyme) vs Specific activity (radioactive) | mol/(s·kg) | Different meanings of "activity" |

---

## Molarity vs Osmolarity

Both express concentration, but they count different things:

| Quantity | Definition | Example |
|----------|------------|---------|
| Molarity | Moles of formula units per liter | 1 M NaCl = 1 mol NaCl/L |
| Osmolarity | Moles of osmotically active particles per liter | 1 M NaCl ≈ 2 Osm (Na⁺ + Cl⁻) |

**Clinical importance:** Plasma osmolarity (~285-295 mOsm/L) determines fluid shifts. Molarity alone doesn't capture dissociation.

### Extended Basis

```python
from ucon.basis import Basis, BasisComponent, Vector
from ucon.core import Dimension, Unit
from fractions import Fraction

CHEM = Basis("Chemistry", [
    BasisComponent("amount", "N"),            # 0 — moles
    BasisComponent("volume", "V"),            # 1 — liters
    BasisComponent("particle_semantics", "Π"), # 2 — dissociation factor
])

# Dimensions
molarity = Dimension(
    vector=Vector(CHEM, (1, -1, 0)),
    name="molarity"
)  # N¹V⁻¹Π⁰

osmolarity = Dimension(
    vector=Vector(CHEM, (1, -1, 1)),
    name="osmolarity"
)  # N¹V⁻¹Π¹

dissociation_factor = Dimension(
    vector=Vector(CHEM, (0, 0, 1)),
    name="dissociation_factor"
)  # Π¹ — i factor (van't Hoff)
```

### Van't Hoff Factor (i)

| Solute | i | Particles |
|--------|---|-----------|
| Glucose | 1 | Does not dissociate |
| NaCl | 2 | Na⁺ + Cl⁻ |
| CaCl₂ | 3 | Ca²⁺ + 2Cl⁻ |
| MgSO₄ | 2 | Mg²⁺ + SO₄²⁻ |

```python
# Conversion
nacl_molarity = molar(0.154)  # 0.154 M NaCl (normal saline)
nacl_osmolarity = nacl_molarity * van_hoff(2)  # ≈ 308 mOsm/L

# Dimensional algebra
# N¹V⁻¹Π¹ = (N¹V⁻¹Π⁰) × (Π¹)  ✓
```

---

## Becquerel vs Hertz

Both have dimension T⁻¹, but they measure fundamentally different phenomena:

| Unit | Measures | Definition |
|------|----------|------------|
| Hertz (Hz) | Oscillation frequency | Cycles per second |
| Becquerel (Bq) | Radioactive decay rate | Disintegrations per second |

**The problem:** 1 Hz ≠ 1 Bq, even though both are s⁻¹.

### Extended Basis

```python
TEMPORAL = Basis("Temporal", [
    BasisComponent("time", "T"),              # 0
    BasisComponent("event_type", "E"),        # 1 — oscillation vs decay
])

# Dimensions
frequency = Dimension(
    vector=Vector(TEMPORAL, (-1, 0)),
    name="frequency"
)  # T⁻¹E⁰

activity = Dimension(
    vector=Vector(TEMPORAL, (-1, 1)),
    name="radioactive_activity"
)  # T⁻¹E¹

# Units
hertz = Unit(name="hertz", shorthand="Hz", dimension=frequency)
becquerel = Unit(name="becquerel", shorthand="Bq", dimension=activity)

# Safety
hertz(1000) + becquerel(1000)
# raises: incompatible dimensions
```

---

## Enzyme Activity vs Radioactive Activity

Both can be expressed as "activity per mass" but mean different things:

| Quantity | Unit | Meaning |
|----------|------|---------|
| Enzyme specific activity | kat/kg (mol·s⁻¹·kg⁻¹) | Catalytic turnover per mass |
| Radioactive specific activity | Bq/kg (s⁻¹·kg⁻¹) | Decays per mass |

### Extended Basis

```python
ACTIVITY = Basis("Activity", [
    BasisComponent("time", "T"),
    BasisComponent("mass", "M"),
    BasisComponent("amount", "N"),            # moles (for enzyme)
    BasisComponent("activity_type", "A"),     # catalytic vs decay
])

# Enzyme specific activity: katal per kilogram
enzyme_specific = Dimension(
    vector=Vector(ACTIVITY, (-1, -1, 1, 0)),
    name="enzyme_specific_activity"
)  # T⁻¹M⁻¹N¹A⁰

# Radioactive specific activity: becquerel per kilogram
radio_specific = Dimension(
    vector=Vector(ACTIVITY, (-1, -1, 0, 1)),
    name="radioactive_specific_activity"
)  # T⁻¹M⁻¹N⁰A¹
```

---

## Concentration Units in Clinical Labs

Clinical laboratories use various concentration expressions:

| Unit | Dimension | Use Case |
|------|-----------|----------|
| mg/dL | M/L | Glucose (US), lipids |
| mmol/L | N/L | Glucose (international), electrolytes |
| mEq/L | N/L | Electrolytes with charge |
| mOsm/L | N/L with Π¹ | Osmolality calculations |
| IU/L | Activity/L | Enzyme assays |

**Problem:** mmol/L and mEq/L are dimensionally equivalent but semantically different (mEq accounts for ionic charge).

### Milliequivalents

```python
ELECTROLYTE = Basis("Electrolyte", [
    BasisComponent("amount", "N"),
    BasisComponent("volume", "V"),
    BasisComponent("charge", "Z"),            # ionic charge factor
])

millimolar = Dimension(
    vector=Vector(ELECTROLYTE, (1, -1, 0)),
    name="millimolar"
)  # N¹V⁻¹Z⁰

milliequivalent = Dimension(
    vector=Vector(ELECTROLYTE, (1, -1, 1)),
    name="milliequivalent"
)  # N¹V⁻¹Z¹
```

**Conversion:**
- For Na⁺ (charge +1): 140 mmol/L = 140 mEq/L
- For Ca²⁺ (charge +2): 2.5 mmol/L = 5 mEq/L
- For Mg²⁺ (charge +2): 1 mmol/L = 2 mEq/L

---

## Practical Example: Anion Gap

The anion gap calculation:

```
AG = [Na⁺] - [Cl⁻] - [HCO₃⁻]
```

All in mEq/L (charge-adjusted):

```python
sodium = meq_per_l(140)      # mEq/L
chloride = meq_per_l(104)    # mEq/L
bicarbonate = meq_per_l(24)  # mEq/L

anion_gap = sodium - chloride - bicarbonate  # 12 mEq/L

# Dimensional safety: can only subtract same dimensions
# N¹V⁻¹Z¹ - N¹V⁻¹Z¹ - N¹V⁻¹Z¹ = N¹V⁻¹Z¹  ✓
```

---

## Safety Guarantees

```python
# These are now caught:

molarity(0.154) + osmolarity(0.308)
# raises: incompatible (Π⁰ vs Π¹)

hertz(60) + becquerel(1000)
# raises: incompatible (E⁰ vs E¹)

mmol_per_l(140) + meq_per_l(140)
# raises: incompatible (Z⁰ vs Z¹)
# Even though numerically equal for Na⁺, must convert explicitly
```

---

## Clinical Decision Support

With proper dimensions, you can build safer lab systems:

```python
def calculate_osmolarity(
    sodium: Number,      # mmol/L
    glucose: Number,     # mmol/L
    urea: Number,        # mmol/L
) -> Number:
    """Calculate serum osmolarity using standard formula."""
    # 2*Na + glucose + urea
    # Each term must be converted to osmolarity (particle count)

    na_osm = sodium * van_hoff(2)        # ×2 for dissociation
    glucose_osm = glucose * van_hoff(1)  # ×1 (no dissociation)
    urea_osm = urea * van_hoff(1)        # ×1 (no dissociation)

    return na_osm + glucose_osm + urea_osm
    # Returns N¹V⁻¹Π¹ (osmolarity)
```

The dimensional system enforces that you can't forget the van't Hoff factor for sodium.
