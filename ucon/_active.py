# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
ucon._active
============

The ``_active`` ContextVar that tracks the currently active UnitSystem.

This module has **zero** intra-ucon imports, placing it at the bottom of the
import DAG (Layer 0). It lives at the package root rather than inside
``ucon.system`` so that low-level modules (e.g. ``ucon.core._types``) can
import it without triggering ``ucon.system/__init__.py`` execution, which
would close cycles back through ``resolver`` → ``core``.
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any

# Typed as Any to avoid importing UnitSystem (which lives at a higher layer).
# The actual value is always ``UnitSystem | None`` at runtime.
_active: ContextVar[Any] = ContextVar('ucon_active_system', default=None)


def active():
    """Return the currently active UnitSystem, or None.

    This is the **raw** accessor — it returns whatever is stored in the
    ContextVar without any fallback logic. The :func:`ucon.system.active`
    wrapper adds a ``from_globals`` fallback for backward compatibility.
    """
    return _active.get()


__all__ = ['_active', 'active']
