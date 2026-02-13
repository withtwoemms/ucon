#!/usr/bin/env python
# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
SRE error budget and SLO tracking example.

Demonstrates:
- Loading SLO/SLI configuration from YAML
- Error budget calculations with dimensional safety
- Burn rate and time-to-exhaustion computations
- Availability in nines notation
- Capacity planning with throughput dimensions
- Alert level evaluation

Usage:
    python main.py
    python main.py path/to/custom/config.yaml
"""

import sys
from pathlib import Path

import yaml

from ucon import units

from models import SREConfig


def load_config(config_path: Path) -> SREConfig:
    """Load and validate SRE configuration from YAML."""
    with open(config_path) as f:
        data = yaml.safe_load(f)
    return SREConfig(**data)


def format_duration(n) -> str:
    """Format a duration nicely."""
    if n is None:
        return "∞ (not burning)"

    hours = n.to(units.hour).quantity
    if hours < 1:
        return f"{n.to(units.minute)}"
    elif hours < 24:
        return f"{n.to(units.hour)}"
    else:
        return f"{n.to(units.day)}"


def main(config_path: Path) -> None:
    print(f"Loading SRE configuration from {config_path}\n")
    config = load_config(config_path)

    # Service info
    print(f"{'=' * 60}")
    print(f"Service: {config.service.name} (tier: {config.service.tier})")
    print(f"{'=' * 60}\n")

    # SLO targets
    print("=== SLO Targets ===")
    avail_pct = config.slos.availability.target.to(units.percent)
    avail_nines = config.slos.availability.target.to(units.nines)
    print(f"  Availability:  {avail_pct} ({avail_nines})")
    print(f"  Latency p50:   < {config.slos.latency_p50.target}")
    print(f"  Latency p99:   < {config.slos.latency_p99.target}")
    print(f"  Error rate:    < {config.slos.error_rate.target}")
    print(f"  Throughput:    > {config.slos.throughput.target}")
    print()

    # Current measurements
    print("=== Current Measurements ===")
    print(f"  Availability:  {config.current.availability}")
    print(f"  Latency p50:   {config.current.latency_p50}")
    print(f"  Latency p99:   {config.current.latency_p99}")
    print(f"  Error rate:    {config.current.error_rate}")
    print(f"  Throughput:    {config.current.throughput}")
    print(f"  Window elapsed: {config.current.window_elapsed}")
    print()

    # SLO compliance
    print("=== SLO Compliance ===")
    checks = [
        ("Availability", config.availability_compliance()),
        ("Latency p99", config.latency_p99_compliance()),
        ("Error rate", config.error_rate_compliance()),
        ("Throughput", config.throughput_compliance()),
    ]
    for name, passed in checks:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {name:15} {status}")
    print()

    # Error budget analysis
    print("=== Error Budget Analysis ===")
    total_budget = config.error_budget_total()
    consumed = config.error_budget_consumed()
    remaining = config.error_budget_remaining()
    remaining_pct = config.error_budget_remaining_percent()
    burn_rate = config.burn_rate()
    tte = config.time_to_exhaustion()

    print(f"  Window:           {config.slos.availability.window}")
    print(f"  Total budget:     {format_duration(total_budget)}")
    print(f"  Consumed:         {format_duration(consumed)}")
    print(f"  Remaining:        {format_duration(remaining)} ({remaining_pct})")
    print(f"  Burn rate:        {burn_rate.quantity:.2f}x")
    print(f"  Time to exhaust:  {format_duration(tte)}")
    print()

    # Alert status
    alert_level = config.alert_level()
    alert_symbol = {"ok": "✓", "warning": "⚠", "critical": "🔴"}[alert_level]
    print(f"=== Alert Status: {alert_symbol} {alert_level.upper()} ===")
    print(f"  Burn rate thresholds:")
    print(f"    Warning:  {config.alerting.burn_rate_warning.quantity}x")
    print(f"    Critical: {config.alerting.burn_rate_critical.quantity}x")
    print(f"  Budget remaining thresholds:")
    print(f"    Warning:  < {config.alerting.budget_remaining_warning}")
    print(f"    Critical: < {config.alerting.budget_remaining_critical}")
    print()

    # Capacity analysis
    print("=== Capacity Analysis ===")
    total_cap = config.capacity.total_capacity
    headroom = config.capacity_headroom()
    instances_needed = config.instances_for_slo()

    print(f"  Current instances:    {config.capacity.current_instances}")
    print(f"  Per-instance capacity: {config.capacity.requests_per_instance}")
    print(f"  Total capacity:       {total_cap}")
    print(f"  Current load:         {config.current.throughput}")
    print(f"  Headroom:             {headroom}")
    print(f"  Target headroom:      {config.capacity.headroom_target}")
    print(f"  Instances for SLO:    {instances_needed}")
    print()

    # Recommendations
    print("=== Recommendations ===")
    if alert_level == "critical":
        print("  🔴 CRITICAL: Error budget nearly exhausted!")
        print("     - Investigate recent incidents")
        print("     - Consider freezing deployments")
        print("     - Page on-call if not already")
    elif alert_level == "warning":
        print("  ⚠ WARNING: Error budget burning faster than expected")
        print("     - Review recent changes")
        print("     - Monitor closely")
    else:
        print("  ✓ All systems nominal")

    if config.capacity.current_instances < instances_needed:
        print(f"  ⚠ CAPACITY: Need {instances_needed} instances to meet SLO with headroom")

    if not config.all_slos_met():
        failing = [name for name, passed in checks if not passed]
        print(f"  ⚠ SLO BREACH: {', '.join(failing)}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        config_file = Path(sys.argv[1])
    else:
        config_file = Path(__file__).parent / "config.yaml"

    main(config_file)
