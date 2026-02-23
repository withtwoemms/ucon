# Why Type Safety Matters

> **Mathematical correctness isn’t enough — physical correctness matters too.**  
> `ucon` encodes that correctness directly into its types.

In most code, numbers are just numbers. There’s nothing to stop you from writing:

```python
speed = 10 + 5  # is this 10 meters + 5 seconds?
```

Python won’t complain — but physics will.

That’s where **`ucon`’s type safety** comes in.

---

## What Type Safety Means in `ucon`

Every measurable value in `ucon` is an instance of a **typed quantity**, built from:
- a **`Number`** (value holder),
- a **`Unit`** (measurement context),
- and a **`Dimension`** (semantic definition of what it represents).

Together, they form a **self-validating algebra** that enforces physical consistency at runtime and, with `pydantic`, even at data-model validation time.

---

## Example: _Dimensional Enforcement_

```python
from ucon import Number, units

length = Number(quantity=5, unit=units.meter)
time = Number(quantity=2, unit=units.second)

speed = length / time     # ✅ valid: L / T = velocity
invalid = length + time   # ❌ raises: incompatible dimensions
```

Every operation checks the **dimensional structure**, not just the unit labels. This means `ucon` doesn’t just track *names* — it enforces *physics*.

---

## Why This Matters

| Problem Without Type Safety | What `ucon` Prevents |
|------------------------------|----------------------|
| Adding incompatible quantities (e.g., `5 meters + 2 seconds`) | Raises dimension error |
| Mis-specified conversions (`100 cm.to("gram")`) | Dimension mismatch validation |
| Silent loss of context (`5 * 10` → 50 of what?) | Every result retains `Unit` and `Dimension` |
| Implicit scale confusion (`1 kB` vs `1 KiB`) | Explicit `Scale` semantics |
| Unverifiable API inputs (`"speed": 12`) | Pydantic validation with `NumberType[Dimension.velocity]` |

---

## With Pydantic Integration (v0.8.0+)

`ucon`’s type safety extends into **data models and APIs**:

```python
from pydantic import BaseModel
from ucon.pydantic_integration import NumberType
from ucon.dimension import Dimension

class Motion(BaseModel):
    distance: NumberType[Dimension.length]
    time: NumberType[Dimension.time]

# Validation happens automatically
Motion(distance="10 meter", time="5 second")     # ✅
Motion(distance="10 meter", time="5 kilogram")   # ❌ validation error
```

This turns physical correctness into a **validation rule**, not a runtime accident.


## In Summary

| Layer | What Type Safety Ensures |
|--------|---------------------------|
| **Algebraic** | Operations preserve valid dimensional structure |
| **Runtime** | Incompatible operations raise descriptive errors |
| **Serialization** | Units and dimensions persist through JSON/YAML models |
| **Validation** | Pydantic can enforce dimension-aware schemas |
| **Introspection** | Each value carries its own semantic meaning |

---

> With `ucon`, every number knows _what it is_,
> every unit knows _what it measures_,
> and every computation knows _if it makes sense._
