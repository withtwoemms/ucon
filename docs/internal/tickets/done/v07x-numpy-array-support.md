# Ticket: v0.7.x NumPy Array Support

**Priority:** High
**Theme:** Scientific computing integration
**Branch:** `ucon#XXX-numpy-array-support`

---

## Summary

Add `NumberArray` class for operating on multiple quantities of a given unit simultaneously. NumPy is an optional dependency — core ucon remains lightweight.

---

## Motivation

Scientific and engineering workflows frequently involve batch operations on arrays of measurements:
- Sensor data streams (thousands of temperature readings)
- Experimental datasets (repeated trials)
- Simulation outputs (grid-based computations)
- Data science pipelines (DataFrame columns)

Currently, users must loop over scalar `Number` instances, losing numpy's vectorization benefits.

---

## Requirements

### Functional

1. **NumberArray class** — Collection of quantities with shared unit
2. **Scalar uncertainty** — Same σ for all elements (instrument error)
3. **Per-element uncertainty** — Array of σ values (varied measurements)
4. **Vectorized conversion** — `.to()` works on entire array
5. **Vectorized arithmetic** — `+`, `-`, `*`, `/` with proper uncertainty propagation
6. **Indexing** — `arr[0]` returns `Number`, `arr[1:3]` returns `NumberArray`
7. **Callable syntax** — `units.meter([1, 2, 3])` returns `NumberArray`

### Non-Functional

1. **Optional dependency** — `pip install ucon[numpy]`
2. **Graceful degradation** — Clear error if numpy not installed
3. **Performance** — Vectorized operations, no Python loops
4. **Display** — Readable repr with truncation for large arrays

---

## API Design

```python
from ucon import units
from ucon.numpy import NumberArray

# Construction
heights = NumberArray([1.7, 1.8, 1.9], unit=units.meter)
heights = units.meter([1.7, 1.8, 1.9])  # callable syntax

# With uncertainty
temps = NumberArray([20, 21, 22], unit=units.celsius, uncertainty=0.5)  # scalar
measures = NumberArray([1, 2, 3], unit=units.meter, uncertainty=[0.01, 0.02, 0.015])  # per-element

# Conversion
heights_ft = heights.to(units.foot)

# Arithmetic
doubled = heights * 2
speeds = heights / units.second(1)

# Indexing
first = heights[0]        # Number
subset = heights[1:3]     # NumberArray

# Display
print(heights)            # <[1.7, 1.8, 1.9] m>
print(temps)              # <[20, 21, 22] ± 0.5 °C>
```

---

## Implementation Phases

| Phase | Scope | Files |
|-------|-------|-------|
| 1 | NumberArray class | `ucon/numpy.py` |
| 2 | Map array support | `ucon/maps.py` |
| 3 | Callable unit syntax | `ucon/core.py` |
| 4 | Tests | `tests/ucon/test_numpy.py` |
| 5 | Package config | `pyproject.toml` |
| 6 | Documentation | `README.md`, `ROADMAP.md` |

---

## Technical Notes

### Map Compatibility

Maps must work with both scalars and arrays:

```python
def _log(x, base):
    """Logarithm that works with scalars and arrays."""
    try:
        import numpy as np
        if isinstance(x, np.ndarray):
            return np.log(x) / np.log(base)
    except ImportError:
        pass
    return math.log(x, base)
```

### Uncertainty Propagation

Same quadrature rules as `Number`, but vectorized:

```python
# Multiplication: δc = |c| * sqrt((δa/a)² + (δb/b)²)
rel_a = np.where(a != 0, ua / np.abs(a), 0)
rel_b = np.where(b != 0, ub / np.abs(b), 0)
result_unc = np.abs(a * b) * np.sqrt(rel_a**2 + rel_b**2)
```

### Display Truncation

For arrays > 6 elements, show first 3 and last 3:

```python
# <[1, 2, 3, ..., 98, 99, 100] m>
```

---

## Acceptance Criteria

- [ ] `NumberArray` class with quantities, unit, uncertainty
- [ ] Scalar and per-element uncertainty support
- [ ] Shape validation for per-element uncertainty
- [ ] Indexing returns `Number` (scalar) or `NumberArray` (slice)
- [ ] Iteration yields `Number` instances
- [ ] Arithmetic with scalars, Numbers, and NumberArrays
- [ ] Uncertainty propagation through arithmetic
- [ ] `.to()` conversion with uncertainty propagation
- [ ] Maps work with array input (`LogMap`, `AffineMap`, etc.)
- [ ] Callable syntax: `units.meter([1, 2, 3])` → `NumberArray`
- [ ] `numpy` is optional dependency
- [ ] Clear `ImportError` when numpy not installed
- [ ] Tests skip gracefully without numpy
- [ ] Repr shows values with truncation for large arrays

---

## Open Questions

1. **Broadcasting** — Should `NumberArray + NumberArray` support numpy broadcasting (different shapes)?
2. **Dimensionality** — Support 2D+ arrays or limit to 1D?
3. **Pydantic** — JSON serialization for NumberArray? (v0.7.x follow-up?)
4. **Comparison** — `arr > threshold` returns boolean array?

---

## References

- Implementation guide: `docs/ucon-v07x-implementation-guide.md`
- ROADMAP: v0.7.0 section

---

## Closure Note (2026-07-12)

**Closed: superseded and completed by v0.10.0** (see
`v010x-scientific-computing.md`), which shipped `NumberArray`, callable unit
syntax, vectorized conversion/arithmetic, and uncertainty propagation. The
open questions (broadcasting, N-D, comparisons) were all resolved
affirmatively in the v0.10.0 acceptance criteria. Code now lives at
`ucon/integrations/numpy.py`.
