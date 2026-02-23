# ADR-005: Tuple Values for Pseudo-Dimensions

**Status:** Accepted
**Date:** 2026-02-01
**Context:** v0.5.0 Dimensionless Units

## Summary

Use tuple values `(Vector(), "tag")` for pseudo-dimensions to prevent Python Enum aliasing while preserving algebraic consistency.

---

## Context

ucon v0.5.0 introduced **pseudo-dimensions**—semantic categories for dimensionless quantities:

- `Dimension.angle` (radian, degree, etc.)
- `Dimension.solid_angle` (steradian, square_degree)
- `Dimension.ratio` (percent, ppm, etc.)

These pseudo-dimensions share the **zero vector** with `Dimension.none`, preserving algebraic consistency:

```python
angle × length = length  # angle has zero vector, so it's multiplicatively transparent
```

However, they must remain **semantically distinct** to prevent nonsensical conversions like `radian(1).to(percent)`.

---

## The Problem

Python's `Enum` treats members with identical values as **aliases**:

```python
class Dimension(Enum):
    none  = Vector()
    angle = Vector()  # Alias for `none`!
```

With this definition:

```python
>>> Dimension.angle is Dimension.none
True
>>> Dimension.angle == Dimension.none
True
```

This defeats the purpose of pseudo-dimensions.

---

## Decision

Use **tuple values** `(Vector(), "tag")` for pseudo-dimensions:

```python
class Dimension(Enum):
    # Base dimensions (single Vector values)
    time   = Vector(T=1)
    length = Vector(L=1)
    # ...

    # Dimensionless
    none = Vector()

    # Pseudo-dimensions (tuple values to prevent aliasing)
    angle       = (Vector(), "angle")
    solid_angle = (Vector(), "solid_angle")
    ratio       = (Vector(), "ratio")

    @property
    def vector(self) -> Vector:
        """Extract the Vector component, handling both regular and pseudo-dimensions."""
        if isinstance(self.value, tuple):
            return self.value[0]
        return self.value
```

---

## Rationale

### Why Tuples Work

Python Enum compares member values for identity. Since each tuple is a distinct object—even if the first element is equal—Enum treats them as separate members:

```python
>>> (Vector(), "angle") == (Vector(), "solid_angle")
False
>>> Dimension.angle is Dimension.solid_angle
False
```

### Why Not Override `__eq__` and `__hash__`?

Enum's comparison behavior is baked into its metaclass and cannot be cleanly overridden without breaking Enum invariants. The tuple approach works with Enum's existing machinery rather than against it.

### Why Use a `vector` Property?

The `@property vector` provides a uniform interface for accessing the dimensional vector regardless of whether the dimension is regular or pseudo:

```python
Dimension.length.vector  # → Vector(L=1)
Dimension.angle.vector   # → Vector()
```

This keeps algebraic operations simple—they always operate on vectors.

---

## Consequences

### Positive

- Zero runtime overhead — No metaclass hacks, no __eq__ overrides
- Enum-native — Uses standard Enum behavior, not fighting it
- Clear semantics — The tag string documents intent
- Stable hashing — Pseudo-dimensions can be dict keys and set members
- Algebraic consistency preserved — `angle.vector == none.vector`, so algebra works correctly
- Pseudo-dimensions work correctly as dict keys and set members
- `Dimension._resolve()` returns `none` for zero-vector results (not pseudo-dimensions)
- Cross-pseudo-dimension conversions fail with `ConversionNotFound`

### Negative

- Two value shapes — Regular dimensions have `Vector` values; pseudo-dimensions have `(Vector, str)` tuples. The `vector` property abstracts this, but it's an internal irregularity.
- `Dimension.angle.value` is a tuple — Direct access to `.value` returns the tuple, which may surprise users expecting a `Vector`. Users should use `.vector` instead.
- Tag strings are arbitrary — The "angle", "solid_angle", "ratio" strings exist only to differentiate tuple values. They're not used programmatically beyond ensuring uniqueness.

---

## Alternatives Considered

| Alternative | Reason Rejected |
|-------------|-----------------|
| Subclass Vector for each pseudo-dimension | Creates unnecessary class proliferation and complicates vector arithmetic |
| Use integer tags `(Vector(), 1)` | String tags are self-documenting; integers require external lookup |
| Custom Enum metaclass | Too complex, fragile across Python versions, violates principle of least surprise |
| Separate Enum for pseudo-dimensions | Requires parallel type handling throughout the codebase and complicates `Dimension` as the single source of truth |

---

## Related Decisions

- **Dimension._resolve()** — Always returns `none` for zero vectors, never pseudo-dimensions
