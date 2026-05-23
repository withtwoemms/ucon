# ucon/numpy.py
#
# NumPy array support for ucon.

"""
NumPy array support for ucon.

This module re-exports :class:`~ucon.core.NumberArray` for backward
compatibility.  The canonical location is :mod:`ucon.core._types`.

Requires: pip install ucon[numpy]

Example:
    >>> from ucon import units
    >>> from ucon.numpy import NumberArray
    >>> heights = NumberArray([1.7, 1.8, 1.9], unit=units.meter)
    >>> heights.to(units.foot)
    <[5.577, 5.905, 6.233] ft>
"""

from ucon.core._types import NumberArray  # noqa: F401

# Export check
__all__ = ['NumberArray']
