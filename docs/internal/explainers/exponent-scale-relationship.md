# Developer Guide: Exponent and Scale Relationship

> Understanding the algebraic foundation of magnitude prefixes in ucon.

---

## Overview

The `Exponent` and `Scale` classes form the algebraic foundation for handling magnitude prefixes (kilo, milli, mebi, etc.) in ucon. This guide explains their relationship and how they work together.

```
┌─────────────────────────────────────────────────────────────┐
│                      Scale (Enum)                           │
│  kilo, milli, mega, kibi, mebi, etc.                       │
│                          │                                  │
│                          ▼                                  │
│              ScaleDescriptor (dataclass)                    │
│              shorthand: "k", alias: "kilo"                  │
│                          │                                  │
│                          ▼                                  │
│                 Exponent (class)                            │
│              base: 10, power: 3                             │
│              evaluated: 1000.0                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Exponent: The Algebraic Primitive

`Exponent` (`ucon.algebra`) represents a base-power pair like 10³ or 2¹⁰.

### Structure

```python
class Exponent:
    base: int   # 2 or 10 only
    power: int | float

    @property
    def evaluated(self) -> float:
        return self.base ** self.power
```

### Supported Bases

Only two bases are supported, chosen for their prevalence in scientific and computing contexts:

| Base | Use Case | Examples |
|------|----------|----------|
| **10** | SI prefixes (metric) | kilo (10³), milli (10⁻³), mega (10⁶) |
| **2** | Binary prefixes (IEC) | kibi (2¹⁰), mebi (2²⁰), gibi (2³⁰) |

### Arithmetic Operations

Exponent supports algebraic operations that mirror the rules of exponents:

```python
from ucon.algebra import Exponent

kilo = Exponent(10, 3)   # 10³ = 1000
milli = Exponent(10, -3) # 10⁻³ = 0.001

# Multiplication: add powers (same base)
kilo * milli  # → Exponent(10, 0) = 1

# Division: subtract powers (same base)
kilo / milli  # → Exponent(10, 6) = 1,000,000

# Exponentiation: multiply power
kilo ** 2     # → Exponent(10, 6) = 1,000,000

# Cross-base operations return float
kibi = Exponent(2, 10)  # 2¹⁰ = 1024
kilo / kibi   # → 0.9765625 (float, not Exponent)
```

### Base Conversion

Convert between bases while preserving numeric value:

```python
kibi = Exponent(2, 10)  # 1024
kibi.to_base(10)        # → Exponent(10, 3.0103...) ≈ 1024
```

---

## ScaleDescriptor: Adding Human-Readable Labels

`ScaleDescriptor` (`ucon.core`) wraps an `Exponent` with display information:

```python
@dataclass(frozen=True)
class ScaleDescriptor:
    exponent: Exponent
    shorthand: str  # "k", "M", "Ki"
    alias: str      # "kilo", "mega", "kibi"
```

### Properties

```python
desc = ScaleDescriptor(Exponent(10, 3), "k", "kilo")

desc.evaluated  # 1000.0 (delegates to exponent)
desc.base       # 10
desc.power      # 3
desc.parts()    # (10, 3)
```

---

## Scale: The User-Facing Enum

`Scale` (`ucon.core`) is an enum where each member's value is a `ScaleDescriptor`.

### Available Scales

```python
class Scale(Enum):
    # Binary (base 2)
    gibi  = ScaleDescriptor(Exponent(2, 30), "Gi", "gibi")  # 2³⁰
    mebi  = ScaleDescriptor(Exponent(2, 20), "Mi", "mebi")  # 2²⁰
    kibi  = ScaleDescriptor(Exponent(2, 10), "Ki", "kibi")  # 2¹⁰

    # Decimal (base 10)
    peta  = ScaleDescriptor(Exponent(10, 15), "P", "peta")
    tera  = ScaleDescriptor(Exponent(10, 12), "T", "tera")
    giga  = ScaleDescriptor(Exponent(10, 9),  "G", "giga")
    mega  = ScaleDescriptor(Exponent(10, 6),  "M", "mega")
    kilo  = ScaleDescriptor(Exponent(10, 3),  "k", "kilo")
    hecto = ScaleDescriptor(Exponent(10, 2),  "h", "hecto")
    deca  = ScaleDescriptor(Exponent(10, 1),  "da", "deca")
    one   = ScaleDescriptor(Exponent(10, 0),  "",  "")      # identity
    deci  = ScaleDescriptor(Exponent(10, -1), "d", "deci")
    centi = ScaleDescriptor(Exponent(10, -2), "c", "centi")
    milli = ScaleDescriptor(Exponent(10, -3), "m", "milli")
    micro = ScaleDescriptor(Exponent(10, -6), "µ", "micro")
    nano  = ScaleDescriptor(Exponent(10, -9), "n", "nano")
    pico  = ScaleDescriptor(Exponent(10, -12),"p", "pico")
    femto = ScaleDescriptor(Exponent(10, -15),"f", "femto")
```

### Scale Arithmetic

Scale operations delegate to Exponent arithmetic, then resolve back to a Scale:

```python
from ucon.core import Scale

# Multiplication
Scale.kilo * Scale.kilo   # → Scale.mega (10³ × 10³ = 10⁶)
Scale.kilo * Scale.milli  # → Scale.one  (10³ × 10⁻³ = 10⁰)

# Division
Scale.mega / Scale.kilo   # → Scale.kilo (10⁶ / 10³ = 10³)
Scale.kilo / Scale.mega   # → Scale.milli (10³ / 10⁶ = 10⁻³)

# Exponentiation
Scale.kilo ** 2           # → Scale.mega (10³)² = 10⁶
Scale.milli ** -1         # → Scale.kilo (10⁻³)⁻¹ = 10³
```

### Nearest Scale Resolution

When arithmetic produces a non-standard power, `Scale.nearest()` finds the closest match:

```python
# Non-exact result resolves to nearest scale
Scale.kilo * Scale.kibi   # Cross-base: 1000 × 1024 = 1,024,000
                          # → resolves to Scale.mega (closest)

# Manual nearest lookup
Scale.nearest(5000)       # → Scale.kilo (10³ = 1000 is closest)
Scale.nearest(500)        # → Scale.one (undershoot bias)
```

The `undershoot_bias` parameter (default 0.75) penalizes scales smaller than the value, preferring slight overestimation for cleaner display.

### Scale × Unit → UnitProduct

The primary use case: applying a scale to a unit:

```python
from ucon.core import Scale
from ucon import units

km = Scale.kilo * units.meter   # → UnitProduct with kilo-scaled meter
mg = Scale.milli * units.gram   # → UnitProduct with milli-scaled gram

print(km.shorthand)  # "km"
print(mg.shorthand)  # "mg"

# Used in Number construction
distance = km(5)     # 5 kilometers
mass = mg(250)       # 250 milligrams
```

---

## The Complete Stack

Here's how it all fits together:

```
User writes:          km = Scale.kilo * units.meter
                            │
                            ▼
Scale.kilo           ScaleDescriptor(Exponent(10, 3), "k", "kilo")
                            │
                            ▼
Scale.__mul__(Unit)  Returns UnitProduct({UnitFactor(meter, kilo): 1})
                            │
                            ▼
UnitProduct          Stores the unit with its scale prefix
                            │
                            ▼
Number(5, unit=km)   <5 km> with quantity=5, preserving "kilo" scale
```

---

## Key Design Decisions

### Why Separate Exponent from Scale?

1. **Algebraic Closure**: Exponent handles the pure math of base-power pairs without display concerns
2. **Cross-Base Operations**: 2¹⁰ / 10³ returns a float because no single base can represent it
3. **Nearest Resolution**: Scale can find the "closest" human-readable prefix for arbitrary values

### Why Only Base 2 and 10?

These are the only bases with standardized prefix names:
- **Base 10**: SI prefixes (kilo, mega, giga, etc.)
- **Base 2**: IEC binary prefixes (kibi, mebi, gibi, etc.)

Other bases would require inventing new prefix names.

### Why ScaleDescriptor?

Separates concerns:
- `Exponent`: Pure numeric computation
- `ScaleDescriptor`: Adds shorthand ("k") and alias ("kilo") for display
- `Scale`: Enum providing named access and class methods like `nearest()`

---

## Common Patterns

### Creating Scaled Units

```python
from ucon.core import Scale
from ucon import units

# Standard metric prefixes
km = Scale.kilo * units.meter
MHz = Scale.mega * units.hertz
ns = Scale.nano * units.second

# Binary prefixes (for information units)
KiB = Scale.kibi * units.byte
GiB = Scale.gibi * units.byte
```

### Scale Arithmetic in Practice

```python
# Velocity: km/h involves scale
km = Scale.kilo * units.meter
speed = (km / units.hour)(100)  # 100 km/h

# Energy: kJ
kJ = Scale.kilo * units.joule
energy = kJ(4.184)  # 4.184 kJ = 1 kcal
```

### Folding Scale into Quantity

```python
km = Scale.kilo * units.meter
distance = km(5)

# Get the scale factor
distance.unit.fold_scale()  # 1000.0

# Canonical magnitude (quantity × scale)
distance._canonical_magnitude  # 5000.0
```

---

## Testing Scale/Exponent Relationships

From `tests/ucon/test_core.py`:

```python
def test_scale_multiplication_same_base(self):
    self.assertEqual(Scale.kilo * Scale.kilo, Scale.mega)
    self.assertEqual(Scale.kilo * Scale.milli, Scale.one)

def test_scale_division(self):
    self.assertEqual(Scale.mega / Scale.kilo, Scale.kilo)
    self.assertEqual(Scale.kilo / Scale.mega, Scale.milli)

def test_scale_exponentiation(self):
    self.assertEqual(Scale.kilo ** 2, Scale.mega)
    self.assertEqual(Scale.milli ** -1, Scale.kilo)
```

From `tests/ucon/test_algebra.py`:

```python
def test_exponent_multiplication(self):
    kibibyte = Exponent(2, 10)
    mebibyte = Exponent(2, 20)
    product = kibibyte * mebibyte
    self.assertEqual(product.power, 30)  # 2³⁰

def test_exponent_division_same_base(self):
    thousand = Exponent(10, 3)
    thousandth = Exponent(10, -3)
    ratio = thousand / thousandth
    self.assertEqual(ratio.power, 6)  # 10⁶
```

---

## Summary

| Class | Module | Purpose |
|-------|--------|---------|
| `Exponent` | `ucon.algebra` | Base-power arithmetic (10³, 2¹⁰) |
| `ScaleDescriptor` | `ucon.core` | Wraps Exponent with shorthand/alias |
| `Scale` | `ucon.core` | Enum of named prefixes with algebra |

The relationship flows downward:
- `Scale.kilo` → `ScaleDescriptor` → `Exponent(10, 3)`

Arithmetic flows upward:
- `Exponent` math → resolve to `Scale` via lookup or `nearest()`

This layered design provides:
- **Type safety**: Scale operations return Scale, not raw numbers
- **Algebraic closure**: `kilo * kilo = mega`, not just `1000000`
- **Human readability**: Quantities display with appropriate prefixes
