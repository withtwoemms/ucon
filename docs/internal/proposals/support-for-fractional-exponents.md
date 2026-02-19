# Discrete vs Continuous `Exponent` Comparison

## Overview

This document compares the **discrete (integer-only)** `Exponent` implementation used in *ucon v0.3.2*
with the prospects of a new `Exponent` design that embraces fractional powers. It highlights how the
continuous model restores algebraic closure, improves precision, and simplifies higher-level `Scale`
operations.

---

## 1. Motivation

In *ucon v0.3.2*, `Exponent` was defined as an integer power over fixed bases (2 and 10).
This worked for standard prefixes like kilo or mebi but failed for mixed-base or non-integer scaling.

The continuous design instead treats `Exponent` as a **real-valued exponential** where a given exponent of base _b_ can be written in terms of another base, _a_:

$$
a^x \times b^y = a^{x + y \cdot \log_a(b)}
$$

This modification closes the algebra under all operations avoiding fallbacks or rounding while remaining fully compatible with integer-based scales.

---

## 2. Feature Comparison

| Property | Discrete Exponent | Continuous Exponent |
|-----------|------------------|---------------------|
| Power type | Integer | Float (real) |
| Closure | Partial | Complete |
| Mixed-base operations | Approximate or invalid | Exact |
| Reversibility (a×b)/b=a | Approximate | Exact |
| Fractional exponents | Not supported | Supported |
| Precision | Rounded to prefix | Full algebraic precision |
| Comparison | Magnitude-based | Power-difference-based |
| Scale interaction | Enum lookup | Continuous projection |

---

## 3. Example Comparisons

### Same-Base Operations

| Operation | Discrete | Continuous |
|------------|-----------|-------------|
| 10³ × 10² | `<10^5>` | `<10^5.00000>` |
| 2¹⁰ × 2⁵ | `<2^15>` | `<2^15.00000>` |

No change: _integer powers remain consistent._

### Mixed-Base Operations

| Operation | Discrete | Continuous |
|------------|-----------|-------------|
| 10³ × 2¹⁰ | `nearest(10⁶)` | `<10^6.01030>` |
| 2¹⁰ × 10³ | `nearest(2¹⁹)` | `<2^19.93157>` |
| 10⁶ ÷ 2¹⁰ | `nearest(10⁶)` | `<10^5.98970>` |

The continuous system captures **exact** mixed-base scaling.

---

## 4. Simplified Scale Operations

The continuous `Exponent` model greatly simplifies `Scale` arithmetic.

In v0.3.2, `Scale.__mul__` and `Scale.__truediv__` had to juggle base mismatches, lookups, and fallbacks.
Now, `Scale` can delegate directly to its underlying `Exponent`:

```python
def __mul__(self, other: 'Scale') -> 'Scale':
    result_exp = self.value * other.value  # exact Exponent
    return Scale.dynamic(result_exp)
```

No more `nearest()` logic, no more rounding errors.

### Before
```python
# had to guess nearest scale name
return Scale.nearest(float(result), include_binary=include_binary)
```

### After
```python
# exact algebraic scaling
return Scale.dynamic(self.value * other.value)
```

This removes three major branches of logic in the old implementation, simplifying the `Scale` layer to a thin symbolic wrapper around continuous exponents.

---

## 5. Conceptual Model

| Level | Entity | Description |
|--------|---------|-------------|
| 1 | **Exponent** | Continuous exponential algebra (base^power) |
| 2 | **Scale** | Human-readable projection onto named prefixes |
| 3 | **Number** | Quantified magnitude combining Scale and Unit |

With closure restored at the core, everything beyond it becomes simpler and more expressive.
`Scale` no longer needs lookup heuristics or error handling.
It can always delegate cleanly to algebraic truth.

---

## 6. Practical Outcomes

| Aspect | Benefit |
|---------|----------|
| Algebraic closure | No undefined or lossy operations |
| Extensibility | Future support for arbitrary user-defined bases |
| Precision | Exact mixed-base conversions (e.g. kilo × kibi) |
| Maintainability | Scale logic reduced to 1–2 lines |
| Mathematical integrity | Continuous and reversible model |

---

## 7. Example

```python
from ucon.core import Exponent

a = Exponent(10, 3)   # kilo
b = Exponent(2, 10)   # kibi

print(a * b)          # <10^6.01030>
print(a / b)          # <10^-0.01030>
print((a * b) / b)    # <10^3.00000>
```

Exact, reversible, and smooth: _no registry lookup or rounding required._

---

## 8. Closing Thoughts

This continuous approach:
- unifies all scaling operations algebraically,  
- removes arbitrary lookup logic from the `Scale` layer, and  
- lays the groundwork for reversibility across all scale relationships.
