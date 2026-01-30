# © 2025 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
ucon.quantity
=============

Re-exports :class:`Number` and :class:`Ratio` from :mod:`ucon.core`
for backward compatibility.

These classes now live in :mod:`ucon.core` to enable the callable
unit syntax: ``meter(5)`` returns a ``Number``.
"""
from ucon.core import Number, Ratio, Quantifiable

__all__ = ['Number', 'Ratio', 'Quantifiable']
