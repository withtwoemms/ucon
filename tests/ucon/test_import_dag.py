# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
test_import_dag
===============

Verification tests for the Phase 2 acyclic DAG restructure.

1. Every ``ucon.*`` module can be imported individually.
2. Audit deferred (function-body) ``from ucon.*`` imports — track known
   transitional imports and flag unexpected new ones.
"""
from __future__ import annotations

import ast
import importlib
import pkgutil
import unittest
from pathlib import Path

UCON_ROOT = Path(__file__).resolve().parent.parent.parent / "ucon"

# -------------------------------------------------------------------
# Known transitional deferred imports.
#
# Each entry is (module_path, function_name, imported_module).
# These are deferred imports that exist for a specific reason
# (circular-import avoidance, optional-dependency guarding, etc.)
# and will be eliminated in later phases or v2.0.
# -------------------------------------------------------------------
KNOWN_DEFERRED = {
    # --- core/ intra-package cross-references ---
    # Scale.__mul__ defers Unit/UnitProduct (cross-module within core/)
    ("ucon.core.scale", "__mul__", "ucon.core.unit"),
    ("ucon.core.scale", "__mul__", "ucon.core.product"),
    # Unit algebra methods defer UnitProduct
    ("ucon.core.unit", "__mul__", "ucon.core.product"),
    ("ucon.core.unit", "__truediv__", "ucon.core.product"),
    ("ucon.core.unit", "__pow__", "ucon.core.product"),
    ("ucon.core.unit", "__eq__", "ucon.core.product"),
    # Unit.__call__ defers Number and NumberArray
    ("ucon.core.unit", "__call__", "ucon.core.product"),
    ("ucon.core.unit", "__call__", "ucon.core.quantity"),
    ("ucon.core.unit", "__call__", "ucon.integrations.numpy"),
    # UnitProduct.__call__ defers Number and NumberArray
    ("ucon.core.product", "__call__", "ucon.core.quantity"),
    ("ucon.core.product", "__call__", "ucon.integrations.numpy"),

    # --- system/ deferred imports ---
    # system/__init__.py: base_for() defers DimensionNotCovered
    ("ucon.system", "base_for", "ucon.core"),
    # system/__init__.py: from_globals() defers high-layer imports (deprecated)
    ("ucon.system", "from_globals", "ucon._loader"),
    ("ucon.system", "from_globals", "ucon.basis.graph"),
    ("ucon.system", "from_globals", "ucon.dimension"),
    ("ucon.system", "from_globals", "ucon.graph"),
    ("ucon.system", "from_globals", "ucon"),
    # system/__init__.py: resolve_unit() defers resolver
    ("ucon.system", "resolve_unit", "ucon.resolver"),

    # --- graph.py / graph_registry.py deferred imports ---
    ("ucon.graph_registry", "_build_standard_graph", "ucon._loader"),
    ("ucon.graph", "from_toml", "ucon.serialization"),
    ("ucon.graph", "to_toml", "ucon.serialization"),
    ("ucon.graph", "with_package", "ucon.packages"),
    ("ucon.graph", "_package_edge_already_covered", "ucon.resolver"),

    # --- _loader.py deferred imports ---
    ("ucon._loader", "_ensure_loaded", "ucon.serialization"),

    # --- packages.py deferred imports ---
    ("ucon.packages", "materialize", "ucon.graph"),
    ("ucon.packages", "materialize", "ucon.resolver"),

    # --- constants.py deferred imports ---
    ("ucon.constants", "_build_constants", "ucon._loader"),
}


def _discover_ucon_modules() -> list[str]:
    """Discover all ucon submodules by walking the package tree."""
    modules = []
    for importer, modname, ispkg in pkgutil.walk_packages(
        [str(UCON_ROOT)], prefix="ucon."
    ):
        modules.append(modname)
    modules.append("ucon")
    return sorted(set(modules))


def _is_type_checking_guard(node: ast.AST) -> bool:
    """Check if an ``if`` node is a ``TYPE_CHECKING`` guard."""
    if not isinstance(node, ast.If):
        return False
    test = node.test
    # Simple: ``if TYPE_CHECKING:``
    if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
        return True
    # Qualified: ``if typing.TYPE_CHECKING:``
    if isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING":
        return True
    return False


def _find_deferred_imports(source: str, module_name: str) -> list[tuple[str, str, str]]:
    """Find ``from ucon.* import ...`` statements inside function/method bodies.

    Skips TYPE_CHECKING-guarded blocks.

    Returns list of (module_name, function_name, imported_module).
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    results = []

    def _collect_import(node, enclosing_name: str):
        """Record a ucon import if it's from a ucon module."""
        if isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("ucon"):
                results.append((module_name, enclosing_name, node.module))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("ucon"):
                    results.append((module_name, enclosing_name, alias.name))

    def _walk_body(nodes, enclosing_name: str):
        for node in nodes:
            # Skip TYPE_CHECKING blocks
            if _is_type_checking_guard(node):
                continue

            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                _walk_body(node.body, node.name)
            elif isinstance(node, ast.ClassDef):
                # Methods inside a class inherit the enclosing name
                _walk_body(node.body, enclosing_name)
            elif isinstance(node, (ast.ImportFrom, ast.Import)):
                _collect_import(node, enclosing_name)
            else:
                # Recurse into try/except/if/with/for/while blocks
                for child_list_name in ("body", "handlers", "orelse", "finalbody"):
                    child_list = getattr(node, child_list_name, None)
                    if isinstance(child_list, list):
                        _walk_body(child_list, enclosing_name)

    # Walk top-level nodes
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _walk_body(node.body, node.name)
        elif isinstance(node, ast.ClassDef):
            _walk_body(node.body, "<module>")
        # Top-level try/except that wraps imports — don't flag
        # (these are conditional imports like numpy)

    return results


class TestModuleImportability(unittest.TestCase):
    """Every ucon.* module should be individually importable without error."""

    def test_all_modules_importable(self):
        modules = _discover_ucon_modules()
        failures = []
        for mod in modules:
            try:
                importlib.import_module(mod)
            except Exception as e:
                failures.append(f"{mod}: {e}")
        if failures:
            self.fail(
                f"{len(failures)} module(s) failed to import:\n"
                + "\n".join(failures)
            )


class TestDeferredImportAudit(unittest.TestCase):
    """Audit deferred imports: only known transitional ones should exist."""

    def test_no_unexpected_deferred_imports(self):
        """Scan all ucon source files for deferred ``from ucon.*`` imports.

        Any deferred import not in KNOWN_DEFERRED is unexpected and should
        either be promoted to top-level or added to the known set with a
        Phase justification comment.
        """
        unexpected = []
        py_files = list(UCON_ROOT.rglob("*.py"))

        for py_file in py_files:
            # Compute module name from file path
            rel = py_file.relative_to(UCON_ROOT.parent)
            parts = list(rel.with_suffix("").parts)
            if parts[-1] == "__init__":
                parts = parts[:-1]
            module_name = ".".join(parts)

            source = py_file.read_text()
            deferred = _find_deferred_imports(source, module_name)

            for mod, func, imported in deferred:
                key = (mod, func, imported)
                if key not in KNOWN_DEFERRED:
                    unexpected.append(
                        f"  {mod}:{func} → from {imported} import ..."
                    )

        if unexpected:
            self.fail(
                f"{len(unexpected)} unexpected deferred import(s):\n"
                + "\n".join(sorted(set(unexpected)))
                + "\n\nEither promote to top-level or add to KNOWN_DEFERRED."
            )

    def test_known_deferred_count(self):
        """Track the count of known deferred imports.

        This test documents the current state. As deferred imports are
        eliminated, update this number downward.
        """
        self.assertEqual(
            len(KNOWN_DEFERRED), 27,
            "Update this count when adding or removing KNOWN_DEFERRED entries"
        )


if __name__ == "__main__":
    unittest.main()
