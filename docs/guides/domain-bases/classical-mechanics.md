# Classical Mechanics Basis

## The Degeneracy Problem

Two classic pairs share SI dimensions:

| Pair | Shared Dimension | Hidden Qualifier |
|------|------------------|------------------|
| Torque vs Energy | ML²T⁻² | Angle (per radian) |
| Surface tension vs Spring constant | MT⁻² | Geometric character |

---

## Torque vs Energy

### The Degeneracy

| Quantity | SI Unit | SI Dimension |
|----------|---------|--------------|
| Energy | Joule (J) | ML²T⁻² |
| Torque | Newton-meter (N·m) | ML²T⁻² |

**Same dimension.** Yet:
- Energy is a scalar (state function)
- Torque is a pseudovector (force × lever arm × sin θ)
- Torque is energy *per unit angle*: τ = dW/dθ

### Extended Basis

```python
from ucon.basis import Basis, BasisComponent, Vector
from ucon.core import Dimension, Unit
from fractions import Fraction

MECHANICS = Basis("Mechanics", [
    BasisComponent("mass", "M"),       # 0
    BasisComponent("length", "L"),     # 1
    BasisComponent("time", "T"),       # 2
    BasisComponent("angle", "A"),      # 3 — the hidden qualifier
])
```

### Dimensional Vectors

| Quantity | Vector | Interpretation |
|----------|--------|----------------|
| Energy | M¹L²T⁻²A⁰ | Work done |
| Torque | M¹L²T⁻²A⁻¹ | Work per radian |
| Angle | M⁰L⁰T⁰A¹ | Rotation measure |
| Angular velocity | M⁰L⁰T⁻¹A¹ | Radians per second |
| Angular momentum | M¹L²T⁻¹A¹ | Rotational inertia × ω |

### Implementation

```python
# Dimensions
energy = Dimension(
    vector=Vector(MECHANICS, (1, 2, -2, 0)),
    name="energy"
)  # M¹L²T⁻²A⁰

torque = Dimension(
    vector=Vector(MECHANICS, (1, 2, -2, -1)),
    name="torque"
)  # M¹L²T⁻²A⁻¹

angle = Dimension(
    vector=Vector(MECHANICS, (0, 0, 0, 1)),
    name="angle"
)  # A¹

# Units
joule = Unit(name="joule", shorthand="J", dimension=energy)
newton_meter = Unit(name="newton_meter", shorthand="N·m", dimension=torque)
radian = Unit(name="radian", shorthand="rad", dimension=angle)
```

### Dimensional Algebra

**Torque × Angle = Energy:**
```
Work = τ × θ
M¹L²T⁻²A⁰ = (M¹L²T⁻²A⁻¹) × (A¹)  ✓
```

**Energy / Angle = Torque:**
```
τ = dW/dθ
M¹L²T⁻²A⁻¹ = (M¹L²T⁻²A⁰) / (A¹)  ✓
```

### Safety

```python
joule(100) + newton_meter(50)
# raises: incompatible dimensions (A⁰ vs A⁻¹)

# Correct: convert torque to energy via angle
work = newton_meter(50) * radian(2)  # → 100 J
```

---

## Surface Tension vs Spring Constant

### The Degeneracy

| Quantity | SI Unit | SI Dimension | Physical Meaning |
|----------|---------|--------------|------------------|
| Spring constant (k) | N/m | MT⁻² | Force per displacement (1D) |
| Surface tension (γ) | N/m | MT⁻² | Force per length along interface (2D) |

Both are N/m = kg/s², but:
- Spring constant: restoring force per unit *displacement*
- Surface tension: force per unit *length of edge* on a surface (or energy per area)

### Alternative View

| Quantity | Alternative Form | Shows |
|----------|------------------|-------|
| Spring constant | N/m | Force / length (1D linear) |
| Surface tension | J/m² | Energy / area (2D interfacial) |

J/m² = (kg·m²/s²)/m² = kg/s² = N/m — same dimension.

### Extended Basis

```python
MECHANICS_EXTENDED = Basis("Mechanics-Extended", [
    BasisComponent("mass", "M"),
    BasisComponent("length", "L"),
    BasisComponent("time", "T"),
    BasisComponent("angle", "A"),
    BasisComponent("interface", "I"),    # interfacial/surface character
])
```

### Dimensional Vectors

| Quantity | Vector | Interpretation |
|----------|--------|----------------|
| Spring constant | M¹L⁰T⁻²A⁰I⁰ | Linear restoring force |
| Surface tension | M¹L⁰T⁻²A⁰I¹ | Interfacial energy density |
| Interface factor | M⁰L⁰T⁰A⁰I¹ | Surface/interface qualifier |

### Implementation

```python
spring_constant_dim = Dimension(
    vector=Vector(MECHANICS_EXTENDED, (1, 0, -2, 0, 0)),
    name="spring_constant"
)  # M¹T⁻²I⁰

surface_tension_dim = Dimension(
    vector=Vector(MECHANICS_EXTENDED, (1, 0, -2, 0, 1)),
    name="surface_tension"
)  # M¹T⁻²I¹

# Units
newton_per_meter = Unit(
    name="newton_per_meter",
    shorthand="N/m",
    dimension=spring_constant_dim
)

joule_per_m2 = Unit(
    name="joule_per_square_meter",
    shorthand="J/m²",
    dimension=surface_tension_dim
)
```

### Physical Context

**Spring constant:**
- Hooke's law: F = -kx
- k has units N/m
- Describes 1D elastic deformation

**Surface tension:**
- Capillary force: F = γL (force along edge of length L)
- γ has units N/m or equivalently J/m²
- Describes 2D interfacial energy
- Examples: water-air (~72 mN/m), mercury-air (~486 mN/m)

### Why It Matters

In multiphysics simulations (e.g., microfluidics), both appear:

```python
# Droplet on a spring (hypothetical)
spring_force = k * displacement       # N
surface_force = gamma * perimeter     # N

# Without dimensional distinction:
total = k + gamma  # Dimensionally valid in SI, physically nonsense

# With extended basis:
total = k + gamma  # raises: incompatible (I⁰ vs I¹)
```

---

## Stiffness Variants

The spring constant degeneracy extends to other stiffness measures:

| Quantity | SI Dimension | Physical Context |
|----------|--------------|------------------|
| Spring constant | MT⁻² | Translational spring |
| Torsional stiffness | ML²T⁻²A⁻¹ | Rotational spring (torque per radian) |
| Bending stiffness (EI) | ML³T⁻² | Beam flexure |
| Surface tension | MT⁻² | Interface energy |

With the extended basis, all are distinct:

```python
# Torsional stiffness: torque per angle
torsional_stiffness = Dimension(
    vector=Vector(MECHANICS_EXTENDED, (1, 2, -2, -2, 0)),
    name="torsional_stiffness"
)  # M¹L²T⁻²A⁻² (N·m per radian)
```

---

## Projection to SI

When you need SI compatibility:

```python
MECHANICS_TO_SI = ConstantAwareBasisTransform(
    source=MECHANICS,
    target=SI,
    matrix=(
        (1, 0, 0, ...),  # M → M
        (0, 1, 0, ...),  # L → L
        (0, 0, 1, ...),  # T → T
        (0, 0, 0, ...),  # A → dimensionless (dropped)
    ),
    bindings=(
        ConstantBinding(
            source_component=MECHANICS["angle"],
            target_expression=Vector(SI, (0, 0, 0, ...)),  # dimensionless
            constant_symbol="rad",
            exponent=Fraction(1),
        ),
    ),
)
```

The binding records that angle was collapsed to dimensionless via the radian.

---

## Summary

| Degeneracy | Hidden Dimension | Resolution |
|------------|------------------|------------|
| Torque vs Energy | Angle (A) | Torque is M¹L²T⁻²A⁻¹ |
| Surface tension vs Spring constant | Interface (I) | Surface tension is M¹T⁻²I¹ |
| Torsional vs Linear stiffness | Angle (A) | Torsional is M¹L²T⁻²A⁻² |

All three are instances of the same pattern: a geometric qualifier (angle, interface) is treated as dimensionless in SI but carries physical meaning that affects how quantities combine.
