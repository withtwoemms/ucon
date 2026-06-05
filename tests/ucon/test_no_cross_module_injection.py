# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
test_no_cross_module_injection
==============================

Static (AST-based) audit asserting that **no module under ``ucon/``
assigns to an attribute of another ``ucon.*`` module at module top
level**. Cross-module assignment is a signal that the assignee
module is treating another module's namespace as its own,
indicating an unresolved layering / cycle-break workaround.

This test was added alongside the structural cycle-break work in v1.12.0
to prevent regressions.

What this catches
-----------------
- ``constants._constants_cache = ...`` (eliminated in S3)
- ``ucon.system._resolve_unit_impl = parse_unit`` (eliminated in S2)

What this does NOT catch
------------------------
- Function-body assignments (those would also be deferred-import
  candidates and are covered by ``test_import_dag.py``).
- Assignments to local module attributes (``__path__``, ``_init_graph``).
- Calls into helper functions that themselves mutate dicts (the
  orthodox replacement pattern — e.g. ``constants._populate_cache(...)``).

Whitelist
---------
A small set of intentional top-level assignments is allowed:

- ``ucon.__init__`` — ``__path__ = extend_path(...)``: this targets
  the module's own ``__path__`` for namespace-package support, not a
  sibling module.
"""
from __future__ import annotations

import ast
import unittest
from pathlib import Path

UCON_ROOT = Path(__file__).resolve().parent.parent.parent / "ucon"


def _qualified_target(node: ast.AST) -> str | None:
    """Render an assignment target as a dotted string, or None.

    Returns:
        ``"ucon.system._resolve_unit_impl"`` for
        ``ucon.system._resolve_unit_impl = ...``,
        ``"constants._constants_cache"`` for
        ``constants._constants_cache = ...``,
        ``None`` for plain ``Name`` targets and unsupported shapes.
    """
    if isinstance(node, ast.Attribute):
        parts: list[str] = [node.attr]
        cur: ast.AST = node.value
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            parts.append(cur.id)
            return ".".join(reversed(parts))
    return None


def _root_name(qualified: str) -> str:
    """Return the leftmost dotted segment."""
    return qualified.split(".", 1)[0]


def _find_cross_module_injections(
    source: str, module_name: str
) -> list[tuple[int, str]]:
    """Return list of (lineno, target) for cross-ucon top-level assignments.

    A target qualifies as cross-module injection if:

    - Its leftmost name resolves (locally) to a ``ucon.*`` module — i.e.
      it appears in the module's imports as a ``from ucon import X``,
      ``from ucon.* import X``, or ``import ucon[.*][.* as X]``.
    - It is not the module's own ``__path__``, ``__all__``,
      ``__getattr__``, etc.

    Strategy: collect the set of names bound at top level by any
    ``Import``/``ImportFrom`` referencing the ``ucon`` package, then
    flag attribute-target assignments whose root is in that set.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    # Collect names bound to ucon.* modules at top level.
    ucon_module_names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "ucon" or alias.name.startswith("ucon."):
                    bound = alias.asname or alias.name.split(".")[0]
                    ucon_module_names.add(bound)
        elif isinstance(node, ast.ImportFrom):
            if node.module and (node.module == "ucon" or node.module.startswith("ucon.")):
                for alias in node.names:
                    bound = alias.asname or alias.name
                    ucon_module_names.add(bound)

    findings: list[tuple[int, str]] = []
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            continue
        targets = (
            node.targets if isinstance(node, ast.Assign) else [node.target]
        )
        for tgt in targets:
            qualified = _qualified_target(tgt)
            if qualified is None:
                continue
            root = _root_name(qualified)
            if root in ucon_module_names:
                findings.append((node.lineno, qualified))
    return findings


# Modules whose top-level attribute-target assignments are tolerated.
# Keep this set minimal and document each entry.
WHITELIST: set[tuple[str, str]] = set()


class TestNoCrossModuleInjection(unittest.TestCase):
    """Static audit: no ucon module top-level-assigns into a sibling."""

    def test_no_top_level_cross_module_assignment(self):
        py_files = list(UCON_ROOT.rglob("*.py"))
        violations: list[str] = []

        for py_file in py_files:
            rel = py_file.relative_to(UCON_ROOT.parent)
            parts = list(rel.with_suffix("").parts)
            if parts[-1] == "__init__":
                parts = parts[:-1]
            module_name = ".".join(parts)

            source = py_file.read_text()
            for lineno, target in _find_cross_module_injections(
                source, module_name
            ):
                key = (module_name, target)
                if key in WHITELIST:
                    continue
                violations.append(
                    f"  {module_name}:{lineno} → {target} = ..."
                )

        if violations:
            self.fail(
                f"{len(violations)} cross-module top-level "
                f"assignment(s) detected:\n"
                + "\n".join(sorted(set(violations)))
                + "\n\nMove the mutation into the target module via "
                "an explicit helper function, or whitelist with "
                "justification."
            )


if __name__ == "__main__":
    unittest.main()
