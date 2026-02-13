# SRE Error Budget & SLO Tracking Example

A comprehensive example demonstrating dimensional analysis for Site Reliability Engineering: SLO tracking, error budget management, burn rate calculations, and capacity planning.

## Overview

This example shows:

1. **Availability in multiple notations** — percent ↔ nines conversion
2. **Error budget calculations** — total, consumed, remaining, time-to-exhaustion
3. **Burn rate analysis** — detecting unsustainable consumption patterns
4. **Ratio/percentage handling** — error rates, availability, headroom
5. **Throughput dimensions** — requests/second for capacity planning
6. **Uncertainty as confidence intervals** — measurement precision from monitoring
7. **Alert threshold evaluation** — multi-dimensional alerting logic

## Files

- `config.yaml` — Service SLOs, current metrics, alert thresholds, capacity params
- `models.py` — Pydantic models with error budget computation methods
- `main.py` — Dashboard-style output with recommendations

## Usage

```bash
# Install dependencies
pip install pyyaml

# Run with default config
python main.py

# Run with custom config
python main.py /path/to/custom/config.yaml
```

## Example Output

```
============================================================
Service: payments-api (tier: critical)
============================================================

=== SLO Targets ===
  Availability:  <99.95 %> (<3.3 nines>)
  Latency p99:   < <200 ms>
  Error rate:    < <0.1 %>
  Throughput:    > <5000 Hz>

=== Current Measurements ===
  Availability:  <99.92 ± 0.01 %>
  Latency p99:   <180 ± 10 ms>
  Throughput:    <4800 ± 100 Hz>

=== SLO Compliance ===
  Availability   ✗ FAIL
  Latency p99    ✓ PASS
  Error rate     ✓ PASS
  Throughput     ✗ FAIL

=== Error Budget Analysis ===
  Window:           <30 day>
  Total budget:     <21.6 min>
  Consumed:         <17.28 min>
  Remaining:        <4.32 min> (<20 %>)
  Burn rate:        1.6x
  Time to exhaust:  <2.7 day>

=== Alert Status: ⚠ WARNING ===
```

## Key Patterns

### Availability Nines ↔ Percent

```python
availability: Percentage  # accepts %, nines, fraction

# In config:
target: { quantity: 99.95, unit: "%" }
# or
target: { quantity: 3.3, unit: "nines" }

# In code:
avail_pct = config.slos.availability.target.to(units.percent)
avail_nines = config.slos.availability.target.to(units.nines)
```

### Error Budget Calculations

```python
def total_error_budget(self) -> Number:
    """Total allowed downtime in the window."""
    budget_fraction = 1 - self.target.to(units.fraction).quantity
    return self.window * budget_fraction

def error_budget_consumed(self) -> Number:
    """Actual downtime so far."""
    actual_avail = self.current.availability.to(units.fraction).quantity
    downtime_fraction = 1 - actual_avail
    return self.current.window_elapsed * downtime_fraction
```

### Burn Rate

```python
def burn_rate(self) -> Number:
    """
    Burn rate = actual_consumption / expected_consumption

    1.0  = on track to use exactly the budget
    >1.0 = burning faster than sustainable
    <1.0 = under budget
    """
    window_fraction = elapsed / total_window
    expected = total_budget * window_fraction
    actual = consumed
    return actual / expected
```

### Time to Exhaustion

```python
def time_to_exhaustion(self) -> Number | None:
    """At current burn rate, when does budget hit zero?"""
    remaining = self.error_budget_remaining()
    burn = self.burn_rate().quantity

    budget_per_day = total_budget / window_days
    days_remaining = remaining / (budget_per_day * burn)
    return units.day(days_remaining)
```

### Capacity Planning with Throughput

```python
class CapacityConfig(BaseModel):
    current_instances: int
    requests_per_instance: PositiveNumber[Dimension.frequency]
    headroom_target: Percentage

    @property
    def total_capacity(self) -> Number:
        return self.requests_per_instance * self.current_instances

    def required_instances(self, target_throughput: Number) -> int:
        headroom = 1 + self.headroom_target.to(units.fraction).quantity
        required = target_throughput.quantity * headroom
        return ceil(required / self.requests_per_instance.quantity)
```

### Alert Level Evaluation

```python
def alert_level(self) -> Literal["ok", "warning", "critical"]:
    """Multi-dimensional alert logic."""
    burn = self.burn_rate().quantity
    remaining_pct = self.error_budget_remaining_percent().quantity

    # Critical if either condition is met
    if burn >= self.alerting.burn_rate_critical.quantity:
        return "critical"
    if remaining_pct <= self.alerting.budget_remaining_critical.quantity:
        return "critical"

    # Warning thresholds
    if burn >= self.alerting.burn_rate_warning.quantity:
        return "warning"
    if remaining_pct <= self.alerting.budget_remaining_warning.quantity:
        return "warning"

    return "ok"
```

### Uncertainty from Monitoring

```yaml
# Measurements include confidence intervals
availability:
  quantity: 99.92
  unit: "%"
  uncertainty: 0.01  # ±0.01% measurement precision
```

```python
# Uncertainty propagates through calculations
remaining = config.error_budget_remaining()
print(remaining)  # <4.32 ± 0.2 min>
```

## Dimensional Safety

The SRE domain involves several dimensions:

| Metric | Dimension | Units |
|--------|-----------|-------|
| Availability | `ratio` | %, nines, fraction |
| Error rate | `ratio` | %, ppm |
| Latency | `time` | ms, s |
| Throughput | `frequency` | req/s, Hz |
| Window | `time` | day, hour |
| Error budget | `time` | min, hour |
| Burn rate | `none` | dimensionless multiplier |

Dimensional validation catches errors like:

```yaml
# ❌ Wrong dimension - latency should be time, not percentage
latency_p99:
  target: { quantity: 99, unit: "%" }
# → ValidationError: expected dimension 'time', got 'ratio'
```

## SRE Concepts Modeled

1. **SLOs (Service Level Objectives)** — targets for availability, latency, error rate
2. **SLIs (Service Level Indicators)** — current measurements with uncertainty
3. **Error Budget** — total allowed "badness" in a window
4. **Burn Rate** — rate of error budget consumption vs expected
5. **Multi-Burn-Rate Alerting** — Google SRE pattern for actionable alerts
6. **Capacity Planning** — instances needed to meet throughput SLO with headroom
