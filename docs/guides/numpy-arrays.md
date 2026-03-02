# NumPy Array Support

ucon provides `NumberArray` for working with numpy arrays of dimensioned quantities.

## Installation

```bash
pip install ucon[numpy]
```

## Creating NumberArrays

### From lists or numpy arrays

```python
from ucon import units
import numpy as np

# From list - uses callable syntax
heights = units.meter([1.7, 1.8, 1.9, 2.0])

# From numpy array
data = np.array([100, 200, 300])
distances = units.kilometer(data)

# Explicit construction
from ucon.numpy import NumberArray
temps = NumberArray([20, 21, 22, 23], unit=units.celsius)
```

### With uncertainty

```python
# Uniform uncertainty (same for all elements)
measurements = units.meter([1.0, 2.0, 3.0], uncertainty=0.01)

# Per-element uncertainty
errors = np.array([0.01, 0.02, 0.015])
measurements = NumberArray([1.0, 2.0, 3.0], unit=units.meter, uncertainty=errors)
```

## Vectorized Conversion

```python
heights = units.meter([1.7, 1.8, 1.9])

# Convert to feet
heights_ft = heights.to(units.foot)
print(heights_ft)  # <[5.577, 5.906, 6.234] ft>

# Uncertainty is propagated
temps = units.celsius([20, 21, 22], uncertainty=0.5)
temps_f = temps.to(units.fahrenheit)
# Uncertainty is scaled appropriately
```

## Arithmetic Operations

All arithmetic preserves units and propagates uncertainty.

```python
a = units.meter([1, 2, 3])
b = units.meter([4, 5, 6])

# Addition/subtraction (same unit required)
c = a + b  # <[5, 7, 9] m>
d = b - a  # <[3, 3, 3] m>

# Multiplication/division
area = a * b  # units are combined: m^2
speed = a / units.second([1, 2, 3])  # m/s

# Scalar operations
doubled = a * 2  # <[2, 4, 6] m>
```

### Broadcasting

NumPy broadcasting is supported:

```python
# (2, 3) + (3,) broadcasting
matrix = NumberArray([[1, 2, 3], [4, 5, 6]], unit=units.meter)
row = NumberArray([10, 20, 30], unit=units.meter)
result = matrix + row  # [[11, 22, 33], [14, 25, 36]] m
```

## Comparison Operators

Comparisons return boolean arrays for filtering:

```python
heights = units.meter([1.5, 1.7, 1.8, 2.0, 2.1])

# Compare with scalar
tall = heights > 1.8
# array([False, False, False, True, True])

# Compare with Number
threshold = units.meter(1.75)
above_threshold = heights >= threshold

# Use for filtering
filtered = heights.quantities[heights > 1.8]
```

## Indexing and Iteration

```python
heights = units.meter([1.7, 1.8, 1.9])

# Scalar index returns Number
first = heights[0]  # <1.7 m>

# Slice returns NumberArray
subset = heights[1:]  # <[1.8, 1.9] m>

# Iterate as Numbers
for h in heights:
    print(h)  # prints each as <Number>
```

## Reduction Operations

```python
heights = units.meter([1.7, 1.8, 1.9, 2.0])

total = heights.sum()   # <7.4 m>
avg = heights.mean()    # <1.85 m>
std = heights.std()     # <0.129... m>
minimum = heights.min() # <1.7 m>
maximum = heights.max() # <2.0 m>
```

### Uncertainty in Reductions

```python
# With uniform uncertainty
data = units.meter([1, 2, 3, 4], uncertainty=0.1)

total = data.sum()
# uncertainty: 0.1 * sqrt(4) = 0.2

avg = data.mean()
# uncertainty: 0.1 / sqrt(4) = 0.05
```

## N-Dimensional Arrays

NumberArray supports arrays of any dimension:

```python
# 2D array
grid = NumberArray(
    [[1, 2, 3],
     [4, 5, 6]],
    unit=units.meter
)
print(grid.shape)  # (2, 3)
print(grid.ndim)   # 2

# Index by row
row = grid[0]  # <[1, 2, 3] m>

# Index by element
element = grid[0, 1]  # <2 m> (Number)
```

## Integration with NumPy

```python
import numpy as np

heights = units.meter([1.7, 1.8, 1.9])

# Convert to raw numpy array
arr = np.asarray(heights)

# Use numpy functions on quantities
mean_val = np.mean(heights.quantities)
```

## Performance Tips

NumberArray is designed for correctness first, but performs well for batch operations.

### What's Fast

| Operation | Performance |
|-----------|-------------|
| Creation from ndarray | Essentially free (~0.001ms) - just wraps the array |
| Addition/subtraction | Excellent - often faster than raw NumPy at scale |
| Reductions (sum, mean) | Excellent - comparable to NumPy |
| Throughput | 100M+ elements/sec for conversions |

### What Has Fixed Costs

Conversions have small fixed costs for unit checking and graph lookup. These are cached after the first conversion, so repeated conversions of the same unit pair are faster (~1.5x speedup from cache).

### Best Practices

**Pass ndarrays, not lists:**

```python
# Slower - must convert list to array
heights = units.meter([1.7, 1.8, 1.9, 2.0])

# Faster - wraps existing array directly
data = np.array([1.7, 1.8, 1.9, 2.0])
heights = units.meter(data)
```

**Pre-convert units before loops:**

```python
# Slower - converts on every iteration
for sample in samples:
    value_ft = sample.to(units.foot)
    process(value_ft)

# Faster - convert once, iterate on result
samples_ft = samples.to(units.foot)
for value in samples_ft:
    process(value)
```

**Batch operations over element-wise:**

```python
# Slower - N separate operations
results = [x.to(units.foot) for x in measurements]

# Faster - single vectorized operation
results = measurements.to(units.foot)
```

### Uncertainty Propagation Cost

Multiplication with uncertainty is more expensive due to quadrature error propagation. If you don't need per-operation uncertainty, consider:

```python
# Propagate uncertainty only at final result
a = NumberArray(data_a, unit=units.meter)  # no uncertainty
b = NumberArray(data_b, unit=units.meter)  # no uncertainty
result = a * b

# Add uncertainty estimate at the end if needed
final = NumberArray(result.quantities, unit=result.unit, uncertainty=estimated_error)
```

## Example: Scientific Data Analysis

```python
import numpy as np
from ucon import units

# Experimental measurements with uncertainty
measurements = units.meter(
    [10.2, 10.5, 10.3, 10.4, 10.6],
    uncertainty=0.1
)

# Statistical analysis
mean = measurements.mean()
std = measurements.std()

print(f"Mean: {mean}")
print(f"Std Dev: {std}")

# Convert to different units
measurements_cm = measurements.to(units.centimeter)

# Filter outliers
mask = abs(measurements.quantities - mean.quantity) < 2 * std.quantity
filtered = measurements.quantities[mask]
```
