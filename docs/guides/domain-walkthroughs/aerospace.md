# Aerospace

This walkthrough demonstrates dimensional analysis for aerospace engineering calculations---a domain where mixed unit systems have caused catastrophic failures.

Each example shows two approaches:

- **Python API** --- Direct use of ucon in your code
- **MCP Server** --- Via AI agents like Claude

## Why Dimensional Analysis Matters

In 1999, NASA's Mars Climate Orbiter was lost because one team used pound-force-seconds while another expected newton-seconds. The $327 million spacecraft entered the atmosphere at the wrong altitude and disintegrated. Dimensional analysis would have caught the mismatch at the interface between the two teams.

Aerospace engineering routinely mixes SI and US customary units: thrust in lbf, mass in slugs, speed in knots, altitude in feet, distance in nautical miles. Every interface is a potential unit error.

---

## Loading Domain Units

ucon ships with SI and common imperial units. Domain-specific units like slugs, knots, and nautical miles are loaded via `UnitPackage` from a TOML file.

### The TOML Package

```toml
# aerospace.ucon.toml
name = "aerospace"
version = "1.0.0"
description = "Aerospace and aviation units"

[[units]]
name = "slug"
dimension = "mass"
aliases = ["slug"]

[[units]]
name = "knot"
dimension = "velocity"
aliases = ["kn", "kt", "knots"]

[[units]]
name = "nautical_mile"
dimension = "length"
aliases = ["nmi", "NM"]

[[units]]
name = "poundal"
dimension = "force"
aliases = ["pdl"]

[[edges]]
src = "slug"
dst = "kilogram"
factor = 14.5939

[[edges]]
src = "nautical_mile"
dst = "meter"
factor = 1852

[[edges]]
src = "knot"
dst = "meter/second"
factor = 0.514444

[[edges]]
src = "poundal"
dst = "newton"
factor = 0.138255
```

### Python API

```python
from ucon import get_default_graph, get_unit_by_name, Number
from ucon.packages import load_package
from ucon.graph import using_graph

# Load the aerospace unit package
package = load_package("aerospace.ucon.toml")
graph = get_default_graph().with_package(package)

with using_graph(graph):
    slug = get_unit_by_name("slug")
    knot = get_unit_by_name("knot")
    nmi = get_unit_by_name("nautical_mile")

    print(slug.dimension)   # <MASS>
    print(knot.dimension)   # <VELOCITY>
    print(nmi.dimension)    # <LENGTH>
```

### MCP Server

```python
# Units are defined inline per session
define_unit(name="slug", dimension="mass", aliases=["slug"])
define_conversion(src="slug", dst="kg", factor=14.5939)

define_unit(name="knot", dimension="velocity", aliases=["kn", "kt"])
define_conversion(src="knot", dst="m/s", factor=0.514444)

define_unit(name="nautical_mile", dimension="length", aliases=["nmi", "NM"])
define_conversion(src="nautical_mile", dst="m", factor=1852)
```

---

## Specific Impulse

**Problem:** A rocket engine produces 2,000,000 lbf of thrust with a propellant mass flow rate of 1,700 lb/s. Calculate the specific impulse in seconds.

Specific impulse (Isp) = thrust / (mass flow rate x g0), where g0 = 9.80665 m/s^2. In US customary units with thrust in lbf and flow rate in lb/s, g0 cancels and Isp = thrust (lbf) / flow rate (lb/s).

### Python API

```python
from ucon import units, Number

# In US customary: Isp = F / mdot (when F in lbf, mdot in lb/s)
thrust = units.pound_force(2_000_000)
flow_rate = (units.pound / units.second)(1700)

# Isp as a force-per-(mass/time) ratio
isp = thrust / flow_rate
print(isp)  # <1176.47 lbf*s/lb>

# In US customary, lbf*s/lb simplifies to seconds (since lbf = lb * g0)
print(f"Isp = {isp.quantity:.1f} s")
```

### MCP Server

```python
compute(
    initial_value=2_000_000,
    initial_unit="lbf",
    factors=[
        {"value": 1, "numerator": "s", "denominator": "1700 lb"},
    ]
)
# -> {"quantity": 1176.47, "unit": "lbf*s/lb"}
```

**Step trace:**

| Step | Factor | Result |
|------|--------|--------|
| 0 | 2,000,000 lbf | 2,000,000 lbf |
| 1 | x (1 s / 1700 lb) | **1176.5 lbf*s/lb** |

---

## Cross-System Conversion

**Problem:** An aircraft is cruising at 450 knots. Express this in m/s and mph.

### Python API

```python
from ucon import get_default_graph, get_unit_by_name, Number
from ucon.packages import load_package
from ucon.graph import using_graph

package = load_package("aerospace.ucon.toml")
graph = get_default_graph().with_package(package)

with using_graph(graph):
    knot = get_unit_by_name("knot")
    meter_per_second = get_unit_by_name("meter/second")
    mile_per_hour = get_unit_by_name("mile/hour")

    groundspeed = Number(450, knot)

    # Knots to m/s (via graph edge)
    gs_si = groundspeed.to(meter_per_second, graph=graph)
    print(gs_si)  # <231.5 m/s>

    # Knots to mph (via knot -> m/s -> mile/hour)
    gs_mph = groundspeed.to(mile_per_hour, graph=graph)
    print(gs_mph)  # <518.0 mi/h>
```

### MCP Server

```python
# After defining knot (see above)
convert(value=450, from_unit="kn", to_unit="m/s")
# -> {"quantity": 231.5, "unit": "m/s", "dimension": "velocity"}

convert(value=450, from_unit="kn", to_unit="mi/h")
# -> {"quantity": 518.0, "unit": "mi/h", "dimension": "velocity"}
```

---

## Flight Distance

**Problem:** A transatlantic flight covers 3,450 nautical miles. Express this in kilometers.

### Python API

```python
from ucon import get_default_graph, get_unit_by_name, Number, Scale
from ucon.packages import load_package
from ucon.graph import using_graph

package = load_package("aerospace.ucon.toml")
graph = get_default_graph().with_package(package)

with using_graph(graph):
    nmi = get_unit_by_name("nautical_mile")
    km = Scale.kilo * get_unit_by_name("meter")

    distance = Number(3450, nmi)
    distance_km = distance.to(km, graph=graph)
    print(distance_km)  # <6389.4 km>
```

### MCP Server

```python
convert(value=3450, from_unit="nmi", to_unit="km")
# -> {"quantity": 6389.4, "unit": "km", "dimension": "length"}
```

---

## Dimensional Safety

ucon prevents the exact class of error that destroyed Mars Climate Orbiter.

### Force Is Not Mass

```python
from ucon import units
from ucon.graph import DimensionMismatch

thrust = units.newton(1000)
try:
    # Treating force as mass is a dimension error
    thrust.to(units.kilogram)
except Exception:
    print("Cannot convert force to mass --- different dimensions")
```

### MCP Server

```python
convert(value=1000, from_unit="N", to_unit="kg")
# -> {
#     "error": "Dimension mismatch: force != mass",
#     "error_type": "dimension_mismatch",
#     "likely_fix": "Use a force unit like N or lbf"
# }
```

!!! warning "The Mars Climate Orbiter Lesson"
    The MCO failure was not a conversion error---it was a *missing* conversion. One team output impulse in lbf*s, the other consumed it as N*s. Dimensional analysis at the interface would have flagged the mismatch immediately: both are force*time, but the numeric values differ by a factor of 4.45.

---

## Key Takeaways

1. **Domain units load from TOML** --- `UnitPackage` extends the graph without modifying core definitions
2. **Cross-system conversion chains automatically** --- knot -> m/s -> mph follows graph edges
3. **Aliases resolve transparently** --- `kn`, `kt`, and `knots` all resolve to the same unit
4. **Force is not mass** --- ucon prevents the MCO class of error by tracking dimensions
5. **`with_package()` is non-destructive** --- the base graph is unchanged; the extended graph is scoped
