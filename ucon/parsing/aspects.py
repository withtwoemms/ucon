# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
TOML parser for ``[[aspects]]`` sections.

Builds an :class:`~ucon.aspects.forest.AspectForest` from a TOML
payload. Two entry points:

* :func:`parse_aspects_payload` — accepts an already-loaded dict (the
  result of :func:`tomllib.load`).
* :func:`load_aspects_file` — convenience wrapper that opens a path and
  decodes it.

Schema
------
::

    [[aspects]]
    name = "weighting_standard"
    applies_to = ["dose_equivalent"]   # optional, root-only
    join_policy = "refuse"             # optional, default "refuse"
    multiplication_policy = "carry"    # optional, root-only

    [[aspects]]
    name = "icrp103"
    parent = "weighting_standard"

``parent`` is a string resolved against the other entries; declaration
order does not matter (aspects are frozen and parents are objects, so
entries build in dependency order regardless of file order). Root-only
fields (``applies_to``, ``multiplication_policy``) on a child entry are
a load-time error — a defaulted field is indistinguishable from an
unset one after construction, so the parser is the layer that can see
the false declaration.

There are no builtin aspects: core ships mechanism, domains ship
vocabulary. Malformed schema raises :class:`ValueError`; aspect-semantic
failures (duplicates, orphan or cyclic parents, root-only violations)
raise :class:`~ucon.aspects.exceptions.AspectError` — never a
Kind-named exception, per the rewrap boundary.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from ucon.aspects import Aspect, AspectError, AspectForest, MultPolicy
from ucon.kinds import JoinPolicy


__all__ = ["parse_aspects_payload", "load_aspects_file"]


def parse_aspects_payload(payload: dict[str, Any]) -> AspectForest:
    """Build an :class:`AspectForest` from a parsed TOML payload.

    Parameters
    ----------
    payload
        The dict produced by :func:`tomllib.load`. Only the
        ``[[aspects]]`` section is consulted.

    Returns
    -------
    AspectForest
        A fully validated forest. Structural failures surface as
        :class:`AspectError` (from here or the forest constructor).

    Raises
    ------
    ValueError
        If an entry is malformed (missing ``name``, wrong field type,
        unrecognized policy value).
    AspectError
        If entries are semantically invalid: duplicate names, a parent
        that is not declared, a parent cycle, or a root-only field on
        a child entry.
    """
    entries = payload.get("aspects", [])
    if not isinstance(entries, list):
        raise ValueError("Expected [[aspects]] to be an array of tables")

    # Pass 1: validate shape, index by name.
    rough: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for raw in entries:
        name = raw.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError(f"Aspect entry missing 'name': {raw!r}")
        if name in rough:
            raise AspectError(
                f"Duplicate aspect name {name!r}: two [[aspects]] entries "
                f"declare it"
            )

        parent_name = raw.get("parent")
        if parent_name is not None and not isinstance(parent_name, str):
            raise ValueError(f"Aspect {name!r} has non-string parent")
        if parent_name is not None:
            for field in ("applies_to", "multiplication_policy"):
                if field in raw:
                    raise AspectError(
                        f"Aspect {name!r} declares {field!r} but has a "
                        f"parent; root-only fields belong on the family "
                        f"root"
                    )

        rough[name] = raw
        order.append(name)

    # Pass 2: build in dependency order (parents are frozen objects, so
    # a child cannot exist before its parent). File order is free.
    by_name: dict[str, Aspect] = {}
    building: set[str] = set()

    def build(name: str) -> Aspect:
        if name in by_name:
            return by_name[name]
        if name not in rough:
            raise AspectError(f"Aspect parent {name!r} is not declared")
        if name in building:
            chain = " -> ".join(sorted(building | {name}))
            raise AspectError(f"Aspect parent cycle involving: {chain}")
        building.add(name)
        raw = rough[name]

        parent = None
        parent_name = raw.get("parent")
        if parent_name is not None:
            parent = build(parent_name)

        join_policy_str = raw.get("join_policy", JoinPolicy.REFUSE.value)
        try:
            join_policy = JoinPolicy(join_policy_str)
        except ValueError as exc:
            raise ValueError(
                f"Aspect {name!r} has unrecognized join_policy "
                f"{join_policy_str!r}; expected one of "
                f"{[p.value for p in JoinPolicy]}"
            ) from exc

        mult_policy_str = raw.get(
            "multiplication_policy", MultPolicy.CARRY.value)
        try:
            mult_policy = MultPolicy(mult_policy_str)
        except ValueError as exc:
            raise ValueError(
                f"Aspect {name!r} has unrecognized multiplication_policy "
                f"{mult_policy_str!r}; expected one of "
                f"{[p.value for p in MultPolicy]}"
            ) from exc

        applies_to = raw.get("applies_to", ())
        if isinstance(applies_to, str) or not all(
            isinstance(k, str) for k in applies_to
        ):
            raise ValueError(
                f"Aspect {name!r}: applies_to must be a list of strings"
            )

        building.discard(name)
        by_name[name] = Aspect(
            name=name,
            parent=parent,
            join_policy=join_policy,
            applies_to=frozenset(applies_to),
            multiplication_policy=mult_policy,
        )
        return by_name[name]

    for name in order:
        build(name)

    return AspectForest(by_name[n] for n in order)


def load_aspects_file(path: str | Path) -> AspectForest:
    """Convenience: load an ``[[aspects]]`` TOML file from disk."""
    with open(path, "rb") as f:
        payload = tomllib.load(f)
    return parse_aspects_payload(payload)
