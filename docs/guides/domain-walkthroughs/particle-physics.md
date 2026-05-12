# Particle Physics

Particle physicists work in **natural units** — a system where
`ℏ = c = 1` and every quantity becomes an energy expressed in electron-volts.
That's a different basis from the SI you'd use to engineer the detector. A
particle-physics calculation usually has to cross between the two.

This walkthrough uses ucon's v1.8 `UnitSystem` to keep a natural-units
calculation isolated from the surrounding SI pipeline. Every example threads
the same `UnitSystem` through three entry points: parsing, conversion, and
dimensional checking.

For the rationale, see
[UnitSystem Value Type](../../architecture/unitsystem-value-type.md). For the
isolation pattern, see
[Building Isolated UnitSystems](../building-isolated-unitsystems.md).

---

## Setting Up: Two Systems

```python
from ucon.system import UnitSystem, use
from ucon import units

# SI snapshot for detector engineering
si_system = UnitSystem.from_globals()

# Natural-units snapshot for particle calculations
# (NATURAL basis is built in to v1.8; ucon.units exports the NATURAL_TO_SI
# transform, so cross-basis conversions are pre-wired.)
natural_system = UnitSystem.from_globals()  # same registries, ready for use(...)
```

Both `UnitSystem`s share the same underlying registries — the difference is
which `BaseUnits` you treat as canonical when you ask "express this in base
form". `BaseUnits` for SI is `units.si`. For a pure particle-physics
calculation you'll often work in `electron_volt` and let the conversion graph
do the rest.

---

## Calculation 1: Pion Rest Energy

The neutral pion has a rest mass of about 135 MeV/c². In natural units it's
just 135 MeV. In SI it's a mass in kilograms.

=== "Python API"

    ```python
    from ucon import Scale, units, parse
    from ucon.system import use

    with use(natural_system):
        # Particle physicist's mental model: m = 135 MeV
        m_natural = parse("135 MeV")
        print(m_natural)            # <135 MeV>

    with use(si_system):
        # Detector engineer's view: same particle, kg
        m_si = m_natural.to(Scale.kilo * units.gram, system=si_system)
        print(m_si)                 # ~2.406e-28 kg
    ```

=== "MCP Server"

    ```
    convert(value=135, from_unit="MeV", to_unit="kg")
    # → 2.406e-28 kg
    ```

The `system=` kwarg on `.to(...)` lets you cross between snapshots without
nesting `use(...)` blocks. Threading explicitly is preferred when one call
needs a different world than its surroundings.

---

## Calculation 2: Branching Ratio with Dimensional Safety

Branching ratios are dimensionless — the ratio of partial widths Γᵢ / Γ_total.
A common bug is forgetting to convert one width into the same units as the
other before dividing. `enforce_dimensions` catches it.

=== "Python API"

    ```python
    from ucon import enforce_dimensions, parse, Dimension
    from ucon.system import use

    @enforce_dimensions(
        partial=Dimension.from_components(name="energy", L=2, M=1, T=-2),
        total=Dimension.from_components(name="energy", L=2, M=1, T=-2),
        returns=None,  # dimensionless ratio
    )
    def branching_ratio(partial, total):
        return partial / total

    with use(natural_system):
        gamma_partial = parse("83.4 keV")
        gamma_total   = parse("167   keV")

        # OK: both widths are energies
        br = branching_ratio(partial=gamma_partial, total=gamma_total)
        print(float(br.quantity))   # 0.499...

        # WRONG: passing a cross-section here raises DimensionMismatch
        sigma = parse("40 mbarn")
        branching_ratio(partial=sigma, total=gamma_total)
        # → ucon.core.DimensionMismatch
    ```

=== "MCP Server"

    ```
    declare_computation(quantity_kind="dimensionless", expected_unit="")
    compute(initial_value=83.4, initial_unit="keV",
            factors=[{"value": 1, "numerator": "ea", "denominator": "167 keV"}],
            expected_unit="")
    ```

`enforce_dimensions` reads the active `UnitSystem` for dimension lookup. If
you'd registered a custom dimension on `natural_system` that `si_system`
doesn't have, the decorator would see only what the active snapshot provides.

---

## Calculation 3: Cross-Section in barns ↔ cm²

Particle physicists report cross-sections in **barns** (1 barn = 10⁻²⁸ m²).
Detector simulations expect cm² (CGS). Two non-SI scales, same dimension.

=== "Python API"

    ```python
    from ucon import units
    from ucon.system import use

    with use(natural_system):
        sigma = parse("40 mbarn")
        # In particle-physics mental units
        print(sigma)                       # <40 mbarn>

    with use(si_system):
        # Convert to detector-friendly cm²
        sigma_cm2 = sigma.to(units.centimeter ** 2, system=si_system)
        print(sigma_cm2)                   # ~4.0e-26 cm²
    ```

=== "MCP Server"

    ```
    convert(value=40, from_unit="mbarn", to_unit="cm^2")
    # → 4.0e-26 cm^2
    ```

This conversion stays within the SI basis (`barn` is registered as an area
unit). No `basis_transform` is needed — the dual graph picks `barn → m² →
cm²`.

---

## Calculation 4: Compton Wavelength via Natural-Units Cross-Basis

The Compton wavelength of the electron is λ_C = h / (m_e c). The natural-units
identity λ_C = 1 / m_e (in units of ℏ = c = 1) collapses that to a single
inverse-mass.

=== "Python API"

    ```python
    from ucon.system import use
    from ucon import parse, units

    with use(natural_system):
        m_e = parse("0.5110 MeV")
        # In natural units, 1/m_e *is* a length
        # ucon's NATURAL basis encodes this: NATURAL has a single component
        # (energy). Inverse energy maps to SI length via NATURAL_TO_SI.
        lam_natural = parse("1 / 0.5110 MeV")   # natural-units expression

    # Cross to SI for the geometric interpretation
    lam_si = lam_natural.to(units.meter, system=si_system)
    print(lam_si)        # ~3.86e-13 m  (the reduced Compton wavelength)
    ```

=== "MCP Server"

    ```
    convert(value=1, from_unit="1/(0.5110 MeV)", to_unit="m")
    # → 3.86e-13 m
    ```

The basis crossing happens at `.to(...)`. `natural_system` and `si_system`
share the same `basis_graph`, which contains the `NATURAL_TO_SI` transform
shipped with v1.8 — that's what lets the BFS find a path between an inverse
energy in NATURAL and a length in SI.

---

## Calculation 5: Lifetime ↔ Width (Heisenberg)

Particle lifetimes and decay widths are related by τ = ℏ / Γ. In natural
units it's just τ = 1 / Γ.

=== "Python API"

    ```python
    with use(natural_system):
        gamma = parse("2.5 GeV")           # Z boson width
        tau_nat = parse("1 / 2.5 GeV")
        tau_si  = tau_nat.to(units.second, system=si_system)
        print(tau_si)                      # ~2.6e-25 s
    ```

=== "MCP Server"

    ```
    convert(value=1, from_unit="1/(2.5 GeV)", to_unit="s")
    # → 2.6e-25 s
    ```

Again the basis crossing happens at the SI conversion — natural-units inverse
energy is identified with SI time via `NATURAL_TO_SI`.

---

## Pinning a Run

For a full analysis run, snapshot once at startup and pin it through the
pipeline. Two snapshots from `from_globals()` compare equal, so dict-keying or
hashing the system stays stable:

```python
def run_analysis(events, *, system):
    """Pure: nothing about this function reads module-level state."""
    with use(system):
        for ev in events:
            yield analyze(ev)

if __name__ == "__main__":
    natural_system = UnitSystem.from_globals()
    results = list(run_analysis(load_events(), system=natural_system))
```

Every dimension lookup, every parse, every conversion sees the same snapshot.
If a co-resident library mutates the global registries mid-run, your pinned
snapshot continues to use the registry references it captured at construction.

---

## Key Takeaways

1. **Two snapshots, one process.** `UnitSystem.from_globals()` is cheap and
   safe to call per pipeline. Particle calculations live in one snapshot,
   engineering in another.

2. **Cross-basis is automatic.** v1.8 ships `NATURAL_TO_SI`. The conversion
   graph's BFS finds paths across the basis edge without per-call setup.

3. **`system=` for one-off crossings.** Use `use(...)` for blocks. Use
   `system=` when one call wants a different world than its surroundings.

4. **`enforce_dimensions` reads the active system.** Dimension equality is
   checked against the snapshot's registries — register a custom dimension on
   your snapshot and the decorator sees it without polluting globals.

5. **Snapshots are values.** Two `from_globals()` calls back-to-back compare
   equal. Pin one at startup and pass it as a parameter, not a global.

---

## Further Reading

- [Building Isolated UnitSystems](../building-isolated-unitsystems.md) — the
  pattern this walkthrough applies
- [UnitSystem Value Type](../../architecture/unitsystem-value-type.md) — why
  the snapshot pattern works
- [Natural Units](../natural-units.md) — the NATURAL basis in depth
- [Domain-Specific Bases](../domain-bases/index.md) — the other built-in bases
