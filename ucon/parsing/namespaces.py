# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
The ``namespace`` rewriter: full qualification without the typing.

Full qualification is the namespacing rule for package-declared
vocabulary: ``pkg:name`` for every kind and aspect a package declares,
aliases included; root builtins stay unprefixed; cross-package
references are written explicitly. A per-package *default scope* was
considered and declined — it needs a resolution rule that silently
shadows a root builtin when a package reuses its name. Design record:
``docs/internal/decisions/008-aspect-stratum.md``.

The verbosity is recovered here. A package sets::

    [package]
    name = "radsafe"
    namespace = "radsafe"

and writes unprefixed names; :func:`rewrite_namespace` prepends the
prefix to every unprefixed declared name and kind-reference in the
payload, producing exactly the dict the hand-qualified file would have
parsed to. Three spellings control the rewrite:

* ``name`` — unprefixed, becomes ``pkg:name``.
* ``pkg:name`` — already qualified (any prefix), left untouched; this
  is also how cross-package references are written.
* ``@name`` — root escape: refers to (or declares) the unqualified
  root name; the ``@`` is stripped and no prefix is applied.

The rewrite is a pure ``dict → dict`` transformation: it consults
nothing loaded — no registry, no active system — and therefore cannot
shadow anything. It is idempotent because the ``namespace`` key is
consumed: the output carries no ``namespace``, so a second application
is the identity (and the output equals the hand-qualified file, which
has no ``namespace`` key either).

Rewritten positions
-------------------
* ``[[kinds]]`` — ``name``, ``parent``, every ``aliases`` entry.
* ``[[aspects]]`` — ``name``, ``parent``, every ``applies_to`` entry
  (kind references; the ``"*"`` wildcard passes through untouched).
* ``[[formulas]]`` — ``output_kind`` and each ``inputs.<binding>.kind``
  (binding names are local to the formula and are not rewritten).
* ``[[constants]]`` — the optional ``kind`` reference.

Everything else (units, edges, dimensions, transforms) is out of the
qualification surface and passes through unchanged.
"""

from __future__ import annotations

import copy
from typing import Any


__all__ = ["rewrite_namespace"]


def _qualify(name: str, prefix: str) -> str:
    """Apply the three-spelling rule to one name."""
    if name.startswith("@"):
        return name[1:]
    if ":" in name:
        return name
    return f"{prefix}:{name}"


def rewrite_namespace(payload: dict[str, Any]) -> dict[str, Any]:
    """Qualify a payload's declared names per its ``package.namespace``.

    Parameters
    ----------
    payload
        The dict produced by :func:`tomllib.load`.

    Returns
    -------
    dict
        When the payload carries no ``package.namespace``: the payload
        itself, unchanged. Otherwise a deep-copied payload with every
        unprefixed kind/aspect name and kind-reference qualified and
        the ``namespace`` key removed (which is what makes the
        transformation idempotent).

    Raises
    ------
    ValueError
        If ``namespace`` is not a nonempty string, or contains ``:``
        or ``@`` (a prefix must itself be an unqualified name).
    """
    package = payload.get("package")
    if not isinstance(package, dict) or "namespace" not in package:
        return payload

    prefix = package["namespace"]
    if not isinstance(prefix, str) or not prefix:
        raise ValueError(
            f"package.namespace must be a nonempty string, got {prefix!r}"
        )
    if ":" in prefix or "@" in prefix:
        raise ValueError(
            f"package.namespace {prefix!r} may not contain ':' or '@'"
        )

    out = copy.deepcopy(payload)
    del out["package"]["namespace"]

    for entry in out.get("kinds", []):
        if "name" in entry:
            entry["name"] = _qualify(entry["name"], prefix)
        if "parent" in entry:
            entry["parent"] = _qualify(entry["parent"], prefix)
        if "aliases" in entry:
            entry["aliases"] = [
                _qualify(alias, prefix) for alias in entry["aliases"]
            ]

    for entry in out.get("aspects", []):
        if "name" in entry:
            entry["name"] = _qualify(entry["name"], prefix)
        if "parent" in entry:
            entry["parent"] = _qualify(entry["parent"], prefix)
        if "applies_to" in entry:
            entry["applies_to"] = [
                kind if kind == "*" else _qualify(kind, prefix)
                for kind in entry["applies_to"]
            ]

    for entry in out.get("formulas", []):
        if "output_kind" in entry:
            entry["output_kind"] = _qualify(entry["output_kind"], prefix)
        inputs = entry.get("inputs")
        if isinstance(inputs, dict):
            for spec in inputs.values():
                if isinstance(spec, dict) and "kind" in spec:
                    spec["kind"] = _qualify(spec["kind"], prefix)

    for entry in out.get("constants", []):
        if "kind" in entry:
            entry["kind"] = _qualify(entry["kind"], prefix)

    return out
