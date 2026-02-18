
# Design Note: Why Closure Matters for ucon's Algebraic Types

This document explains why closure is essential for all **non-semantic** types in the ucon type system—types that participate in algebra and symbolic manipulation.

## Table of Contents
1. [Introduction](#1-introduction)
2. [Overview of ucon Types](#2-overview-of-ucon-types)
3. [What Closure Means in Algebra](#3-what-closure-means-in-algebra)
4. [Why Closure Matters for Each Type](#4-why-closure-matters-for-each-type)
5. [Semantic vs. Algebraic Types](#5-semantic-vs-algebraic-types)
6. [Summary](#6-summary)

---

## 1. Introduction

Closure ensures that algebraic operations yield results that stay within the same algebraic universe.  
Closure gives ucon:

- predictable behavior  
- composability across chained operations  
- mathematical correctness  
- symbolic reasoning capability  

Without closure, unit algebra and dimensional analysis would collapse into ad hoc case handling.

---

## 2. Overview of ucon Types

### **Algebraic Types (non-semantic)**
These support algebraic operations and must be closed over them:

- `Vector`
- `Exponent`
- `Dimension`
- `CompositeUnit`
- `Number`
- `Ratio` (partial algebra)

### **Semantic Types**
These express identity/meaning, not algebra:

- `Unit`
- `Scale`
- `ScaleDescriptor`
- `FactoredUnit` (future `UnitFactor`)
- `UnitForm` (future syntax layer)

Semantic types **must not** satisfy closure; they represent atomic symbolic entities.

---

## 3. What Closure Means in Algebra

Closure requires:

```
For any a, b ∈ T and operation ◦,
a ◦ b must also be ∈ T.
```

Closure is a cornerstone of algebraic structures such as:

- groups  
- rings  
- vector spaces  
- free abelian groups  

Closure enables:

- infinite chaining of operations  
- type stability  
- predictable transformations  
- mathematically valid simplification

---

## 4. Why Closure Matters for Each Type

### **Vector**  
Vectors form the basis of dimensional algebra.  
Closure ensures:

- exponent vectors can always add/subtract  
- every result is a valid vector  
- dimensional operations never "fall out" of the system

### **Exponent**  
Rational exponent algebra used for:

- roots  
- fractional powers  
- exponentiation of unit products  

Closure ensures consistent manipulation of exponents during unit algebra.

### **Dimension**  
Dimensions form a **free abelian group** over the 7 SI base dimensions.  
Closure guarantees:

- length/time → velocity  
- velocity*time → length  
- power laws (`dimension ** exponent`) stay meaningful  
- dimensional reasoning always produces valid dimensions

### **CompositeUnit**  
The algebra of unit expressions.  
CompositeUnit must be closed so that:

- `(g/mL) * mL = g`  
- `(m/s) * (s) = m`  
- `(m^2) / (m) = m`  

Closure keeps unit propagation correct in every arithmetic operation involving `Number`.

### **Number**  
Numbers represent physical quantities.  
Closure ensures:

- unit-carrying quantities remain quantities  
- addition/subtraction only valid for same dimensions  
- multiplication/division produces new quantities with correct units  
- `(density * volume)` stays a `Number`

Without closure, the physical modeling layer fails.

### **Ratio** (partial algebra)  
Represents symbolic `Number / Number`.  
Closure within Ratio operations allows:

- `ratio * ratio` → ratio  
- `ratio / ratio` → ratio  
- but collapse (→ `Number`) only happens via `.evaluate()`

This keeps symbolic expressions manipulable until evaluation.

---

## 5. Semantic vs. Algebraic Types

### **Semantic Types**
They encode *meaning*, not operations.  
They must not have closure because that would imply:

- adding units  
- subtracting prefixes  
- treating identity objects as algebraic actors  

Examples: `Unit`, `Scale`, `FactoredUnit`.

### **Algebraic Types**
These perform real symbolic mathematics and rely on closure for:

- chaining  
- simplification  
- correctness  
- type stability  

Examples: `Vector`, `Dimension`, `CompositeUnit`, `Number`.

---

## 6. Summary

Closure is essential to ucon’s design because:

- It guarantees every algebraic layer remains stable under operations.
- It ensures dimensional correctness throughout calculations.
- It preserves symbolic reasoning both before and after evaluation.
- It cleanly separates *semantic identity* from *algebraic behavior*.
- It ensures the system behaves like a true physical unit algebra rather than a procedural rule engine.

Closure is the backbone that allows ucon to scale from simple units to fully composable dimensional analysis.
