# Conversion Contexts

Normally, ucon converts between units of the **same dimension** — meters
to feet (length), kilograms to pounds (mass). But physics often relates
quantities of *different* dimensions through fundamental constants:

- Wavelength (length) and frequency (time⁻¹) via the speed of light *c*
- Energy and temperature via the Boltzmann constant *k_B*
- Energy and frequency via Planck's constant *h*

A `ConversionContext` bundles these cross-dimensional relationships and
makes them available within a scoped block.

## Built-in Contexts

ucon ships with two contexts:

| Context | Constant(s) | Conversions enabled |
|---------|-------------|---------------------|
| `spectroscopy` | *c*, *h*, *hc* | wavelength ↔ frequency ↔ energy ↔ wavenumber |
| `boltzmann` | *k_B* | temperature ↔ energy |

## Basic Usage

```python
from ucon import units, spectroscopy, boltzmann, using_context
```

### Spectroscopy: wavelength to frequency

```python
with using_context(spectroscopy):
    green_light = units.meter(500e-9)       # 500 nm
    freq = green_light.to(units.hertz)
    print(freq)  # <5.996e+14 Hz>
```

### Spectroscopy: frequency to energy

```python
with using_context(spectroscopy):
    freq = units.hertz(5.996e14)
    energy = freq.to(units.joule)
    print(energy)  # <3.974e-19 J>
```

### Spectroscopy: wavelength to wavenumber

```python
with using_context(spectroscopy):
    wl = units.meter(500e-9)
    k = wl.to(units.reciprocal_meter)
    print(f"{k.quantity:.0f} m⁻¹")  # 2000000 m⁻¹
```

### Boltzmann: temperature to energy

```python
with using_context(boltzmann):
    room_temp = units.kelvin(300)
    thermal_energy = room_temp.to(units.joule)
    print(thermal_energy)  # <4.141e-21 J>
```

### Combining contexts

Multiple contexts can be activated together:

```python
with using_context(spectroscopy, boltzmann):
    # Temperature → energy → frequency (chain through both contexts)
    temp = units.kelvin(5000)
    energy = temp.to(units.joule)
    freq = energy.to(units.hertz)
    print(f"{freq.quantity:.3e} Hz")  # 1.041e+14 Hz
```

## How It Works

`using_context()` copies the current conversion graph, injects the
context's cross-dimensional edges, and scopes the extended graph for the
duration of the `with` block. The original graph is untouched:

```python
# Outside the context — cross-dimensional conversion fails
units.meter(500e-9).to(units.hertz)  # raises ConversionNotFound
```

## Defining Custom Contexts

You can define your own contexts for domain-specific cross-dimensional
relationships.

```python
from ucon import units, using_context
from ucon.contexts import ConversionContext, ContextEdge
from ucon.maps import LinearMap

# Stefan-Boltzmann: radiant exitance from temperature
# M = σ * T⁴ — but for a linear context edge, we fix T and express
# as a proportionality at a reference temperature.
#
# For a simple constant-of-proportionality relationship:
sigma = 5.670374419e-8  # W/(m²·K⁴)

my_context = ConversionContext(
    name="custom",
    edges=(
        ContextEdge(
            src=units.meter,
            dst=units.foot,
            map=LinearMap(3.28084),  # any Map works
        ),
    ),
    description="Example custom context.",
)

with using_context(my_context):
    # Context edges are active here
    pass
```

A `ContextEdge` requires:

- `src` — source unit (`Unit` or `UnitProduct`)
- `dst` — destination unit (`Unit` or `UnitProduct`)
- `map` — a `Map` instance (`LinearMap`, `ReciprocalMap`, etc.)

The inverse edge is registered automatically.

## API Summary

| Symbol | Type | Description |
|--------|------|-------------|
| `spectroscopy` | `ConversionContext` | Wavelength/frequency/energy via *c* and *h* |
| `boltzmann` | `ConversionContext` | Temperature/energy via *k_B* |
| `using_context(*contexts)` | context manager | Activate contexts for a block |
| `ConversionContext(name, edges, description)` | class | Bundle of cross-dimensional edges |
| `ContextEdge(src, dst, map)` | class | Single cross-dimensional edge |
