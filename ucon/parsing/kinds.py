# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
TOML parser for ``[[kinds]]`` sections.

Builds a :class:`~ucon.kinds.lattice.KindLattice` from a TOML payload.
Two entry points:

* :func:`parse_kinds_payload` — accepts an already-loaded dict (the
  result of :func:`tomllib.load`).
* :func:`load_kinds_file` — convenience wrapper that opens a path and
  decodes it.

Schema
------
::

    [[kinds]]
    name = "kinetic_energy"
    dimension = "L²·M·T⁻²"
    parent = "energy"           # optional
    join_policy = "lca"         # optional, default "lca"
    aliases = ["KE"]            # optional

The ``dimension`` field is parsed via
:func:`ucon.parsing.dimensions.parse_dimension`. The ``parent`` field
is a string; the parser resolves it during a second pass to support
forward references and out-of-order declarations.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Iterable

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from ucon.kinds import JoinPolicy, Kind, KindLattice
from ucon.parsing.dimensions import parse_dimension


__all__ = ["parse_kinds_payload", "load_kinds_file"]


def parse_kinds_payload(payload: dict[str, Any]) -> KindLattice:
    """Build a :class:`KindLattice` from a parsed TOML payload.

    Parameters
    ----------
    payload
        The dict produced by :func:`tomllib.load`. Only the
        ``[[kinds]]`` section is consulted.

    Returns
    -------
    KindLattice
        A fully validated lattice. All load-time errors
        (:class:`~ucon.kinds.exceptions.KindError` subclasses) surface
        from the lattice constructor.

    Raises
    ------
    ValueError
        If a kind entry is missing required fields or has an
        unrecognized ``join_policy``.
    """
    entries = payload.get("kinds", [])
    if not isinstance(entries, list):
        raise ValueError("Expected [[kinds]] to be an array of tables")

    # Pass 1: build kinds without parent edges (parent resolved by name).
    rough: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for raw in entries:
        name = raw.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError(f"Kind entry missing 'name': {raw!r}")
        if "dimension" not in raw:
            raise ValueError(f"Kind {name!r} missing 'dimension'")
        rough[name] = raw
        order.append(name)

    # Pass 2: resolve parents, build Kind instances in declaration order.
    by_name: dict[str, Kind] = {}
    for name in order:
        raw = rough[name]
        dimension = parse_dimension(str(raw["dimension"]))

        join_policy_str = raw.get("join_policy", "lca")
        try:
            join_policy = JoinPolicy(join_policy_str)
        except ValueError as exc:
            raise ValueError(
                f"Kind {name!r} has unrecognized join_policy "
                f"{join_policy_str!r}; expected one of {[p.value for p in JoinPolicy]}"
            ) from exc

        aliases = tuple(raw.get("aliases", ()))
        if not all(isinstance(a, str) for a in aliases):
            raise ValueError(f"Kind {name!r} has non-string alias")

        parent_name = raw.get("parent")
        parent_kind: Kind | None = None
        if parent_name is not None:
            if not isinstance(parent_name, str):
                raise ValueError(f"Kind {name!r} has non-string parent")
            # Resolve through by_name when already built; fall through to
            # a placeholder Kind by name for forward references. The
            # lattice validates against actual nodes during construction.
            parent_kind = by_name.get(parent_name)
            if parent_kind is None:
                if parent_name not in rough:
                    # Defer to OrphanParent at lattice validation time.
                    parent_kind = _placeholder(parent_name, dimension)
                else:
                    # Forward reference: build a placeholder with the
                    # declared parent's dimension so cross-dimension checks
                    # surface meaningfully.
                    parent_dim = parse_dimension(str(rough[parent_name]["dimension"]))
                    parent_kind = _placeholder(parent_name, parent_dim)

        by_name[name] = Kind(
            name=name,
            dimension=dimension,
            parent=parent_kind,
            join_policy=join_policy,
            aliases=aliases,
        )

    return KindLattice(by_name[n] for n in order)


def load_kinds_file(path: str | Path) -> KindLattice:
    """Convenience: load a ``[[kinds]]`` TOML file from disk."""
    with open(path, "rb") as f:
        payload = tomllib.load(f)
    return parse_kinds_payload(payload)


def _placeholder(name: str, dimension) -> Kind:
    """Build a parent-name placeholder Kind for second-pass resolution."""
    return Kind(name=name, dimension=dimension)
