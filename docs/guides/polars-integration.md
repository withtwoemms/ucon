# Polars Integration

ucon provides `NumberColumn` for working with unit-aware Polars Series.

## Installation

```bash
pip install ucon[polars]
```

## NumberColumn

`NumberColumn` wraps a Polars Series with unit metadata.

### Creating NumberColumn

```python
import polars as pl
from ucon import units
from ucon.polars import NumberColumn

# From Polars Series
heights = NumberColumn(
    pl.Series([1.7, 1.8, 1.9, 2.0]),
    unit=units.meter
)

# From list
temperatures = NumberColumn([20, 21, 22, 23], unit=units.celsius)
```

### With uncertainty

```python
# Uniform uncertainty
measurements = NumberColumn(
    pl.Series([100, 200, 300]),
    unit=units.meter,
    uncertainty=0.5
)

# Per-element uncertainty
errors = pl.Series([0.1, 0.2, 0.15])
measurements = NumberColumn(
    pl.Series([100, 200, 300]),
    unit=units.meter,
    uncertainty=errors
)
```

## Conversion

```python
heights = NumberColumn(pl.Series([1.7, 1.8, 1.9]), unit=units.meter)

# Convert to feet
heights_ft = heights.to(units.foot)
print(heights_ft)  # <NumberColumn [5.577, 5.906, 6.234] ft>
```

## Arithmetic

```python
a = NumberColumn(pl.Series([1, 2, 3]), unit=units.meter)
b = NumberColumn(pl.Series([4, 5, 6]), unit=units.meter)

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
heights = NumberColumn(pl.Series([1.5, 1.7, 1.8, 2.0]), unit=units.meter)

# Compare with scalar
tall = heights > 1.8
# Series([False, False, False, True])

# Filter using Polars
filtered = heights.series.filter(heights > 1.75)
```

## Reduction Operations

```python
heights = NumberColumn(pl.Series([1.7, 1.8, 1.9, 2.0]), unit=units.meter)

total = heights.sum()   # <7.4 m>
avg = heights.mean()    # <1.85 m>
std = heights.std()     # std deviation
minimum = heights.min() # <1.7 m>
maximum = heights.max() # <2.0 m>
```

## Indexing

```python
heights = NumberColumn(pl.Series([1.7, 1.8, 1.9]), unit=units.meter)

# By position
first = heights[0]  # <1.7 m> (Number)

# Slice
subset = heights[1:]  # NumberColumn
```

## Converting to List

```python
heights = NumberColumn(pl.Series([1.7, 1.8, 1.9]), unit=units.meter)

# Convert to list of Number instances
numbers = heights.to_list()
for n in numbers:
    print(n)  # <1.7 m>, <1.8 m>, <1.9 m>
```

## Example: Data Analysis Workflow

```python
import polars as pl
from ucon import units
from ucon.polars import NumberColumn

# Create DataFrame
df = pl.DataFrame({
    'name': ['Alice', 'Bob', 'Charlie'],
    'height_cm': [170.0, 180.0, 175.0],
    'weight_kg': [65.0, 80.0, 70.0]
})

# Extract columns with units
heights = NumberColumn(df['height_cm'], unit=units.centimeter)
weights = NumberColumn(df['weight_kg'], unit=units.kilogram)

# Convert
heights_m = heights.to(units.meter)

# Statistical analysis
print(f"Mean height: {heights_m.mean()}")
print(f"Mean weight: {weights.mean()}")

# Filter with comparison
tall_mask = heights > 175
tall_people = df.filter(tall_mask)
```

## Polars vs Pandas

| Feature | Polars (NumberColumn) | Pandas (NumberSeries) |
|---------|----------------------|----------------------|
| Label indexing | Position only | Labels and position |
| Accessor | Not available | `.ucon` accessor |
| Speed | Faster for large data | Good for small-medium |
| Memory | More efficient | Standard pandas |

Choose Polars when:
- Working with large datasets
- Performance is critical
- You prefer Polars' API

Choose Pandas when:
- You need the `.ucon` accessor
- Working with existing pandas workflows
- You need label-based indexing
