# Domain-Specific Bases

## The Problem: SI Degeneracies

The SI system has seven base dimensions (eight in ucon, including information). This is sufficient for dimensional analysis in most contexts, but it fails to distinguish physically or clinically distinct quantities that happen to share the same dimensional formula.

**Examples of degenerate pairs in SI:**

| Quantity A | Quantity B | Shared Dimension | Risk |
|------------|------------|------------------|------|
| Gray (absorbed dose) | Sievert (equivalent dose) | L²T⁻² | Radiation safety errors |
| Torque | Energy | ML²T⁻² | Mechanical analysis errors |
| Fentanyl (mg) | Morphine (mg) | M | Fatal dosing errors |
| Molarity | Osmolarity | NL⁻³ | Clinical chemistry errors |
| Heat capacity | Entropy | ML²T⁻²Θ⁻¹ | Thermodynamic confusion |

These aren't edge cases — they represent real sources of error in safety-critical domains.

---

## The Solution: Extended Bases

ucon allows you to define custom bases with additional dimensions that capture domain-specific semantics. When a "hidden qualifier" is promoted to a real basis component, degenerate quantities become structurally distinguishable.

**The pattern:**

1. Identify the degenerate pair
2. Find the hidden qualifier (what makes them physically different?)
3. Add that qualifier as a new basis component
4. Redefine dimensions with explicit exponents for the new component

---

## Domain Guides

| Domain | Degeneracies Addressed | Guide |
|--------|------------------------|-------|
| [Radiation Dosimetry](radiation-dosimetry.md) | Gy vs Sv vs Gy(RBE) vs effective dose | Extended dose basis |
| [Pharmacology](pharmacology.md) | Drug mass vs potency, IU variations | Potency-aware basis |
| [Clinical Chemistry](clinical-chemistry.md) | Molarity vs Osmolarity, Bq vs Hz | Particle semantics |
| [Classical Mechanics](classical-mechanics.md) | Torque vs energy, surface tension vs spring constant | Geometric qualifiers |
| [Thermodynamics](thermodynamics.md) | Heat capacity vs entropy | Statistical mechanics |

---

## General Approach

```python
from ucon.basis import Basis, BasisComponent, Vector
from ucon.core import Dimension, Unit
from fractions import Fraction

# 1. Define your extended basis
MY_DOMAIN = Basis("MyDomain", [
    BasisComponent("existing_dim_1", "X"),
    BasisComponent("existing_dim_2", "Y"),
    BasisComponent("hidden_qualifier", "Q"),  # NEW
])

# 2. Create dimensions with explicit Q exponents
quantity_a = Dimension(
    vector=Vector(MY_DOMAIN, (Fraction(1), Fraction(-1), Fraction(0))),
    name="quantity_a"
)  # X¹Y⁻¹Q⁰

quantity_b = Dimension(
    vector=Vector(MY_DOMAIN, (Fraction(1), Fraction(-1), Fraction(1))),
    name="quantity_b"
)  # X¹Y⁻¹Q¹ — now distinguishable!

# 3. Create units
unit_a = Unit(name="unit_a", dimension=quantity_a)
unit_b = Unit(name="unit_b", dimension=quantity_b)

# 4. Safety guaranteed
unit_a(1.0) + unit_b(1.0)  # raises: incompatible dimensions
```

---

## When to Use Extended Bases

**Use an extended basis when:**

- Two quantities have identical SI dimensions but different physical meaning
- Conflating them would be a safety or correctness error
- Domain experts treat them as fundamentally different
- You need to track a qualifier through calculations (not just label units)

**Don't use an extended basis when:**

- The distinction is purely notational (e.g., km vs m — same dimension, different scale)
- A pseudo-dimension suffices (e.g., radians vs pure ratio at the unit level)
- The overhead isn't justified for your use case

---

## Relationship to Pseudo-Dimensions

ucon also supports pseudo-dimensions for lighter-weight tagging:

```python
ANGLE = Dimension.pseudo("angle", name="angle", symbol="θ")
```

Pseudo-dimensions:
- Tag units without affecting dimensional algebra with real dimensions
- Prevent adding radians to pure ratios
- Don't survive into compound quantities (torque still equals energy)

Extended bases:
- Full dimensional tracking through all operations
- Torque ≠ energy even in derived quantities
- More overhead, more safety

Choose based on your needs.
