# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
ucon.graph — backward-compatibility shim.

All functionality has moved to :mod:`ucon.conversion`. This module
re-exports everything so existing ``from ucon.graph import ...``
statements continue to work.
"""
from ucon.conversion import *  # noqa: F401,F403
from ucon.conversion import Graph as ConversionGraph  # noqa: F401
from ucon.conversion import _graph_context  # noqa: F401 — private name used by tests
