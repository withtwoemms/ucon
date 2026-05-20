# Copyright 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0

"""
Exceptions raised by the formula registry.
"""

from __future__ import annotations


__all__ = ["FormulaError", "FormulaNotFound", "DuplicateFormula"]


class FormulaError(Exception):
    """Base class for formula registry errors."""


class FormulaNotFound(FormulaError):
    """No formula matches the supplied lookup key.

    ``name_or_kinds`` carries the lookup argument for the diagnostic.
    """

    def __init__(self, name_or_kinds: object) -> None:
        self.name_or_kinds = name_or_kinds
        super().__init__(f"No formula found for {name_or_kinds!r}")


class DuplicateFormula(FormulaError):
    """A formula with the given name is already registered.

    The registry's primary key is the formula name. Re-registering a
    formula with the same name is refused.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Duplicate formula: {name!r}")
