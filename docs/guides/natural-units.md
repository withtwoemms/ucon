# Natural Units Guide

This guide explains ucon's support for natural units, commonly used in particle physics and theoretical physics.

---

## What Are Natural Units?

Natural units simplify physical equations by setting certain fundamental constants to 1:

| Convention | Constants Set to 1 | Common Use |
|------------|-------------------|------------|
| **Particle Physics** | c, h_bar, k_B | High-energy physics |
| **Planck Units** | c, h_bar, G, k_B | Quantum gravity |
| **Stoney Units** | c, e, G, k_B | Historical |

In ucon's `NATURAL` basis (particle physics convention), setting **c = h_bar = k_B = 1** collapses length, time, mass, and temperature into expressions of a single dimension: **energy**.

---

## Key Consequences

### Velocity is Dimensionless

With c = 1, the speed of light is just the number 1. All velocities are expressed as fractions of c:

```python
from ucon import SI, NATURAL, SI_TO_NATURAL, BasisVector
from fractions import Fraction

# Velocity in SI: L^1 T^-1
si_velocity = BasisVector(SI, (
    Fraction(-1),  # T^-1
    Fraction(1),   # L^1
    Fraction(0), Fraction(0), Fraction(0),
    Fraction(0), Fraction(0), Fraction(0),
))

natural_velocity = SI_TO_NATURAL(si_velocity)
natural_velocity.is_dimensionless()  # True!
```

### Mass and Energy Share Dimension

With E = mc^2 and c = 1, mass **is** energy:

```python
# Mass in SI: M^1
si_mass = BasisVector(SI, (
    Fraction(0), Fraction(0), Fraction(1), Fraction(0),
    Fraction(0), Fraction(0), Fraction(0), Fraction(0),
))

natural_mass = SI_TO_NATURAL(si_mass)
natural_mass["E"]  # Fraction(1) - pure energy!
```

Particle physicists express masses in energy units: "The electron mass is 0.511 MeV."

### Action is Dimensionless

With h_bar = 1, action (energy x time) becomes dimensionless:

```python
# Action in SI: M^1 L^2 T^-1 (same as h_bar)
si_action = BasisVector(SI, (
    Fraction(-1),  # T^-1
    Fraction(2),   # L^2
    Fraction(1),   # M^1
    Fraction(0), Fraction(0),
    Fraction(0), Fraction(0), Fraction(0),
))

natural_action = SI_TO_NATURAL(si_action)
natural_action.is_dimensionless()  # True!
```

### Length and Time are Inverse Energy

Since L = h_bar*c/E and T = h_bar/E, both length and time scale as E^-1:

```python
# Length: L -> E^-1
# Time: T -> E^-1

# This means frequency (T^-1) has dimension E:
si_frequency = BasisVector(SI, (
    Fraction(-1), Fraction(0), Fraction(0), Fraction(0),
    Fraction(0), Fraction(0), Fraction(0), Fraction(0),
))
SI_TO_NATURAL(si_frequency)["E"]  # Fraction(1)
```

---

## The NATURAL Basis

ucon provides the `NATURAL` basis with a single component:

```python
from ucon import NATURAL

len(NATURAL)  # 1
NATURAL[0].name  # "energy"
NATURAL[0].symbol  # "E"
```

### Dimension Mapping Table

| SI Dimension | Natural | Physical Origin |
|--------------|---------|-----------------|
| Length (L) | E^-1 | L = h_bar*c / E |
| Time (T) | E^-1 | T = h_bar / E |
| Mass (M) | E^1 | E = mc^2 |
| Temperature (Theta) | E^1 | E = k_B*T |
| Current (I) | -- | Not representable |
| Luminous Int. (J) | -- | Not representable |
| Amount (N) | -- | Not representable |
| Information (B) | -- | Not representable |

---

## Using SI_TO_NATURAL

Transform SI dimensional vectors to natural units:

```python
from ucon import SI, SI_TO_NATURAL, BasisVector
from fractions import Fraction

# Energy in SI: M^1 L^2 T^-2
si_energy = BasisVector(SI, (
    Fraction(-2), Fraction(2), Fraction(1), Fraction(0),
    Fraction(0), Fraction(0), Fraction(0), Fraction(0),
))

natural_energy = SI_TO_NATURAL(si_energy)
print(f"Energy: E^{natural_energy['E']}")  # "Energy: E^1"
```

### Handling Electromagnetic Dimensions

Electromagnetic quantities (current, charge, etc.) are **not representable** in pure natural units. Attempting to transform them raises `LossyProjection`:

```python
from ucon import SI, SI_TO_NATURAL, BasisVector, LossyProjection
from fractions import Fraction

# Current: I^1
si_current = BasisVector(SI, (
    Fraction(0), Fraction(0), Fraction(0), Fraction(1),
    Fraction(0), Fraction(0), Fraction(0), Fraction(0),
))

# This raises LossyProjection
try:
    SI_TO_NATURAL(si_current)
except LossyProjection as e:
    print("Cannot transform current to natural units")
```

If you want to proceed anyway (projecting to zero):

```python
result = SI_TO_NATURAL(si_current, allow_projection=True)
result.is_dimensionless()  # True (current dimension is lost)
```

---

## Going Back: NATURAL_TO_SI

The inverse transform uses constant bindings to reverse the mapping:

```python
from ucon import NATURAL, NATURAL_TO_SI, BasisVector
from fractions import Fraction

# Energy in natural units
natural_energy = BasisVector(NATURAL, (Fraction(1),))

# Transform to SI representation
si_result = NATURAL_TO_SI(natural_energy)
print(si_result.basis.name)  # "SI"
```

Note: The inverse transform recovers the **primary** SI representation. Since mass, temperature, and energy all have E^1, the inverse picks one canonical form.

---

## Particle Physics Examples

### Cross-Section (Area)

Cross-sections are measured in units of area (L^2), which becomes E^-2 in natural units:

```python
si_cross_section = BasisVector(SI, (
    Fraction(0), Fraction(2), Fraction(0), Fraction(0),
    Fraction(0), Fraction(0), Fraction(0), Fraction(0),
))

natural_xs = SI_TO_NATURAL(si_cross_section)
print(f"Cross-section: E^{natural_xs['E']}")  # "E^-2"
```

In particle physics, cross-sections are often given in inverse GeV^2 (or barns).

### Decay Width

Decay widths have dimension of inverse time (T^-1), which is E in natural units:

```python
si_decay_width = BasisVector(SI, (
    Fraction(-1), Fraction(0), Fraction(0), Fraction(0),
    Fraction(0), Fraction(0), Fraction(0), Fraction(0),
))

natural_width = SI_TO_NATURAL(si_decay_width)
print(f"Decay width: E^{natural_width['E']}")  # "E^1"
```

Particle physicists express decay widths directly in energy units (MeV, GeV).

### Momentum

Momentum (M*L/T) has dimension E in natural units:

```python
si_momentum = BasisVector(SI, (
    Fraction(-1), Fraction(1), Fraction(1), Fraction(0),
    Fraction(0), Fraction(0), Fraction(0), Fraction(0),
))

natural_p = SI_TO_NATURAL(si_momentum)
print(f"Momentum: E^{natural_p['E']}")  # "E^1"
```

Hence "the proton momentum is 100 GeV" -- momentum and energy share units.

---

## Advanced: ConstantBinding

Under the hood, `SI_TO_NATURAL` uses `ConstantBinding` to record which constants relate each dimension:

```python
from ucon.bases import SI_TO_NATURAL

# The transform has 4 bindings (L, T, M, Theta)
len(SI_TO_NATURAL.bindings)  # 4

for binding in SI_TO_NATURAL.bindings:
    print(f"{binding.source_component.symbol} via {binding.constant_symbol}^{binding.exponent}")
```

These bindings enable the inverse transform to work despite the non-square (8x1) matrix.

---

## Summary

| Feature | Description |
|---------|-------------|
| `NATURAL` | Single-dimensional basis (energy only) |
| `SI_TO_NATURAL` | Transform SI dimensions to natural units |
| `NATURAL_TO_SI` | Inverse transform using constant bindings |
| `ConstantBinding` | Records dimension-constant relationships |
| `LossyProjection` | Raised for non-representable dimensions |

Natural units in ucon enable dimensional analysis for particle physics, where c = h_bar = k_B = 1 simplifies calculations and all quantities reduce to powers of energy.
