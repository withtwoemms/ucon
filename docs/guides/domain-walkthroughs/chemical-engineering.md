# Chemical Engineering

This walkthrough demonstrates dimensional analysis for chemical engineering calculations---a domain where stoichiometry chains, molar conversions, and logarithmic measures like pH demand rigorous unit tracking.

Each example shows two approaches:

- **Python API** --- Direct use of ucon in your code
- **MCP Server** --- Via AI agents like Claude

## Why Dimensional Analysis Matters

Chemical engineering calculations chain through multiple conversion factors: mass to moles (via molar mass), moles to concentration (via volume), concentration to pH (via logarithm). A single unit error in a stoichiometry chain propagates through every downstream step. Dimensional analysis catches these errors at each link.

---

## Solution Preparation

**Problem:** Calculate the mass of NaOH required to prepare 500 mL of 0.1 M solution. The molar mass of NaOH is 40.00 g/mol.

### Python API

```python
from ucon import units, Scale

mg = Scale.milli * units.gram
mL = Scale.milli * units.liter
mol_per_liter = units.mole / units.liter

# Givens
target_concentration = mol_per_liter(0.1)  # 0.1 M
target_volume = mL(500)                     # 500 mL
molar_mass = (units.gram / units.mole)(40.00)  # 40.00 g/mol

# Chain: concentration x volume = moles, moles x molar_mass = mass
moles_needed = target_concentration * target_volume
print(moles_needed)  # <0.05 mol>

mass_needed = moles_needed * molar_mass
print(mass_needed)  # <2.0 g>
```

### MCP Server

```python
compute(
    initial_value=0.1,
    initial_unit="mol/L",
    factors=[
        {"value": 500, "numerator": "mL", "denominator": "1000 mL/L"},
        {"value": 40.00, "numerator": "g", "denominator": "mol"},
    ]
)
```

**Step trace:**

| Step | Factor | Dimension | Result |
|------|--------|-----------|--------|
| 0 | 0.1 mol/L | concentration | 0.1 mol/L |
| 1 | x (500 mL / 1000 mL/L) | amount | 0.05 mol |
| 2 | x (40.00 g / mol) | mass | **2.0 g** |

---

## pH and Concentration

**Problem:** Given a hydrogen ion concentration of 1 x 10^-3 mol/L (vinegar), find the pH. Then convert pH 7 back to concentration.

ucon models pH as a logarithmic unit with concentration dimension, using `LogMap` under the hood: pH = -log10([H+]).

### Python API

```python
from ucon import units

mol_per_liter = units.mole / units.liter

# Concentration to pH
vinegar = mol_per_liter(1e-3)
ph = vinegar.to(units.pH)
print(ph)  # <3.0 pH>

# pH to concentration
neutral = units.pH(7.0)
concentration = neutral.to(mol_per_liter)
print(concentration)  # <1e-07 mol/L>
```

### MCP Server

```python
convert(value=1e-3, from_unit="mol/L", to_unit="pH")
# -> {"quantity": 3.0, "unit": "pH", "dimension": "concentration"}

convert(value=7.0, from_unit="pH", to_unit="mol/L")
# -> {"quantity": 1e-7, "unit": "mol/L", "dimension": "concentration"}
```

!!! note "Logarithmic Conversions"
    The pH conversion uses a `LogMap` internally: `pH = -1 * log10(x / 1 mol/L)`. The inverse (`ExpMap`) recovers concentration from pH. Both directions are exact round-trips.

---

## Reaction Yield with Uncertainty

**Problem:** A reaction produces 4.82 +/- 0.15 g of product from 5.00 +/- 0.02 g of limiting reagent (theoretical yield: 6.00 g based on stoichiometry). Calculate the percent yield with uncertainty.

### Python API

```python
from ucon import units

# Actual yield with measurement uncertainty
actual = units.gram(4.82, uncertainty=0.15)

# Theoretical yield from stoichiometry (known precisely)
theoretical = units.gram(6.00)

# Yield ratio: actual / theoretical
yield_ratio = actual / theoretical
print(yield_ratio)  # <0.8033... +/- 0.025 frac>

# Convert to percent
yield_pct = yield_ratio.to(units.percent)
print(yield_pct)  # <80.3 +/- 2.5 %>
```

Uncertainty propagates automatically through division via quadrature: the 0.15 g uncertainty on the numerator becomes a 2.5% uncertainty on the yield.

### MCP Server

```python
# Step 1: compute the ratio
compute(
    initial_value=4.82,
    initial_unit="g",
    factors=[
        {"value": 1, "numerator": "1", "denominator": "6.00 g"},
    ]
)
# -> {"quantity": 0.8033, "unit": "fraction", "dimension": "ratio"}

# Step 2: convert to percent
convert(value=0.8033, from_unit="fraction", to_unit="%")
# -> {"quantity": 80.33, "unit": "%", "dimension": "ratio"}
```

!!! note "Uncertainty in MCP"
    The MCP `compute` tool does not currently propagate uncertainty. For uncertainty-aware calculations, use the Python API directly.

---

## Multi-Step Dilution Chain

**Problem:** You have a 12 M stock solution of HCl. Prepare 250 mL of 0.5 M working solution. How much stock do you need?

This uses the dilution equation: C1 x V1 = C2 x V2, rearranged as V1 = C2 x V2 / C1.

### Python API

```python
from ucon import units, Scale

mL = Scale.milli * units.liter
mol_per_liter = units.mole / units.liter

# Givens
stock_conc = mol_per_liter(12.0)    # 12 M stock
target_conc = mol_per_liter(0.5)    # 0.5 M target
target_vol = mL(250)                 # 250 mL target volume

# Moles needed: target concentration x target volume
moles_needed = target_conc * target_vol
print(moles_needed)  # <0.125 mol>

# Volume of stock: moles / stock concentration
stock_vol = moles_needed / stock_conc
print(stock_vol)  # <0.01042 L> ~ 10.4 mL
```

### MCP Server

```python
compute(
    initial_value=0.5,
    initial_unit="mol/L",
    factors=[
        {"value": 250, "numerator": "mL", "denominator": "1000 mL/L"},
        {"value": 1, "numerator": "L", "denominator": "12 mol"},
    ]
)
```

**Step trace:**

| Step | Factor | Dimension | Result |
|------|--------|-----------|--------|
| 0 | 0.5 mol/L | concentration | 0.5 mol/L |
| 1 | x (250 mL / 1000 mL/L) | amount | 0.125 mol |
| 2 | x (1 L / 12 mol) | volume | **0.01042 L** (10.4 mL) |

---

## Dimensional Safety

ucon prevents nonsensical conversions in both interfaces.

### Moles Are Not Grams

```python
from ucon import units
from ucon.graph import ConversionNotFound

moles = units.mole(0.5)
try:
    moles.to(units.gram)  # mol -> g requires molar mass!
except ConversionNotFound:
    print("Cannot convert amount to mass without molar mass")
```

### Concentration Requires Volume

```python
mol_per_liter = units.mole / units.liter

concentration = mol_per_liter(0.1)
try:
    concentration.to(units.gram)  # mol/L -> g makes no sense
except ConversionNotFound:
    print("Cannot convert concentration directly to mass")
```

### MCP Server

```python
convert(value=0.5, from_unit="mol", to_unit="g")
# -> {
#     "error": "Dimension mismatch: amount_of_substance != mass",
#     "error_type": "dimension_mismatch",
#     "likely_fix": "Use molar mass to bridge amount_of_substance and mass"
# }
```

---

## Key Takeaways

1. **Stoichiometry is dimensional analysis** --- concentration x volume = moles, moles x molar mass = mass
2. **pH is a logarithmic unit** --- ucon handles the log/exp conversion automatically via `LogMap`
3. **Uncertainty propagates** through arithmetic --- measurement errors on mass become errors on yield
4. **Moles are not grams** --- you need molar mass to bridge amount and mass dimensions
5. **Both interfaces validate dimensions** --- errors are caught, not silently computed
