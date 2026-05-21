# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
ucon.parsing
============

Recursive-descent parsers for ucon's string forms.

Public surface
--------------
- :func:`parse` — quantity string → :class:`~ucon.core.Number`
  (e.g., ``"60 mph"``, ``"1.234 ± 0.005 m"``).
- :func:`parse_dimension` — dimension string → :class:`~ucon.dimension.Dimension`
  (e.g., ``"M"``, ``"velocity"``, ``"M·L/T²"``).
- :func:`parse_unit_expression` — power-user entry point for unit-expression
  parsing; called by :func:`ucon.resolver.parse_unit` for compound forms.
- :class:`ParseError` — raised on malformed input.

Internal layout
---------------
- :mod:`ucon.parsing.lexer` — shared tokenizer (``_Tokenizer``,
  ``_TokenType``, ``_Token``, ``ParseError``).
- :mod:`ucon.parsing.units` — unit-expression grammar plus the
  quantity-string :func:`parse` entry point.
- :mod:`ucon.parsing.dimensions` — dimension-expression grammar.

The dimensions submodule is loaded lazily (PEP 562 ``__getattr__``)
to avoid a load-time cycle through
``ucon.units → ucon.resolver → ucon.parsing``: by the time anyone
calls :func:`parse_dimension`, :mod:`ucon.dimension` is fully loaded.

Tokenizer privates (``_Tokenizer``, ``_Token``, ``_TokenType``) are
re-exported here for backward compatibility with code that previously
imported them from the single-file ``ucon.parsing`` module. New code
should import them from :mod:`ucon.parsing.lexer` directly.
"""
from ucon.parsing.lexer import (
    ParseError,
    _Token,
    _TokenType,
    _Tokenizer,
)
from ucon.parsing.units import (
    parse,
    parse_unit_expression,
)


_LAZY = {
    "parse_dimension": ("ucon.parsing.dimensions", "parse_dimension"),
    "parse_kinds_payload": ("ucon.parsing.kinds", "parse_kinds_payload"),
    "load_kinds_file": ("ucon.parsing.kinds", "load_kinds_file"),
    "parse_formulas_payload": ("ucon.parsing.formulas", "parse_formulas_payload"),
    "load_formulas_file": ("ucon.parsing.formulas", "load_formulas_file"),
}


def __getattr__(name):
    """PEP 562 lazy attribute access.

    Loading ``ucon.parsing.dimensions`` eagerly would force
    ``ucon.dimension`` to be evaluated whenever ``ucon.parsing`` is
    imported, including the early-bootstrap path
    ``ucon.units → ucon.resolver → ucon.parsing`` where the dimension
    module has not yet finished registering its attributes. The kind
    and formula parsers are deferred for the same reason: keeping
    ``ucon.kinds`` and ``ucon.formulas`` out of the bootstrap path.
    """
    spec = _LAZY.get(name)
    if spec is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr = spec
    import importlib

    return getattr(importlib.import_module(module_name), attr)


__all__ = [
    "ParseError",
    "parse",
    "parse_dimension",
    "parse_unit_expression",
    "parse_kinds_payload",
    "load_kinds_file",
    "parse_formulas_payload",
    "load_formulas_file",
]
