# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
ucon.system._active
====================

The ``_active`` ContextVar that tracks the currently active UnitSystem.

This module has **zero** intra-ucon imports, placing it at the bottom of the
import DAG (Layer 1). Any module that needs to check or set the active system
can import from here without risk of circular imports.
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any

# Typed as Any to avoid importing UnitSystem (which lives at Layer 5).
# The actual value is always ``UnitSystem | None`` at runtime.
_active: ContextVar[Any] = ContextVar('ucon_active_system', default=None)

__all__ = ['_active']
