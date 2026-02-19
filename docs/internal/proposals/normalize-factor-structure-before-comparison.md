# Factor Simplification for Derived Dimension Equivalences

## Summary

Enable automatic recognition of algebraic equivalences between factor structures, such as `energy/time = power`, eliminating the need for explicit product edges.

---

## Problem Statement

Currently, conversions like `BTU/h → kW` require explicit product edges because the factor structures don't match:

```
BTU/h: {Dimension.energy: 1, Dimension.time: -1}
kW:    {Dimension.power: 1}
```

Even though `energy / time = power` algebraically (both have vector `M·L²·T⁻³`), the factorwise decomposition fails because it compares factor structures by dimension enum identity.

### Current Workaround

Add explicit product edges for common cases:
```python
graph.add_edge(src=units.btu / units.hour, dst=units.watt, map=LinearMap(1055.06 / 3600))
```

This works but doesn't scale—every new derived unit combination requires manual edges.

---

## Proposed Solution

Normalize factor structures to a **canonical form** before comparison, recognizing when different factor structures represent the same physical quantity.

### Approach: Base Dimension Normalization

Convert all UnitProducts to their base SI equivalent for matching purposes:

1. **Compute effective base dimensions**: Expand each factor's dimension to base dimensions, multiply by exponent
2. **Sum contributions**: Combine all contributions to each base dimension
3. **Match by base structure**: Two products match if their base dimension structures are identical

### Example

```python
# BTU/h
btu_expansion = {mass: 1, length: 2, time: -2}  # energy
hour_expansion = {time: 1}
# Combined: {mass: 1, length: 2, time: -2 + (-1)} = {mass: 1, length: 2, time: -3}

# kW
watt_expansion = {mass: 1, length: 2, time: -3}  # power
# Combined: {mass: 1, length: 2, time: -3}

# Both normalize to the same base structure → conversion possible
```

---

## Implementation

### 1. Add `Dimension.canonical_unit()` Method

Return the base SI unit for each dimension:

```python
class Dimension(Enum):
    def canonical_unit(self) -> Unit | UnitProduct:
        """Return the canonical SI unit for this dimension."""
        CANONICAL_UNITS = {
            Dimension.length: meter,
            Dimension.mass: kilogram,
            Dimension.time: second,
            Dimension.energy: joule,
            Dimension.power: watt,
            Dimension.volume: meter ** 3,
            # ... etc
        }
        return CANONICAL_UNITS.get(self)
```

### 2. Add `UnitProduct.to_base_si()` Method

Convert any UnitProduct to base SI units:

```python
class UnitProduct:
    def to_base_si(self, graph: ConversionGraph) -> tuple[float, UnitProduct]:
        """
        Convert to base SI representation.

        Returns (scale_factor, base_si_product) where:
        - scale_factor: multiply original quantity by this to get base SI
        - base_si_product: the equivalent product in base SI units
        """
        scale = 1.0
        base_factors = {}

        for factor, exp in self.factors.items():
            # Get canonical unit for this factor's dimension
            canonical = factor.unit.dimension.canonical_unit()

            # Find conversion: factor.unit → canonical
            unit_scale = graph._convert_units(factor.unit, canonical_unit)

            # Accumulate scale and factors
            scale *= (factor.scale.fold() * unit_scale) ** exp
            base_factors[canonical_factor] = exp

        return scale, UnitProduct(base_factors)
```

### 3. Modify `_convert_factorwise()` to Use Base Normalization

```python
def _convert_factorwise(self, *, src: UnitProduct, dst: UnitProduct) -> Map:
    # Try current approach first (for efficiency)
    try:
        return self._convert_factorwise_direct(src, dst)
    except ConversionNotFound:
        pass

    # Fall back to base normalization
    src_scale, src_base = src.to_base_si(self)
    dst_scale, dst_base = dst.to_base_si(self)

    # Base structures must match
    if src_base.factors.keys() != dst_base.factors.keys():
        raise ConversionNotFound(...)

    # Conversion is just the scale ratio
    return LinearMap(src_scale / dst_scale)
```

---

## Complexity Analysis

| Component | Effort | Risk | Notes |
|-----------|--------|------|-------|
| `Dimension.canonical_unit()` | Low | Low | Static mapping |
| `UnitProduct.to_base_si()` | Medium | Medium | Requires graph access |
| Modify `_convert_factorwise()` | Medium | High | Core conversion path |
| Handle composite canonical units | Medium | Medium | e.g., `m³` for volume |
| Test coverage | High | Low | Many edge cases |

**Total Estimate:** 2-3 days of focused work

---

## Edge Cases

### 1. Composite Canonical Units

Volume's canonical unit is `m³`, which is a UnitProduct, not a Unit. The implementation must handle this.

### 2. Pseudo-Dimensions

Angle, solid_angle, and ratio have zero vectors. They cannot be normalized to base SI and must remain isolated.

### 3. Cross-System Units

Units from different systems (CGS, imperial) must convert through SI base units.

### 4. Circular Dependencies

`to_base_si()` calls `_convert_units()`, which might call `_convert_factorwise()`. Guard against infinite recursion.

---

## Alternatives Considered

### A. Expand Product Edge Registry

Add all possible derived-to-derived edges:
- ❌ Combinatorial explosion
- ❌ Maintenance burden
- ❌ Doesn't scale to user-defined units

### B. Symbolic Simplification

Use symbolic algebra to simplify factor structures:
- ❌ Over-engineered for this use case
- ❌ External dependency (SymPy)
- ❌ Performance concerns

### C. Current Approach (Explicit Edges)

Keep adding product edges for common cases:
- ✅ Simple, predictable
- ❌ Doesn't scale
- ❌ Users must know which edges exist

---

## Success Criteria

- [ ] `BTU/h → kW` works without explicit product edge
- [ ] `J/s → W` works (energy/time → power)
- [ ] `N*m → J` works (force*length → energy)
- [ ] `kg*m/s² → N` works (mass*acceleration → force)
- [ ] No regression on existing conversions
- [ ] Performance impact < 10% for typical conversions

---

## References

- Dimensional analysis: https://en.wikipedia.org/wiki/Dimensional_analysis
- SI derived units: https://en.wikipedia.org/wiki/SI_derived_unit
