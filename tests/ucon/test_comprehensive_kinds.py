"""Regression tests for the built-in kind catalog."""

from pathlib import Path

import pytest

from ucon.dimension import Dimension
from ucon.kinds import JoinPolicy, JoinRefused
from ucon.parsing import load_kinds_file


CATALOG = Path(__file__).resolve().parents[2] / "ucon" / "comprehensive.ucon.toml"


def test_dimensionless_koq_cluster_is_declared() -> None:
    lattice = load_kinds_file(CATALOG)
    root = lattice.get("dimensionless_ratio")
    names = {
        "efficiency",
        "relative_humidity",
        "mass_fraction",
        "volume_fraction",
        "amount_fraction",
        "bioavailability",
        "strain",
        "reynolds",
        "mach",
        "froude",
    }

    assert root.dimension == Dimension.none
    assert root.join_policy is JoinPolicy.REFUSE
    assert {lattice.get(name).name for name in names} == names
    assert all(lattice.get(name).parent == root for name in names)
    assert all(lattice.get(name).dimension == Dimension.none for name in names)


def test_dimensionless_koq_siblings_refuse_to_join() -> None:
    lattice = load_kinds_file(CATALOG)

    with pytest.raises(JoinRefused, match="dimensionless_ratio"):
        lattice.join(lattice.get("efficiency"), lattice.get("relative_humidity"))
