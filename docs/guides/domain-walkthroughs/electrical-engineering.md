# Electrical Engineering

This walkthrough demonstrates dimensional analysis for electrical engineering calculations---a domain where logarithmic units (decibels), power variants (real, apparent, reactive), and reference-level conversions demand rigorous unit tracking.

Each example shows two approaches:

- **Python API** --- Direct use of ucon in your code
- **MCP Server** --- Via AI agents like Claude

## Why Dimensional Analysis Matters

Electrical engineering uses decibels pervasively, but not all decibels are the same. dBm references 1 mW (power), dBV references 1 V (voltage), and dBSPL references 20 uPa (pressure). Confusing dBm with dBW is a 30 dB error---a factor of 1000 in power. Meanwhile, real power (W), apparent power (VA), and reactive power (var) share the same SI dimension but represent physically distinct quantities.

---

## Power Conversions

**Problem:** A transmitter outputs 100 W. Express this in kilowatts, milliwatts, and horsepower.

### Python API

```python
from ucon import units, Scale

kW = Scale.kilo * units.watt
mW = Scale.milli * units.watt

power = units.watt(100)

# Scale conversions (no graph needed)
print(power.to(kW))            # <0.1 kW>
print(power.to(mW))            # <100000.0 mW>
print(power.to(units.horsepower))  # depends on graph edge
```

### MCP Server

```python
convert(value=100, from_unit="W", to_unit="kW")
# -> {"quantity": 0.1, "unit": "kW", "dimension": "power"}

convert(value=100, from_unit="W", to_unit="mW")
# -> {"quantity": 100000.0, "unit": "mW", "dimension": "power"}
```

---

## Decibel Conversions

Decibels are logarithmic units. ucon uses `LogMap` internally to handle the nonlinear conversion between linear and logarithmic scales.

### Watts to dBm

**Problem:** Express common power levels in dBm (decibel-milliwatts). dBm = 10 * log10(P / 1 mW).

#### Python API

```python
from ucon import units

# Key reference points
levels = [
    (1e-6, "1 uW (weak signal)"),
    (1e-3, "1 mW (0 dBm reference)"),
    (0.1,  "100 mW (WiFi router)"),
    (1.0,  "1 W (30 dBm)"),
    (100,  "100 W (FM broadcast)"),
]

for watts, description in levels:
    p = units.watt(watts)
    dbm = p.to(units.decibel_milliwatt)
    print(f"  {watts:8.0e} W = {dbm.quantity:7.1f} dBm  ({description})")
```

Output:

```
     1e-06 W =   -30.0 dBm  (1 uW (weak signal))
     1e-03 W =     0.0 dBm  (1 mW (0 dBm reference))
     1e-01 W =    20.0 dBm  (100 mW (WiFi router))
     1e+00 W =    30.0 dBm  (1 W (30 dBm))
     1e+02 W =    50.0 dBm  (100 W (FM broadcast))
```

#### MCP Server

```python
convert(value=0.001, from_unit="W", to_unit="dBm")
# -> {"quantity": 0.0, "unit": "dBm", "dimension": "power"}

convert(value=1.0, from_unit="W", to_unit="dBm")
# -> {"quantity": 30.0, "unit": "dBm", "dimension": "power"}
```

### dBm Back to Watts

The conversion is bidirectional:

```python
from ucon import units

dbm = units.decibel_milliwatt(23)  # 23 dBm (typical cell phone)
watts = dbm.to(units.watt)
print(watts)  # <0.2 W> (200 mW)
```

```python
# MCP
convert(value=23, from_unit="dBm", to_unit="W")
# -> {"quantity": 0.19953, "unit": "W", "dimension": "power"}
```

### Voltage to dBV

**Problem:** Express 3.5 V in dBV. Note that voltage uses the 20*log10 scale (amplitude), not 10*log10 (power).

#### Python API

```python
from ucon import units

signal = units.volt(3.5)
dbv = signal.to(units.decibel_volt)
print(dbv)  # <10.88 dBV>

# Round-trip
back = dbv.to(units.volt)
print(back)  # <3.5 V>
```

#### MCP Server

```python
convert(value=3.5, from_unit="V", to_unit="dBV")
# -> {"quantity": 10.88, "unit": "dBV", "dimension": "voltage"}
```

!!! note "Power vs Amplitude"
    dBm and dBW use `10 * log10` (power quantities). dBV and dBSPL use `20 * log10` (amplitude quantities). ucon handles this distinction automatically based on the reference unit's dimension.

---

## dBW vs dBm

**Problem:** Compare dBW and dBm for the same power level. The relationship is dBW = dBm - 30.

### Python API

```python
from ucon import units

for watts in [0.001, 0.1, 1.0, 10.0, 1000.0]:
    p = units.watt(watts)
    dbw = p.to(units.decibel_watt)
    dbm = p.to(units.decibel_milliwatt)
    print(f"  {watts:7.3f} W = {dbw.quantity:6.1f} dBW = {dbm.quantity:6.1f} dBm")
```

Output:

```
    0.001 W =  -30.0 dBW =    0.0 dBm
    0.100 W =  -10.0 dBW =   20.0 dBm
    1.000 W =    0.0 dBW =   30.0 dBm
   10.000 W =   10.0 dBW =   40.0 dBm
 1000.000 W =   30.0 dBW =   60.0 dBm
```

---

## KOQ: Real vs Apparent vs Reactive Power

Real power (W), apparent power (VA), and reactive power (var) all have the same SI dimension (ML^2T^-3). In standard SI, they are indistinguishable. ucon's Kind-of-Quantity (KOQ) system, available via the MCP server, disambiguates them.

**Problem:** A server rack draws 2.5 kVA apparent power at 0.85 power factor. Calculate real power and reactive power. Prevent accidentally adding W to var.

### MCP Server

```python
# Declare that we're computing real power
declare_computation(
    quantity_kind="real_power",
    expected_unit="W",
    context={"power_factor": "0.85"}
)

# Real power = apparent power x power factor
compute(
    initial_value=2500,
    initial_unit="W",
    factors=[
        {"value": 0.85, "numerator": "1", "denominator": "1"},
    ]
)
# -> {"quantity": 2125, "unit": "W"}

# Validate the result
validate_result(
    value=2125,
    unit="W",
    reasoning="Calculated P = S * pf = 2500 VA * 0.85 = 2125 W"
)
# -> {"valid": true, "declared_kind": "real_power"}
```

KOQ prevents confusing power types:

```python
# Declare reactive power computation
declare_computation(
    quantity_kind="reactive_power",
    expected_unit="var"
)

# If you accidentally validate with real_power kind:
validate_result(
    value=1320,
    unit="W",
    declared_kind="real_power",
    reasoning="This is actually reactive power Q = S * sin(acos(pf))"
)
# -> {"valid": false, "warning": "Result declared as real_power but reasoning suggests reactive_power"}
```

!!! note "KOQ Is an MCP Feature"
    Kind-of-Quantity discrimination is available through the MCP server's `declare_computation` and `validate_result` tools. The core Python library tracks dimensions but does not distinguish between dimensionally identical quantity kinds. For Python-level KOQ, use extended bases (see [Domain-Specific Bases](../domain-bases/index.md)).

---

## Dimensional Safety

### Watts Are Not Volts

```python
from ucon import units

power = units.watt(100)
try:
    power.to(units.volt)
except Exception:
    print("Cannot convert power to voltage --- different dimensions")
```

### dBm Is Not dBV

```python
from ucon import units

signal_power = units.decibel_milliwatt(23)
try:
    signal_power.to(units.decibel_volt)
except Exception:
    print("Cannot convert dBm to dBV --- power != voltage")
```

### MCP Server

```python
convert(value=23, from_unit="dBm", to_unit="dBV")
# -> {
#     "error": "Dimension mismatch: power != voltage",
#     "error_type": "dimension_mismatch",
#     "likely_fix": "Use impedance to bridge power and voltage (P = V^2/R)"
# }
```

---

## Key Takeaways

1. **Decibels are logarithmic units** --- ucon handles the log/exp conversion via `LogMap` automatically
2. **dBm != dBW != dBV** --- each has a different reference level and dimension
3. **Power vs amplitude scaling** --- 10*log10 for power (dBm, dBW), 20*log10 for amplitude (dBV, dBSPL)
4. **KOQ disambiguates** --- W, VA, and var share a dimension but are distinct quantity kinds
5. **Both interfaces validate dimensions** --- power != voltage, dBm != dBV
