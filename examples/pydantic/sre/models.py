# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
SRE configuration models for SLO tracking and error budget management.

Demonstrates:
- Ratio dimension for availability and error rates
- Time-based calculations for error budgets
- Burn rate and exhaustion time computations
- Capacity planning with throughput dimensions
- Uncertainty as confidence intervals on measurements
"""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, model_validator
from pydantic.functional_validators import AfterValidator

from ucon import Dimension, Number, Scale, units
from ucon.pydantic import constrained_number


# Define millisecond for convenience
millisecond = Scale.milli * units.second

# ---------------------------------------------------------------------------
# Custom validators
# ---------------------------------------------------------------------------


def must_be_positive(n: Number) -> Number:
    """Validator: quantity must be > 0."""
    if n.quantity <= 0:
        raise ValueError(f"must be positive, got {n.quantity}")
    return n


def must_be_percentage(n: Number) -> Number:
    """Validator: must be in ratio dimension and reasonable range."""
    dim = n.unit.dimension if n.unit else Dimension.none
    if dim != Dimension.ratio:
        raise ValueError(f"must be a ratio/percentage, got {dim.name}")
    pct = n.to(units.percent).quantity
    if pct < 0 or pct > 100:
        raise ValueError(f"percentage must be 0-100, got {pct}")
    return n


# Subscriptable types with additional validators
PositiveNumber = constrained_number(AfterValidator(must_be_positive))
Percentage = constrained_number(
    AfterValidator(must_be_positive),
    AfterValidator(must_be_percentage),
)


# ---------------------------------------------------------------------------
# SLO definitions
# ---------------------------------------------------------------------------


class ThresholdType(str, Enum):
    """Whether the SLO is an upper or lower bound."""
    upper = "upper"  # metric should be below target (latency, error rate)
    lower = "lower"  # metric should be above target (availability, throughput)


class AvailabilitySLO(BaseModel):
    """Availability SLO with target and measurement window."""

    target: Percentage[Dimension.ratio]
    window: PositiveNumber[Dimension.time]

    @property
    def target_nines(self) -> float:
        """Target availability in nines notation."""
        return self.target.to(units.nines).quantity

    @property
    def error_budget_ratio(self) -> Number:
        """Allowed error ratio (1 - availability)."""
        target_fraction = self.target.to(units.fraction).quantity
        return units.fraction(1 - target_fraction)

    def total_error_budget(self) -> Number:
        """Total error budget in time units."""
        budget_fraction = 1 - self.target.to(units.fraction).quantity
        return self.window * budget_fraction


class LatencySLO(BaseModel):
    """Latency SLO (p50, p99, etc.)."""

    target: PositiveNumber[Dimension.time]
    threshold_type: Literal["upper"] = "upper"


class ErrorRateSLO(BaseModel):
    """Error rate SLO."""

    target: Percentage[Dimension.ratio]
    threshold_type: Literal["upper"] = "upper"


class ThroughputSLO(BaseModel):
    """Throughput SLO (requests per second)."""

    target: PositiveNumber[Dimension.frequency]
    threshold_type: Literal["lower"] = "lower"


class SLOConfig(BaseModel):
    """All SLOs for a service."""

    availability: AvailabilitySLO
    latency_p50: LatencySLO
    latency_p99: LatencySLO
    error_rate: ErrorRateSLO
    throughput: ThroughputSLO


# ---------------------------------------------------------------------------
# Current measurements
# ---------------------------------------------------------------------------


class CurrentMetrics(BaseModel):
    """Current measured values from monitoring."""

    availability: Percentage[Dimension.ratio]
    latency_p50: PositiveNumber[Dimension.time]
    latency_p99: PositiveNumber[Dimension.time]
    error_rate: Percentage[Dimension.ratio]
    throughput: PositiveNumber[Dimension.frequency]
    window_elapsed: PositiveNumber[Dimension.time]


# ---------------------------------------------------------------------------
# Alerting configuration
# ---------------------------------------------------------------------------


class AlertingConfig(BaseModel):
    """Alert thresholds for error budget burn rate."""

    burn_rate_critical: PositiveNumber[Dimension.ratio]
    burn_rate_warning: PositiveNumber[Dimension.ratio]
    budget_remaining_critical: Percentage[Dimension.ratio]
    budget_remaining_warning: Percentage[Dimension.ratio]

    @model_validator(mode='after')
    def critical_more_severe(self) -> 'AlertingConfig':
        """Ensure critical thresholds are more severe than warning."""
        if self.burn_rate_critical.quantity <= self.burn_rate_warning.quantity:
            raise ValueError("burn_rate_critical must be > burn_rate_warning")
        crit_pct = self.budget_remaining_critical.to(units.percent).quantity
        warn_pct = self.budget_remaining_warning.to(units.percent).quantity
        if crit_pct >= warn_pct:
            raise ValueError("budget_remaining_critical must be < warning")
        return self


# ---------------------------------------------------------------------------
# Capacity planning
# ---------------------------------------------------------------------------


class CapacityConfig(BaseModel):
    """Capacity planning parameters."""

    current_instances: int
    requests_per_instance: PositiveNumber[Dimension.frequency]
    headroom_target: Percentage[Dimension.ratio]

    @property
    def total_capacity(self) -> Number:
        """Total capacity across all instances."""
        return self.requests_per_instance * self.current_instances

    def required_instances(self, target_throughput: Number) -> int:
        """Calculate instances needed for target throughput with headroom."""
        headroom_mult = 1 + self.headroom_target.to(units.fraction).quantity
        required_capacity = target_throughput.quantity * headroom_mult
        per_instance = self.requests_per_instance.quantity
        return int((required_capacity / per_instance) + 0.999)  # ceil


# ---------------------------------------------------------------------------
# Service configuration
# ---------------------------------------------------------------------------


class ServiceConfig(BaseModel):
    """Service metadata."""

    name: str
    tier: Literal["critical", "high", "medium", "low"]


# ---------------------------------------------------------------------------
# Root configuration with computed methods
# ---------------------------------------------------------------------------


class SREConfig(BaseModel):
    """Root SRE configuration with error budget calculations."""

    service: ServiceConfig
    slos: SLOConfig
    current: CurrentMetrics
    alerting: AlertingConfig
    capacity: CapacityConfig

    # -------------------------------------------------------------------------
    # Error budget calculations
    # -------------------------------------------------------------------------

    def error_budget_total(self) -> Number:
        """Total error budget for the window (in time units)."""
        return self.slos.availability.total_error_budget()

    def error_budget_consumed(self) -> Number:
        """Error budget consumed so far (in time units)."""
        # Actual downtime = elapsed_time * (1 - actual_availability)
        actual_avail = self.current.availability.to(units.fraction).quantity
        downtime_fraction = 1 - actual_avail
        return self.current.window_elapsed * downtime_fraction

    def error_budget_remaining(self) -> Number:
        """Remaining error budget (in time units)."""
        total = self.error_budget_total()
        consumed = self.error_budget_consumed()
        remaining_qty = total.quantity - consumed.quantity
        # Propagate uncertainty if present
        unc = None
        if consumed.uncertainty:
            unc = consumed.uncertainty  # dominated by measurement uncertainty
        return Number(
            quantity=max(0, remaining_qty),
            unit=total.unit,
            uncertainty=unc,
        )

    def error_budget_remaining_percent(self) -> Number:
        """Remaining error budget as percentage of total."""
        total = self.error_budget_total().quantity
        remaining = self.error_budget_remaining().quantity
        if total == 0:
            return units.percent(0)
        return units.percent(100 * remaining / total)

    def burn_rate(self) -> Number:
        """Current burn rate (1.0 = on track, >1.0 = burning too fast)."""
        # Expected consumption at this point in window
        window_fraction = (
            self.current.window_elapsed.quantity /
            self.slos.availability.window.to(self.current.window_elapsed.unit).quantity
        )
        expected_consumed = self.error_budget_total().quantity * window_fraction

        # Actual consumption
        actual_consumed = self.error_budget_consumed().quantity

        if expected_consumed == 0:
            return units.fraction(0)

        rate = actual_consumed / expected_consumed
        return Number(
            quantity=rate,
            unit=units.fraction,
            uncertainty=None,  # Could compute from availability uncertainty
        )

    def time_to_exhaustion(self) -> Number | None:
        """Time until error budget is exhausted at current burn rate."""
        remaining = self.error_budget_remaining()
        if remaining.quantity <= 0:
            return units.second(0)

        burn = self.burn_rate().quantity
        if burn <= 0:
            return None  # Not burning budget

        # At current rate, how long until remaining is consumed?
        # Remaining budget / (budget_per_unit_time * burn_rate)
        window = self.slos.availability.window
        total_budget = self.error_budget_total()
        budget_per_day = total_budget.quantity / window.to(units.day).quantity

        if budget_per_day * burn <= 0:
            return None

        days_remaining = remaining.quantity / (budget_per_day * burn)
        return units.day(days_remaining)

    # -------------------------------------------------------------------------
    # SLO compliance checks
    # -------------------------------------------------------------------------

    def availability_compliance(self) -> bool:
        """Is current availability meeting SLO?"""
        current = self.current.availability.to(units.percent).quantity
        target = self.slos.availability.target.to(units.percent).quantity
        return current >= target

    def latency_p99_compliance(self) -> bool:
        """Is current p99 latency meeting SLO?"""
        current = self.current.latency_p99.to(millisecond).quantity
        target = self.slos.latency_p99.target.to(millisecond).quantity
        return current <= target

    def error_rate_compliance(self) -> bool:
        """Is current error rate meeting SLO?"""
        current = self.current.error_rate.to(units.percent).quantity
        target = self.slos.error_rate.target.to(units.percent).quantity
        return current <= target

    def throughput_compliance(self) -> bool:
        """Is current throughput meeting SLO?"""
        current = self.current.throughput.to(units.hertz).quantity
        target = self.slos.throughput.target.to(units.hertz).quantity
        return current >= target

    def all_slos_met(self) -> bool:
        """Are all SLOs currently being met?"""
        return (
            self.availability_compliance() and
            self.latency_p99_compliance() and
            self.error_rate_compliance() and
            self.throughput_compliance()
        )

    # -------------------------------------------------------------------------
    # Alert evaluation
    # -------------------------------------------------------------------------

    def alert_level(self) -> Literal["ok", "warning", "critical"]:
        """Current alert level based on burn rate and remaining budget."""
        burn = self.burn_rate().quantity
        remaining_pct = self.error_budget_remaining_percent().quantity

        crit_burn = self.alerting.burn_rate_critical.quantity
        warn_burn = self.alerting.burn_rate_warning.quantity
        crit_remaining = self.alerting.budget_remaining_critical.to(units.percent).quantity
        warn_remaining = self.alerting.budget_remaining_warning.to(units.percent).quantity

        # Critical if burn rate is critical OR remaining budget is critical
        if burn >= crit_burn or remaining_pct <= crit_remaining:
            return "critical"

        # Warning if burn rate is warning OR remaining budget is warning
        if burn >= warn_burn or remaining_pct <= warn_remaining:
            return "warning"

        return "ok"

    # -------------------------------------------------------------------------
    # Capacity analysis
    # -------------------------------------------------------------------------

    def capacity_headroom(self) -> Number:
        """Current capacity headroom as percentage."""
        total_cap = self.capacity.total_capacity.quantity
        current_load = self.current.throughput.quantity
        if total_cap == 0:
            return units.percent(0)
        headroom = (total_cap - current_load) / total_cap * 100
        return units.percent(headroom)

    def instances_for_slo(self) -> int:
        """Instances needed to meet throughput SLO with headroom."""
        return self.capacity.required_instances(self.slos.throughput.target)
