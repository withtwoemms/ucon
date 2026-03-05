# Pharmacology Basis

## The Degeneracy Problem

In SI, drug amounts are measured in mass (kg or mg). But:

| Drug | Dose | Equivalent Effect |
|------|------|-------------------|
| Morphine | 10 mg | Baseline |
| Fentanyl | 0.1 mg | Same as 10 mg morphine |
| Codeine | 100 mg | Same as 10 mg morphine |

**All are "milligrams" in SI. Treating them as equivalent is fatal.**

Similar problems exist with:
- International Units (IU) — different for each substance
- Bioavailability — IV vs oral doses
- Receptor binding — agonist vs antagonist potency

---

## The Extended Pharmacology Basis

```python
from ucon.basis import Basis, BasisComponent, Vector
from ucon.core import Dimension, Unit
from fractions import Fraction

PHARMA = Basis("Pharma", [
    BasisComponent("mass", "M"),              # 0 — physical mass
    BasisComponent("potency", "P"),           # 1 — biological activity
    BasisComponent("bioavailability", "F"),   # 2 — fraction reaching systemic circulation
])
```

---

## Dimensional Vectors

| Quantity | Vector | Interpretation |
|----------|--------|----------------|
| Drug mass | M¹P⁰F⁰ | Raw substance amount |
| Potency factor | M⁰P¹F⁰ | Activity per unit mass |
| Bioactive dose | M¹P¹F⁰ | Mass × potency |
| Systemically available dose | M¹P¹F¹ | Mass × potency × bioavailability |

---

## Implementation

```python
# Dimensions
drug_mass = Dimension(
    vector=Vector(PHARMA, (1, 0, 0)),
    name="drug_mass"
)

potency_factor = Dimension(
    vector=Vector(PHARMA, (0, 1, 0)),
    name="potency_factor"
)

bioactive_dose = Dimension(
    vector=Vector(PHARMA, (1, 1, 0)),
    name="bioactive_dose"
)

systemic_dose = Dimension(
    vector=Vector(PHARMA, (1, 1, 1)),
    name="systemic_dose"
)

# Units with potency baked in
morphine_mg = Unit(
    name="morphine_mg",
    shorthand="mg(morphine)",
    dimension=bioactive_dose
)  # potency = 1 (reference)

fentanyl_mg = Unit(
    name="fentanyl_mg",
    shorthand="mg(fentanyl)",
    dimension=bioactive_dose
)  # potency = 100

codeine_mg = Unit(
    name="codeine_mg",
    shorthand="mg(codeine)",
    dimension=bioactive_dose
)  # potency = 0.1
```

---

## Morphine Milligram Equivalents (MME)

The CDC uses MME for opioid risk assessment:

```python
# Conversion factors to MME
OPIOID_MME = {
    "morphine": 1.0,
    "fentanyl": 100.0,      # 0.1 mg fentanyl = 10 MME
    "oxycodone": 1.5,
    "hydrocodone": 1.0,
    "codeine": 0.15,
    "methadone": 4.0,       # variable, dose-dependent
    "buprenorphine": 30.0,
}

# With dimensional tracking:
fentanyl_dose = fentanyl_mg(0.1)
mme = fentanyl_dose.to(morphine_equivalent)  # → 10 MME

# CDC risk thresholds
# ≥50 MME/day: increased overdose risk
# ≥90 MME/day: avoid or justify
```

---

## International Units (IU)

IU is a measure of biological activity, not mass. Each substance has its own definition:

| Substance | 1 IU = | Notes |
|-----------|--------|-------|
| Insulin | 0.0347 mg (human) | Based on blood glucose effect |
| Vitamin D | 0.025 μg | Based on antirachitic activity |
| Vitamin A | 0.3 μg retinol | Based on growth assay |
| Heparin | ~0.002 mg | Based on anticoagulation |
| Penicillin | 0.6 μg | Historical bioassay |

**Problem:** 1 IU of insulin ≠ 1 IU of vitamin D, but SI treats both as dimensionless counts.

**Solution:** Model IU as substance-specific potency:

```python
# Each IU type is a distinct unit with P¹ dimension
insulin_iu = Unit(name="insulin_IU", dimension=potency_factor)
vitamin_d_iu = Unit(name="vitamin_d_IU", dimension=potency_factor)

# These cannot be added
insulin_iu(100) + vitamin_d_iu(1000)
# raises: incompatible (different substances, even though both are "IU")
```

For full safety, extend the basis with a substance tag:

```python
PHARMA_TYPED = Basis("Pharma-Typed", [
    BasisComponent("mass", "M"),
    BasisComponent("potency", "P"),
    BasisComponent("bioavailability", "F"),
    BasisComponent("substance_class", "S"),  # insulin=1, vitamin_d=2, etc.
])
```

---

## Bioavailability

The fraction of drug reaching systemic circulation:

| Route | Typical F |
|-------|-----------|
| IV | 1.0 (by definition) |
| IM | 0.8-1.0 |
| Oral | 0.1-0.9 (highly variable) |
| Transdermal | 0.1-0.5 |
| Sublingual | 0.3-0.8 |

```python
# Oral morphine vs IV morphine
oral_morphine = Unit(
    name="oral_morphine_mg",
    dimension=systemic_dose  # M¹P¹F¹
)
# F ≈ 0.3 for oral morphine

iv_morphine = Unit(
    name="iv_morphine_mg",
    dimension=systemic_dose
)
# F = 1.0 for IV

# 30 mg oral ≈ 10 mg IV (same systemic exposure)
```

---

## Dimensional Algebra

**Mass → Bioactive dose:**
```
bioactive = mass × potency
M¹P¹F⁰ = (M¹P⁰F⁰) × (P¹)  ✓
```

**Bioactive → Systemic:**
```
systemic = bioactive × bioavailability
M¹P¹F¹ = (M¹P¹F⁰) × (F¹)  ✓
```

---

## Safety Guarantees

```python
# These are now dimension mismatches:

morphine_mg(10) + fentanyl_mg(0.1)
# Must convert to common equivalents first

oral_morphine(30) + iv_morphine(10)
# Must account for bioavailability

insulin_iu(100) + vitamin_d_iu(1000)
# Cannot add different IU types
```

---

## Clinical Decision Support

With dimensional tracking, you can build safer systems:

```python
def check_mme_risk(prescriptions: list[Number]) -> str:
    """Check total daily MME against CDC thresholds."""
    total_mme = sum(
        dose.to(morphine_equivalent)
        for dose in prescriptions
    )

    if total_mme.quantity >= 90:
        return "HIGH RISK: ≥90 MME/day"
    elif total_mme.quantity >= 50:
        return "ELEVATED RISK: ≥50 MME/day"
    else:
        return "Standard risk"
```

The dimension system ensures all inputs are converted to a common basis before summation — no accidental fentanyl + morphine addition.

---

## Corticosteroid Equivalents

Similar pattern for steroid conversions:

| Drug | Equivalent Dose | Relative Potency |
|------|-----------------|------------------|
| Prednisone | 5 mg | 1.0 (reference) |
| Prednisolone | 5 mg | 1.0 |
| Methylprednisolone | 4 mg | 1.25 |
| Dexamethasone | 0.75 mg | 6.7 |
| Hydrocortisone | 20 mg | 0.25 |

The same extended basis applies — mass alone is insufficient.
