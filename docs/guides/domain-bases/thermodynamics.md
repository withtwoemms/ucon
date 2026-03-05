# Thermodynamics Basis

## The Degeneracy Problem

Heat capacity and entropy share the same SI dimension:

| Quantity | SI Unit | SI Dimension | Physical Meaning |
|----------|---------|--------------|------------------|
| Heat capacity (C) | J/K | ML²T⁻²Θ⁻¹ | Energy required to raise temperature |
| Entropy (S) | J/K | ML²T⁻²Θ⁻¹ | Microstate counting / disorder |

**Same dimension. Different physics.**

- Heat capacity: dQ/dT — a process-dependent response function
- Entropy: ∫dQ_rev/T — a state function measuring disorder

---

## Conceptual Difference

### Heat Capacity

- **Question answered:** "How much energy to raise temperature by 1 K?"
- **Type:** Response function (can depend on process: C_p vs C_v)
- **Formula:** C = dQ/dT
- **Intensive form:** Specific heat c = C/m or molar heat C_m = C/n

### Entropy

- **Question answered:** "How many microstates correspond to this macrostate?"
- **Type:** State function (path-independent)
- **Formula:** S = k_B ln Ω (statistical), dS = dQ_rev/T (thermodynamic)
- **Intensive form:** Specific entropy s = S/m or molar entropy S_m = S/n

---

## Extended Basis

```python
from ucon.basis import Basis, BasisComponent, Vector
from ucon.core import Dimension, Unit
from fractions import Fraction

THERMO = Basis("Thermodynamics", [
    BasisComponent("mass", "M"),              # 0
    BasisComponent("length", "L"),            # 1
    BasisComponent("time", "T"),              # 2
    BasisComponent("temperature", "Θ"),       # 3
    BasisComponent("statistical", "Σ"),       # 4 — microstate/entropy character
])
```

---

## Dimensional Vectors

| Quantity | Vector | Interpretation |
|----------|--------|----------------|
| Energy | M¹L²T⁻²Θ⁰Σ⁰ | Mechanical/thermal energy |
| Heat capacity | M¹L²T⁻²Θ⁻¹Σ⁰ | Thermal response |
| Entropy | M¹L²T⁻²Θ⁻¹Σ¹ | Statistical/microstate measure |
| Boltzmann constant | M¹L²T⁻²Θ⁻¹Σ¹ | Entropy per microstate (k_B) |
| Temperature | M⁰L⁰T⁰Θ¹Σ⁰ | Thermal intensity |

---

## Implementation

```python
# Dimensions
energy = Dimension(
    vector=Vector(THERMO, (1, 2, -2, 0, 0)),
    name="energy"
)

heat_capacity = Dimension(
    vector=Vector(THERMO, (1, 2, -2, -1, 0)),
    name="heat_capacity"
)  # ML²T⁻²Θ⁻¹Σ⁰

entropy = Dimension(
    vector=Vector(THERMO, (1, 2, -2, -1, 1)),
    name="entropy"
)  # ML²T⁻²Θ⁻¹Σ¹

statistical_factor = Dimension(
    vector=Vector(THERMO, (0, 0, 0, 0, 1)),
    name="statistical_factor"
)  # Σ¹

# Units
joule_per_kelvin_heat = Unit(
    name="joule_per_kelvin_C",
    shorthand="J/K",
    dimension=heat_capacity
)

joule_per_kelvin_entropy = Unit(
    name="joule_per_kelvin_S",
    shorthand="J/K",
    dimension=entropy
)
```

---

## The Boltzmann Constant

k_B connects temperature to energy via entropy:

```
S = k_B ln Ω
```

In the extended basis, k_B has dimension Σ¹ — it's the bridge between statistical mechanics (microstates) and thermodynamics (temperature).

When we set k_B = 1 (natural units for statistical mechanics), we're collapsing the statistical dimension:

```python
# Forward: Σ¹ → dimensionless via k_B
# Inverse: dimensionless → Σ¹ by dividing by k_B
```

---

## Dimensional Algebra

**Heat absorbed from capacity:**
```
Q = C × ΔT
M¹L²T⁻²Θ⁰Σ⁰ = (M¹L²T⁻²Θ⁻¹Σ⁰) × (Θ¹)  ✓
```

**Entropy from heat (reversible):**
```
ΔS = Q_rev / T
M¹L²T⁻²Θ⁻¹Σ¹ = (M¹L²T⁻²Θ⁰Σ⁰) / (Θ¹) × (Σ¹)  ← needs statistical factor
```

Wait — this reveals something important. The formula dS = dQ/T doesn't automatically give you entropy's statistical character. The Σ¹ comes from the *definition* of entropy as a statistical quantity, not from the algebra.

This is analogous to torque vs energy: the angle factor comes from the physics (τ = dW/dθ), not from pure dimensional analysis.

---

## Related Degeneracies

### Specific Heat vs Specific Entropy

| Quantity | SI Dimension | Extended |
|----------|--------------|----------|
| Specific heat | L²T⁻²Θ⁻¹ | L²T⁻²Θ⁻¹Σ⁰ |
| Specific entropy | L²T⁻²Θ⁻¹ | L²T⁻²Θ⁻¹Σ¹ |

### Gas Constant vs Entropy

The gas constant R = 8.314 J/(mol·K) has the same dimension as molar entropy:

| Quantity | SI Dimension | Extended |
|----------|--------------|----------|
| Gas constant R | ML²T⁻²Θ⁻¹N⁻¹ | ML²T⁻²Θ⁻¹N⁻¹Σ⁰ |
| Molar entropy | ML²T⁻²Θ⁻¹N⁻¹ | ML²T⁻²Θ⁻¹N⁻¹Σ¹ |

R is a proportionality constant; molar entropy is a state function.

---

## Safety Guarantees

```python
# These are now caught:

heat_capacity_water + entropy_water
# raises: incompatible dimensions (Σ⁰ vs Σ¹)

# Must be explicit about what you're computing:
total_entropy = entropy_system + entropy_surroundings  # ✓ (both Σ¹)
total_capacity = C_water + C_container                 # ✓ (both Σ⁰)
```

---

## Free Energy Functions

The statistical dimension clarifies thermodynamic potentials:

| Potential | Definition | Entropy Term |
|-----------|------------|--------------|
| Internal energy U | — | No explicit S |
| Helmholtz F | U - TS | Contains Σ¹ via S |
| Gibbs G | H - TS | Contains Σ¹ via S |
| Enthalpy H | U + PV | No explicit S |

When computing G = H - TS:
- H has dimension M¹L²T⁻²Σ⁰ (energy)
- T has dimension Θ¹
- S has dimension M¹L²T⁻²Θ⁻¹Σ¹

```
TS: Θ¹ × M¹L²T⁻²Θ⁻¹Σ¹ = M¹L²T⁻²Σ¹
```

**Problem:** H (Σ⁰) and TS (Σ¹) have different dimensions!

**Resolution:** Gibbs energy inherits the statistical character:
```
G = H - TS  →  G has dimension M¹L²T⁻²Σ¹
```

Or we recognize that H implicitly carries Σ⁰ and the subtraction is valid only when we track that TS "converts" to pure energy via the temperature multiplication.

This is a deep point — the extended basis reveals that free energies are intrinsically statistical quantities, not pure mechanical energies.

---

## Practical Value

**Textbook sanity check:**

> "The entropy of the system increased by 50 J/K."
> "The heat capacity is 50 J/K."

In SI, these are dimensionally indistinguishable. In the extended basis:
- First statement: Σ¹ quantity changed
- Second statement: Σ⁰ property measured

**Simulation validation:**

In molecular dynamics, you compute entropy from microstate sampling (statistical) and heat capacity from energy fluctuations (thermodynamic response). Conflating them is a methodological error the extended basis can catch.

---

## Summary

| Degeneracy | Hidden Dimension | Resolution |
|------------|------------------|------------|
| Heat capacity vs Entropy | Statistical (Σ) | Entropy is ML²T⁻²Θ⁻¹Σ¹ |
| Gas constant vs Molar entropy | Statistical (Σ) | Molar entropy carries Σ¹ |
| Specific heat vs Specific entropy | Statistical (Σ) | Same pattern, intensive |

The statistical dimension captures whether a quantity describes:
- **Σ⁰**: Bulk thermal response (heat capacity, gas constant)
- **Σ¹**: Microstate counting (entropy, Boltzmann constant)
