# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
test_import_dag
===============

Verification tests for the acyclic import DAG.

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
    # ------------------------------------------------------------------
    # ucon.conversion — three deferred imports on convenience methods.
    #
    # The imported modules (``ucon.serialization``, ``ucon.packages``)
    # sit *above* ``ucon.conversion`` in the import DAG, so promoting
    # these imports to top-level would close a cycle. The deferred
    # imports are structurally necessary.
    #
    # Each entry: (module_path, function_name, imported_module).
    # ------------------------------------------------------------------
    ("ucon.conversion", "from_toml", "ucon.serialization"),    # structural — avoids cycle
    ("ucon.conversion", "to_toml", "ucon.serialization"),      # structural — avoids cycle
    ("ucon.conversion", "with_package", "ucon.packages"),      # structural — avoids cycle
    # ------------------------------------------------------------------
    # ucon._cache — marshal codec for graph cache.
    #
    # _cache.py is a Layer-0-adjacent leaf that must be importable before
    # the heavy ucon.core / ucon.conversion modules. All imports of ucon
    # submodules are deferred to function bodies so the module's top-level
    # is stdlib-only (marshal, os, struct, sys, tempfile, pathlib,
    # warnings, fractions).
    # ------------------------------------------------------------------
    ("ucon._cache", "load_cached_graph", "ucon.serialization"),
    ("ucon._cache", "write_cached_graph", "ucon.serialization"),
    ("ucon._cache", "_map_to_prim", "ucon.maps"),
    ("ucon._cache", "_prim_to_map", "ucon.maps"),
    ("ucon._cache", "_unit_ref", "ucon.core"),
    ("ucon._cache", "_resolve_unit_ref", "ucon.core"),
    ("ucon._cache", "_to_primitives", "ucon.basis"),
    ("ucon._cache", "_to_primitives", "ucon.basis.transforms"),
    ("ucon._cache", "_to_primitives", "ucon.constants"),
    ("ucon._cache", "_to_primitives", "ucon.conversion"),
    ("ucon._cache", "_to_primitives", "ucon.core"),
    ("ucon._cache", "_to_primitives", "ucon.dimension"),
    ("ucon._cache", "_to_primitives", "ucon.kinds.types"),
    ("ucon._cache", "_from_primitives", "ucon.basis"),
    ("ucon._cache", "_from_primitives", "ucon.basis.transforms"),
    ("ucon._cache", "_from_primitives", "ucon.constants"),
    ("ucon._cache", "_from_primitives", "ucon.contexts"),
    ("ucon._cache", "_from_primitives", "ucon.conversion"),
    ("ucon._cache", "_from_primitives", "ucon.core"),
    ("ucon._cache", "_from_primitives", "ucon.dimension"),
    ("ucon._cache", "_from_primitives", "ucon.kinds.lattice"),
    ("ucon._cache", "_from_primitives", "ucon.kinds.types"),
    ("ucon._cache", "_build_kinds_recursive", "ucon.kinds.types"),
    ("ucon._cache", "_deserialize_product_key", "ucon.core"),
    ("ucon._cache", "_deserialize_product_tuple_key", "ucon.core"),
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


class TestLayer0Leaves(unittest.TestCase):
    """Layer-0 leaves must contain zero intra-ucon imports.

    A Layer-0 leaf is a module whose role is to host primitive state
    (e.g. a ``ContextVar``) that higher layers consume. To stay at the
    bottom of the import DAG it must not import anything from
    ``ucon.*`` at module load time.

    This property is what makes the v1.12.0 cycle-break durable: any
    contributor who adds ``from ucon.units import ...`` to ``ucon/_active.py``
    re-closes the cycle through ``resolver`` → ``core``. The test below
    catches the addition statically, before import time.
    """

    LAYER_0_LEAVES: set[str] = {"ucon._active"}

    def test_no_intra_ucon_imports(self):
        """Each declared Layer-0 leaf must not reference ``ucon.*``."""
        violations: list[str] = []

        for modname in self.LAYER_0_LEAVES:
            rel_parts = modname.split(".")
            py_file = UCON_ROOT.parent.joinpath(*rel_parts).with_suffix(".py")
            if not py_file.exists():
                py_file = UCON_ROOT.parent.joinpath(*rel_parts, "__init__.py")
            if not py_file.exists():
                violations.append(
                    f"  {modname}: source file not found at expected path"
                )
                continue

            source = py_file.read_text()
            try:
                tree = ast.parse(source)
            except SyntaxError as exc:
                violations.append(f"  {modname}: parse error: {exc}")
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and (
                        node.module == "ucon" or node.module.startswith("ucon.")
                    ):
                        violations.append(
                            f"  {modname}:{node.lineno} → "
                            f"from {node.module} import ..."
                        )
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == "ucon" or alias.name.startswith("ucon."):
                            violations.append(
                                f"  {modname}:{node.lineno} → "
                                f"import {alias.name}"
                            )

        if violations:
            self.fail(
                f"{len(violations)} Layer-0 leaf invariant violation(s):\n"
                + "\n".join(sorted(set(violations)))
                + "\n\nA Layer-0 leaf must have zero intra-ucon imports. "
                "Either remove the import or remove the module from "
                "LAYER_0_LEAVES with justification."
            )


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
            len(KNOWN_DEFERRED), 28,
            "Update this count when adding or removing KNOWN_DEFERRED entries"
        )


if __name__ == "__main__":
    unittest.main()
