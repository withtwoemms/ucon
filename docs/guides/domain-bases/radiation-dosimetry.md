# Radiation Dosimetry Basis

## The Degeneracy Problem

In SI, all of these have dimension L²T⁻² (equivalent to J/kg):

| Quantity | Unit | What It Measures |
|----------|------|------------------|
| Absorbed dose | Gray (Gy) | Energy deposited per mass |
| Equivalent dose | Sievert (Sv) | Biologically weighted dose (radiation type) |
| Effective dose | Sievert (Sv) | Whole-body risk-weighted dose |
| RBE-weighted dose | Gy(RBE) | Therapeutically weighted dose |
| Kerma | Gray (Gy) | Kinetic energy released in matter |
| Specific energy | J/kg | Generic energy per mass |

**All dimensionally identical. All clinically distinct.**

Confusing Gray with Sievert, or equivalent dose with effective dose, is a medical error.

---

## The Extended Dose Basis

```python
from ucon.basis import Basis, BasisComponent, Vector
from ucon.core import Dimension, Unit
from fractions import Fraction

DOSE = Basis("Dose", [
    BasisComponent("energy", "E"),              # 0
    BasisComponent("mass", "M"),                # 1
    BasisComponent("radiation_weighting", "R"), # 2 — w_R (regulatory)
    BasisComponent("rbe", "B"),                 # 3 — RBE (therapeutic)
    BasisComponent("tissue_weighting", "T"),    # 4 — w_T (organ sensitivity)
])
```

---

## Dimensional Vectors

| Quantity | Vector | Interpretation |
|----------|--------|----------------|
| Absorbed dose (Gy) | E¹M⁻¹R⁰B⁰T⁰ | Raw energy deposition |
| Equivalent dose (Sv) | E¹M⁻¹R¹B⁰T⁰ | w_R weighted (organ level) |
| Effective dose (Sv) | E¹M⁻¹R¹B⁰T¹ | w_R × w_T weighted (whole body) |
| RBE-weighted dose Gy(RBE) | E¹M⁻¹R⁰B¹T⁰ | Therapeutic RBE weighted |

---

## Implementation

```python
# Dimensions
absorbed_dose = Dimension(
    vector=Vector(DOSE, (1, -1, 0, 0, 0)),
    name="absorbed_dose",
    symbol="D"
)

equivalent_dose = Dimension(
    vector=Vector(DOSE, (1, -1, 1, 0, 0)),
    name="equivalent_dose",
    symbol="H"
)

effective_dose = Dimension(
    vector=Vector(DOSE, (1, -1, 1, 0, 1)),
    name="effective_dose",
    symbol="E_eff"
)

rbe_weighted_dose = Dimension(
    vector=Vector(DOSE, (1, -1, 0, 1, 0)),
    name="rbe_weighted_dose",
    symbol="D_RBE"
)

# Weighting factor dimensions
radiation_weighting = Dimension(
    vector=Vector(DOSE, (0, 0, 1, 0, 0)),
    name="radiation_weighting"
)  # R¹ — w_R values: gamma=1, alpha=20

tissue_weighting = Dimension(
    vector=Vector(DOSE, (0, 0, 0, 0, 1)),
    name="tissue_weighting"
)  # T¹ — w_T values: lung=0.12, gonads=0.08, etc.

rbe_factor = Dimension(
    vector=Vector(DOSE, (0, 0, 0, 1, 0)),
    name="rbe_factor"
)  # B¹ — RBE values: proton≈1.1, carbon≈2-3

# Units
gray = Unit(name="gray", shorthand="Gy", dimension=absorbed_dose)
sievert_eq = Unit(name="sievert_equivalent", shorthand="Sv", dimension=equivalent_dose)
sievert_eff = Unit(name="sievert_effective", shorthand="Sv_eff", dimension=effective_dose)
gray_rbe = Unit(name="gray_rbe", shorthand="Gy(RBE)", dimension=rbe_weighted_dose)
```

---

## Dimensional Algebra

**Absorbed → Equivalent:**
```
H = D × w_R
E¹M⁻¹R¹B⁰T⁰ = (E¹M⁻¹R⁰B⁰T⁰) × (R¹)  ✓
```

**Equivalent → Effective:**
```
E_eff = H × w_T
E¹M⁻¹R¹B⁰T¹ = (E¹M⁻¹R¹B⁰T⁰) × (T¹)  ✓
```

**Absorbed → RBE-weighted:**
```
D_RBE = D × RBE
E¹M⁻¹R⁰B¹T⁰ = (E¹M⁻¹R⁰B⁰T⁰) × (B¹)  ✓
```

---

## Safety Guarantees

```python
# These are now compile-time errors (dimension mismatch):

gray(2.0) + sievert_eq(1.0)
# raises: incompatible dimensions (R⁰ vs R¹)

sievert_eq(1.0) + sievert_eff(0.5)
# raises: incompatible dimensions (T⁰ vs T¹)

gray(2.0) + gray_rbe(2.2)
# raises: incompatible dimensions (B⁰ vs B¹)
```

---

## Weighting Factor Values

### Radiation Weighting Factors (w_R)

| Radiation Type | w_R |
|----------------|-----|
| Photons (all energies) | 1 |
| Electrons, muons | 1 |
| Protons | 2 |
| Alpha particles | 20 |
| Neutrons | 5-20 (energy dependent) |

### Tissue Weighting Factors (w_T)

| Tissue | w_T |
|--------|-----|
| Bone marrow, colon, lung, stomach, breast | 0.12 |
| Gonads | 0.08 |
| Bladder, liver, esophagus, thyroid | 0.04 |
| Skin, bone surface, brain, salivary glands | 0.01 |
| Remainder | 0.12 (distributed) |

### RBE Values (Therapeutic)

| Particle | RBE (typical) |
|----------|---------------|
| Photons | 1.0 (reference) |
| Protons | 1.1 (clinical convention) |
| Carbon ions | 2-3 (varies with LET) |

---

## Clinical Context

### Radiation Protection (ICRP)

Uses **w_R** and **w_T** for regulatory dose limits:
- Occupational limit: 20 mSv/year (effective dose)
- Public limit: 1 mSv/year (effective dose)

### Radiation Therapy

Uses **RBE** for treatment planning:
- Proton therapy: Gy(RBE) = Gy × 1.1
- Carbon ion therapy: Gy(RBE) = Gy × RBE(LET)

**The distinction matters:** A patient receiving 60 Gy(RBE) proton therapy has a different physical dose than 60 Gy photon therapy, and both differ from regulatory effective dose calculations.

---

## Projection to SI

If you need to collapse back to SI (L²T⁻²), use a `ConstantBoundBasisTransform` with bindings that record which weighting factors were absorbed:

```python
DOSE_TO_SI = ConstantBoundBasisTransform(
    source=DOSE,
    target=SI,
    matrix=(...),  # Maps E¹M⁻¹ → L²T⁻²
    bindings=(
        ConstantBinding(
            source_component=DOSE["radiation_weighting"],
            target_expression=Vector(SI, (0, 0, 0, ...)),  # dimensionless
            constant_symbol="w_R",
            exponent=Fraction(1),
        ),
        # ... similar for tissue_weighting, rbe
    ),
)
```

The bindings enable round-trip conversion while tracking which weighting was applied.
