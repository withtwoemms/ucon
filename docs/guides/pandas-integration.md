# Pandas Integration

ucon provides `NumberSeries` and a pandas accessor for working with unit-aware DataFrame columns.

## Installation

```bash
pip install ucon[pandas]
```

## NumberSeries

`NumberSeries` wraps a pandas Series with unit metadata.

### Creating NumberSeries

```python
import pandas as pd
from ucon import units
from ucon.pandas import NumberSeries

# From pandas Series
heights = NumberSeries(
    pd.Series([1.7, 1.8, 1.9, 2.0]),
    unit=units.meter
)

# From list
temperatures = NumberSeries([20, 21, 22, 23], unit=units.celsius)
```

### With uncertainty

```python
# Uniform uncertainty
measurements = NumberSeries(
    pd.Series([100, 200, 300]),
    unit=units.meter,
    uncertainty=0.5
)

# Per-element uncertainty
errors = pd.Series([0.1, 0.2, 0.15])
measurements = NumberSeries(
    pd.Series([100, 200, 300]),
    unit=units.meter,
    uncertainty=errors
)
```

## Pandas Accessor

The `.ucon` accessor enables unit operations directly on pandas Series:

```python
import pandas as pd
from ucon import units

df = pd.DataFrame({
    'height_m': [1.7, 1.8, 1.9],
    'weight_kg': [65, 70, 75]
})

# Attach units and convert
heights = df['height_m'].ucon(units.meter)
heights_ft = heights.to(units.foot)

# Or use with_unit
heights = df['height_m'].ucon.with_unit(units.meter, uncertainty=0.01)
```

## Conversion

```python
heights = NumberSeries(pd.Series([1.7, 1.8, 1.9]), unit=units.meter)

# Convert to feet
heights_ft = heights.to(units.foot)
print(heights_ft)  # <NumberSeries [5.577, 5.906, 6.234] ft>
```

## Arithmetic

```python
a = NumberSeries(pd.Series([1, 2, 3]), unit=units.meter)
b = NumberSeries(pd.Series([4, 5, 6]), unit=units.meter)

# Addition (same unit required)
c = a + b

# Multiplication
area = a * b  # units: m^2

# Scalar operations
doubled = a * 2
```

## Comparison Operators

Comparisons return boolean Series for filtering:

```python
heights = NumberSeries(pd.Series([1.5, 1.7, 1.8, 2.0]), unit=units.meter)

# Compare with scalar
tall = heights > 1.8
# Series([False, False, False, True])

# Filter
filtered = heights.series[heights > 1.75]
```

## Reduction Operations

```python
heights = NumberSeries(pd.Series([1.7, 1.8, 1.9, 2.0]), unit=units.meter)

total = heights.sum()   # <7.4 m>
avg = heights.mean()    # <1.85 m>
std = heights.std()     # std deviation
minimum = heights.min() # <1.7 m>
maximum = heights.max() # <2.0 m>
```

## Indexing

```python
heights = NumberSeries(
    pd.Series([1.7, 1.8, 1.9], index=['alice', 'bob', 'charlie']),
    unit=units.meter
)

# By position
first = heights[0]  # <1.7 m> (Number)

# By label
bob_height = heights['bob']  # <1.8 m> (Number)

# Slice
subset = heights[1:]  # NumberSeries
```

## Converting to DataFrame

```python
heights = NumberSeries(pd.Series([1.7, 1.8, 1.9]), unit=units.meter)

# Convert to DataFrame with unit in column name
df = heights.to_frame()  # column: 'value (m)'

# With custom name
df = heights.to_frame(name='height')
```

## Example: Data Analysis Workflow

```python
import pandas as pd
from ucon import units

# Load data
df = pd.DataFrame({
    'name': ['Alice', 'Bob', 'Charlie'],
    'height_cm': [170, 180, 175],
    'weight_kg': [65, 80, 70]
})

# Attach units
heights = df['height_cm'].ucon(units.centimeter)
weights = df['weight_kg'].ucon(units.kilogram)

# Convert
heights_m = heights.to(units.meter)

# Calculate BMI (kg/m^2)
heights_m_sq = heights_m * heights_m
bmi = weights / heights_m_sq

# Statistical analysis
print(f"Mean height: {heights_m.mean()}")
print(f"Mean weight: {weights.mean()}")

# Filter
tall = heights > units.centimeter(175)
tall_people = df[tall.series]
```

## Performance Tips

- **Batch conversions**: Convert entire columns at once rather than row-by-row
- **Pre-convert before loops**: Call `.to()` once before iterating over values
- **Accessor overhead**: The `.ucon` accessor has minimal overhead, but for tight loops consider extracting to a NumberSeries first

```python
# Efficient - single conversion
heights_ft = df['height_m'].ucon(units.meter).to(units.foot)

# Less efficient - converts per row
for idx, row in df.iterrows():
    height_ft = units.meter(row['height_m']).to(units.foot)  # avoid this
```
