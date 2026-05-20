# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
TOML parser for ``[[formulas]]`` sections.

Builds a :class:`~ucon.formulas.registry.FormulaRegistry` from a TOML
payload. Formulas reference kinds by name; the caller supplies the
:class:`~ucon.kinds.lattice.KindLattice` that resolves those names.

Schema
------
::

    [[formulas]]
    name = "radiation_weighting"
    expression = "D * w_R"
    output_kind = "equivalent_dose"
    notes = "..."                # optional
    generalizes = false          # optional, default false
    commutative = true           # optional, default true
      [formulas.inputs]
      D   = { kind = "absorbed_dose" }
      w_R = { kind = "radiation_weighting_factor" }
      [formulas.aspect_rules]    # optional, opaque in v1.9.0
      signal_summary = "consume"
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from ucon.formulas import AspectRule, FormulaRegistry, KindFormula
from ucon.kinds import KindLattice


__all__ = ["parse_formulas_payload", "load_formulas_file"]


def parse_formulas_payload(
    payload: dict[str, Any],
    *,
    lattice: KindLattice,
) -> FormulaRegistry:
    """Build a :class:`FormulaRegistry` from a parsed TOML payload.

    Parameters
    ----------
    payload
        The dict produced by :func:`tomllib.load`. Only the
        ``[[formulas]]`` section is consulted.
    lattice
        Lattice supplying the :class:`~ucon.kinds.types.Kind` instances
        referenced by formula entries. Names that do not resolve raise
        :class:`~ucon.kinds.exceptions.KindNotFound`.

    Returns
    -------
    FormulaRegistry
        A registry containing every parsed formula.

    Raises
    ------
    ValueError
        If a formula entry is missing required fields or has an
        unrecognized ``aspect_rules`` value.
    """
    entries = payload.get("formulas", [])
    if not isinstance(entries, list):
        raise ValueError("Expected [[formulas]] to be an array of tables")

    formulas: list[KindFormula] = []
    for raw in entries:
        name = raw.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError(f"Formula entry missing 'name': {raw!r}")
        expression = raw.get("expression")
        if not isinstance(expression, str):
            raise ValueError(f"Formula {name!r} missing 'expression'")
        output_kind_name = raw.get("output_kind")
        if not isinstance(output_kind_name, str):
            raise ValueError(f"Formula {name!r} missing 'output_kind'")

        inputs_block = raw.get("inputs", {})
        if not isinstance(inputs_block, dict):
            raise ValueError(
                f"Formula {name!r} 'inputs' must be a table mapping binding "
                f"names to {{ kind = \"...\" }} entries"
            )
        input_kinds = {}
        for binding, spec in inputs_block.items():
            if not isinstance(spec, dict) or "kind" not in spec:
                raise ValueError(
                    f"Formula {name!r} input {binding!r} must be "
                    f"{{ kind = \"...\" }}"
                )
            input_kinds[binding] = lattice.get(str(spec["kind"]))

        output_kind = lattice.get(output_kind_name)

        aspect_block = raw.get("aspect_rules", {})
        if not isinstance(aspect_block, dict):
            raise ValueError(
                f"Formula {name!r} 'aspect_rules' must be a table"
            )
        aspect_rules: dict[str, AspectRule] = {}
        for facet, rule in aspect_block.items():
            try:
                aspect_rules[str(facet)] = AspectRule(str(rule))
            except ValueError as exc:
                raise ValueError(
                    f"Formula {name!r} aspect_rules[{facet!r}] has "
                    f"unrecognized value {rule!r}; expected one of "
                    f"{[r.value for r in AspectRule]}"
                ) from exc

        formulas.append(
            KindFormula(
                name=name,
                expression=expression,
                input_kinds=input_kinds,
                output_kind=output_kind,
                aspect_rules=aspect_rules,
                generalizes=bool(raw.get("generalizes", False)),
                commutative=bool(raw.get("commutative", True)),
                notes=str(raw.get("notes", "")),
            )
        )

    return FormulaRegistry(formulas)


def load_formulas_file(
    path: str | Path,
    *,
    lattice: KindLattice,
) -> FormulaRegistry:
    """Convenience: load a ``[[formulas]]`` TOML file from disk."""
    with open(path, "rb") as f:
        payload = tomllib.load(f)
    return parse_formulas_payload(payload, lattice=lattice)
