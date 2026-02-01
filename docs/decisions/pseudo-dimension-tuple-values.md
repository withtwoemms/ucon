# Tuple Values for Pseudo-Dimensions
*(Preventing Python Enum Aliasing)*

## 1. Context

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

## 2. The Problem

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

## 3. Decision

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

## 4. Rationale

### 4.1. Why Tuples Work

Python Enum compares member values for identity. Since each tuple is a distinct object—even if the first element is equal—Enum treats them as separate members:

```python
>>> (Vector(), "angle") == (Vector(), "solid_angle")
False
>>> Dimension.angle is Dimension.solid_angle
False
```

### 4.2. Why Not Override `__eq__` and `__hash__`?

Enum's comparison behavior is baked into its metaclass and cannot be cleanly overridden without breaking Enum invariants. The tuple approach works with Enum's existing machinery rather than against it.

### 4.3. Why Use a `vector` Property?

The `@property vector` provides a uniform interface for accessing the dimensional vector regardless of whether the dimension is regular or pseudo:

```python
Dimension.length.vector  # → Vector(L=1)
Dimension.angle.vector   # → Vector()
```

This keeps algebraic operations simple—they always operate on vectors.

---

## 5. Advantages

1. **Zero runtime overhead** — No metaclass hacks, no __eq__ overrides
2. **Enum-native** — Uses standard Enum behavior, not fighting it
3. **Clear semantics** — The tag string documents intent
4. **Stable hashing** — Pseudo-dimensions can be dict keys and set members
5. **Algebraic consistency preserved** — `angle.vector == none.vector`, so algebra works correctly

---

## 6. Shortcomings

1. **Two value shapes** — Regular dimensions have `Vector` values; pseudo-dimensions have `(Vector, str)` tuples. The `vector` property abstracts this, but it's an internal irregularity.

2. **`Dimension.angle.value` is a tuple** — Direct access to `.value` returns the tuple, which may surprise users expecting a `Vector`. Users should use `.vector` instead.

3. **Tag strings are arbitrary** — The "angle", "solid_angle", "ratio" strings exist only to differentiate tuple values. They're not used programmatically beyond ensuring uniqueness.

4. **Not extensible to many pseudo-dimensions** — While sufficient for the three current pseudo-dimensions, adding many more would require careful tag management. (This is unlikely to be an issue in practice.)

---

## 7. Alternatives Considered

### 7.1. Subclass Vector for Each Pseudo-Dimension

```python
class AngleVector(Vector): pass
class Dimension(Enum):
    angle = AngleVector()
```

**Rejected** — Creates unnecessary class proliferation and complicates vector arithmetic.

### 7.2. Use Integer Tags

```python
angle = (Vector(), 1)
solid_angle = (Vector(), 2)
```

**Rejected** — String tags are self-documenting; integers require external lookup.

### 7.3. Custom Enum Metaclass

Override Enum's value handling to allow identical Vector values as distinct members.

**Rejected** — Too complex, fragile across Python versions, and violates principle of least surprise.

### 7.4. Separate Enum for Pseudo-Dimensions

```python
class PseudoDimension(Enum):
    angle = auto()
    solid_angle = auto()
```

**Rejected** — Requires parallel type handling throughout the codebase and complicates `Dimension` as the single source of truth.

---

## 8. Consequences

### Positive

- Pseudo-dimensions work correctly as dict keys and set members
- Algebraic operations continue to use vector arithmetic unchanged
- `Dimension._resolve()` returns `none` for zero-vector results (not pseudo-dimensions)
- Cross-pseudo-dimension conversions fail with `ConversionNotFound`

### Negative

- Internal complexity: two value shapes in one Enum
- Users must use `.vector` instead of `.value` for consistent access

---

## 9. Related Decisions

- **Dimension._resolve()** — Always returns `none` for zero vectors, never pseudo-dimensions
