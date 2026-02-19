# Custom Unit Systems with BasisTransform

This example demonstrates how to define a custom dimensional system and convert between it and SI units.

## Scenario: Fantasy Game Physics

The realm of Valdris has three fundamental dimensions:
- **Aether (A)**: magical energy substrate
- **Resonance (R)**: vibrational frequency of magic
- **Substance (S)**: physical matter

These combine into SI dimensions via a transformation matrix:

```
| L |   | 2  0  0 |   | A |
| M | = | 1  0  1 | × | R |
| T |   |-2 -1  0 |   | S |
```

Reading the columns:
- 1 aether contributes: L², M, T⁻² (energy-like)
- 1 resonance contributes: T⁻¹ (frequency-like)
- 1 substance contributes: M (mass-like)

## Implementation

```python
from fractions import Fraction
from ucon import BasisTransform, Dimension, Unit, UnitSystem, units
from ucon.graph import ConversionGraph
from ucon.maps import LinearMap

# Fantasy base units
mote = Unit(name='mote', dimension=Dimension.energy, aliases=('mt',))
chime = Unit(name='chime', dimension=Dimension.frequency, aliases=('ch',))
ite = Unit(name='ite', dimension=Dimension.mass, aliases=('it',))

valdris = UnitSystem(
    name="Valdris",
    bases={
        Dimension.energy: mote,
        Dimension.frequency: chime,
        Dimension.mass: ite,
    }
)

# The basis transform encodes how Valdris dimensions compose into SI
valdris_to_si = BasisTransform(
    src=valdris,
    dst=units.si,
    src_dimensions=(Dimension.energy, Dimension.frequency, Dimension.mass),
    dst_dimensions=(Dimension.energy, Dimension.frequency, Dimension.mass),
    matrix=(
        (2, 0, 0),    # energy: 2 × aether
        (1, 0, 1),    # frequency: aether + substance
        (-2, -1, 0),  # mass: -2×aether - resonance
    ),
)

# Physical calibration: how many SI units per fantasy unit
graph = ConversionGraph()
graph.connect_systems(
    basis_transform=valdris_to_si,
    edges={
        (mote, units.joule): LinearMap(42),           # 1 mote = 42 J
        (chime, units.hertz): LinearMap(7),           # 1 chime = 7 Hz
        (ite, units.kilogram): LinearMap(Fraction(1, 2)),  # 1 ite = 0.5 kg
    }
)

# Game engine converts between physics systems
energy_map = graph.convert(src=mote, dst=units.joule)
energy_map(10)  # 420 joules from 10 motes

# Inverse: display real-world values in game units
joule_to_mote = graph.convert(src=units.joule, dst=mote)
joule_to_mote(420)  # 10 motes

# The transform is invertible with exact Fraction arithmetic
valdris_to_si.is_invertible  # True
```

## Use Cases

This pattern enables:
- **Fantasy/sci-fi game physics**: Define alternate dimensional systems for fictional worlds
- **Domain-specific units**: Create unit systems for specialized fields (e.g., CGS, Gaussian)
- **Legacy system integration**: Bridge between incompatible measurement frameworks
- **Educational tools**: Demonstrate dimensional analysis with custom examples
