# Scales & Prefixes

SI decimal and binary prefixes for unit scaling.

---

## SI Decimal Prefixes

Standard metric prefixes from peta (10^15) to femto (10^-15).

| Name | Prefix | Factor | Power |
|------|--------|--------|-------|
| peta | P | 1,000,000,000,000,000 | 10^15 |
| tera | T | 1,000,000,000,000 | 10^12 |
| giga | G | 1,000,000,000 | 10^9 |
| mega | M | 1,000,000 | 10^6 |
| kilo | k | 1,000 | 10^3 |
| hecto | h | 100 | 10^2 |
| deca | da | 10 | 10^1 |
| *(base)* | - | 1 | 10^0 |
| deci | d | 0.1 | 10^-1 |
| centi | c | 0.01 | 10^-2 |
| milli | m | 0.001 | 10^-3 |
| micro | u | 0.000001 | 10^-6 |
| nano | n | 0.000000001 | 10^-9 |
| pico | p | 0.000000000001 | 10^-12 |
| femto | f | 0.000000000000001 | 10^-15 |

---

## Binary Prefixes (IEC)

For information units (bits, bytes). These use powers of 2.

| Name | Prefix | Factor | Power |
|------|--------|--------|-------|
| gibi | Gi | 1,073,741,824 | 2^30 |
| mebi | Mi | 1,048,576 | 2^20 |
| kibi | Ki | 1,024 | 2^10 |

---

## Usage

### Python API

```python
from ucon import units, Scale

# Apply scale prefix to unit
km = Scale.kilo * units.meter
mg = Scale.milli * units.gram
uA = Scale.micro * units.ampere

# Create scaled values
distance = km(5)        # <5 km>
dose = mg(250)          # <250 mg>

# Binary prefixes for information
GiB = Scale.gibi * units.byte
storage = GiB(16)       # <16 GiB>
```

### Parsing Scaled Units

ucon parses scaled unit strings automatically:

```python
from ucon.units import get_unit_by_name

# Returns UnitProduct with scale applied
km = get_unit_by_name("km")      # kilo * meter
mL = get_unit_by_name("mL")      # milli * liter
MHz = get_unit_by_name("MHz")    # mega * hertz
KiB = get_unit_by_name("KiB")    # kibi * byte
```

---

## Scalable Units

Not all units accept scale prefixes. These are the scalable base units:

**SI Base:**
- meter, gram, second, ampere, kelvin, mole, candela

**SI Derived:**
- hertz, newton, pascal, joule, watt, coulomb, volt
- farad, ohm, siemens, weber, tesla, henry, lumen
- lux, becquerel, gray, sievert, katal

**Other:**
- liter, byte

---

## Scale Arithmetic

Scales compose when multiplying/dividing units:

```python
from ucon import units, Scale

# Scale * Scale
Scale.kilo * Scale.milli  # → Scale.one (10^3 * 10^-3 = 10^0)

# Scale * Unit → UnitProduct
mg = Scale.milli * units.gram

# Scales in expressions
mg_per_kg = mg / (Scale.kilo * units.gram)  # mg/kg
```

---

## Unicode Support

Both ASCII and Unicode scale prefixes are accepted in parsing:

| Scale | ASCII | Unicode |
|-------|-------|---------|
| micro | u | (U+00B5) or (U+03BC) |

```python
# All equivalent
get_unit_by_name("ug")   # ASCII 'u'
get_unit_by_name("g")   # Unicode micro sign
get_unit_by_name("g")   # Unicode mu
```

---

## SI vs Binary: A Note on Bytes

The distinction matters for storage:

| Notation | Meaning | Bytes |
|----------|---------|-------|
| kB | kilobyte (SI) | 1,000 |
| KiB | kibibyte (IEC) | 1,024 |
| MB | megabyte (SI) | 1,000,000 |
| MiB | mebibyte (IEC) | 1,048,576 |
| GB | gigabyte (SI) | 1,000,000,000 |
| GiB | gibibyte (IEC) | 1,073,741,824 |

ucon supports both conventions:

```python
# SI (decimal)
kB = Scale.kilo * units.byte   # 1000 bytes

# IEC (binary)
KiB = Scale.kibi * units.byte  # 1024 bytes
```
