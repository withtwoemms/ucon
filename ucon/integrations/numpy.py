# ucon/numpy.py
#
# NumPy array support for ucon.

"""
NumPy array support for ucon.

This module provides NumberArray, a collection type for operating on
multiple quantities of a given unit simultaneously.

Requires: pip install ucon[numpy]

Example:
    >>> from ucon import units
    >>> from ucon.numpy import NumberArray
    >>> heights = NumberArray([1.7, 1.8, 1.9], unit=units.meter)
    >>> heights.to(units.foot)
    <[5.577, 5.905, 6.233] ft>
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Union, TYPE_CHECKING, Iterator, Any

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False
    np = None  # type: ignore

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import ArrayLike, NDArray

from ucon.core import Unit, UnitProduct, UnitFactor, Scale, Number, _none

# Module-level cache for scale factors: (src_unit, dst_unit) -> factor
_scale_factor_cache: dict[tuple, float] = {}

# Module-level cache for unit multiplication: (unit_a, unit_b) -> result_unit
_unit_mul_cache: dict[tuple, 'UnitProduct'] = {}

# Module-level cache for unit division: (unit_a, unit_b) -> result_unit
_unit_div_cache: dict[tuple, 'UnitProduct'] = {}


def _require_numpy() -> None:
    """Raise ImportError if numpy is not available."""
    if not _HAS_NUMPY:
        raise ImportError(
            "NumPy is required for NumberArray. "
            "Install with: pip install ucon[numpy]"
        )


class NumberArray:
    """
    A collection of quantities with a shared unit.

    Combines a numpy array of magnitudes with a unit, enabling vectorized
    arithmetic and conversion.

    Parameters
    ----------
    quantities : array-like
        The numeric values (will be converted to numpy array).
    unit : Unit or UnitProduct, optional
        The unit for all quantities. Defaults to dimensionless.
    uncertainty : float or array-like, optional
        Uncertainty value(s). If scalar, applies uniformly to all elements.
        If array-like, must match the shape of quantities.

    Examples
    --------
    >>> from ucon import units
    >>> from ucon.numpy import NumberArray

    Create from list:

    >>> heights = NumberArray([1.7, 1.8, 1.9], unit=units.meter)
    >>> len(heights)
    3

    Vectorized conversion:

    >>> heights_ft = heights.to(units.foot)
    >>> heights_ft[0].quantity  # doctest: +ELLIPSIS
    5.577...

    With uniform uncertainty:

    >>> temps = NumberArray([20, 21, 22], unit=units.celsius, uncertainty=0.5)

    With per-element uncertainty:

    >>> measurements = NumberArray([1.0, 2.0, 3.0], unit=units.meter,
    ...                            uncertainty=[0.01, 0.02, 0.015])
    """

    __slots__ = ('_quantities', '_unit', '_uncertainty')

    def __init__(
        self,
        quantities: 'ArrayLike',
        unit: Union[Unit, UnitProduct, None] = None,
        uncertainty: Union[float, 'ArrayLike', None] = None,
    ):
        _require_numpy()

        self._quantities: NDArray[np.floating] = np.asarray(quantities, dtype=float)
        self._unit = unit if unit is not None else _none

        if uncertainty is not None:
            if isinstance(uncertainty, (int, float)):
                self._uncertainty: Union[float, NDArray[np.floating], None] = float(uncertainty)
            else:
                self._uncertainty = np.asarray(uncertainty, dtype=float)
                if self._uncertainty.shape != self._quantities.shape:
                    raise ValueError(
                        f"Uncertainty shape {self._uncertainty.shape} does not match "
                        f"quantities shape {self._quantities.shape}"
                    )
        else:
            self._uncertainty = None

    @property
    def quantities(self) -> 'NDArray[np.floating]':
        """The array of numeric values."""
        return self._quantities

    @property
    def unit(self) -> Union[Unit, UnitProduct]:
        """The unit shared by all quantities."""
        return self._unit

    @property
    def uncertainty(self) -> Union[float, 'NDArray[np.floating]', None]:
        """The uncertainty (scalar or per-element array)."""
        return self._uncertainty

    def __len__(self) -> int:
        """Return the number of elements."""
        return len(self._quantities)

    @property
    def shape(self) -> tuple:
        """Shape of the quantities array."""
        return self._quantities.shape

    @property
    def ndim(self) -> int:
        """Number of dimensions."""
        return self._quantities.ndim

    @property
    def dtype(self) -> 'np.dtype':
        """Data type of the quantities array."""
        return self._quantities.dtype

    @property
    def dimension(self):
        """The physical dimension of the quantities."""
        if hasattr(self._unit, 'dimension'):
            return self._unit.dimension
        return None

    def __getitem__(self, key) -> Union[Number, 'NumberArray']:
        """Index or slice the array.

        Returns Number for scalar index, NumberArray for slice.
        """
        q = self._quantities[key]

        # Determine uncertainty for the slice
        if self._uncertainty is None:
            unc = None
        elif isinstance(self._uncertainty, float):
            unc = self._uncertainty
        else:
            unc = self._uncertainty[key]

        # Return Number for scalar index, NumberArray for slice
        if np.ndim(q) == 0:
            unc_val = float(unc) if unc is not None and not isinstance(unc, float) else unc
            return Number(quantity=float(q), unit=self._unit, uncertainty=unc_val)
        else:
            return NumberArray(quantities=q, unit=self._unit, uncertainty=unc)

    def __iter__(self) -> Iterator[Number]:
        """Iterate as Number instances."""
        for i in range(len(self)):
            yield self[i]  # type: ignore

    def __repr__(self) -> str:
        """String representation with truncation for large arrays."""
        # Format quantities with truncation for large arrays
        if len(self._quantities) <= 6:
            q_str = np.array2string(
                self._quantities,
                separator=', ',
                precision=4,
                suppress_small=True,
            )
        else:
            # Show first 3 and last 3
            head = ', '.join(f'{x:.4g}' for x in self._quantities[:3])
            tail = ', '.join(f'{x:.4g}' for x in self._quantities[-3:])
            q_str = f'[{head}, ..., {tail}]'

        # Format unit
        unit_str = self._format_unit()

        # Format uncertainty
        if self._uncertainty is None:
            return f'<{q_str} {unit_str}>'
        elif isinstance(self._uncertainty, float):
            return f'<{q_str} \u00b1 {self._uncertainty:.4g} {unit_str}>'
        else:
            # Per-element uncertainty - show shape indicator
            return f'<{q_str} \u00b1 [...] {unit_str}>'

    def _format_unit(self) -> str:
        """Format the unit for display."""
        if hasattr(self._unit, 'shorthand') and self._unit.shorthand:
            return self._unit.shorthand
        elif hasattr(self._unit, 'name'):
            return self._unit.name
        else:
            return str(self._unit)

    # -------------------------------------------------------------------------
    # Arithmetic Operations
    # -------------------------------------------------------------------------

    def __mul__(self, other) -> 'NumberArray':
        """Multiply by scalar, Number, or NumberArray."""
        if isinstance(other, (int, float)):
            new_unc = None
            if self._uncertainty is not None:
                new_unc = self._uncertainty * abs(other)
            return NumberArray(
                quantities=self._quantities * other,
                unit=self._unit,
                uncertainty=new_unc,
            )

        if isinstance(other, Number):
            result_q = self._quantities * other.quantity
            result_unit = self._unit * other.unit

            new_unc = self._propagate_mul_uncertainty(
                self._quantities, self._uncertainty,
                other.quantity, other.uncertainty
            )
            return NumberArray(quantities=result_q, unit=result_unit, uncertainty=new_unc)

        if isinstance(other, NumberArray):
            # Allow numpy broadcasting - shapes must be broadcast-compatible
            try:
                result_q = self._quantities * other._quantities
            except ValueError as e:
                raise ValueError(
                    f"Shapes {self.shape} and {other.shape} are not broadcast-compatible"
                ) from e

            # Cache unit multiplication (expensive due to UnitProduct.__init__)
            unit_key = (self._unit, other._unit)
            if unit_key in _unit_mul_cache:
                result_unit = _unit_mul_cache[unit_key]
            else:
                result_unit = self._unit * other._unit
                _unit_mul_cache[unit_key] = result_unit

            new_unc = self._propagate_mul_uncertainty(
                self._quantities, self._uncertainty,
                other._quantities, other._uncertainty
            )
            return NumberArray(quantities=result_q, unit=result_unit, uncertainty=new_unc)

        return NotImplemented

    def __rmul__(self, other) -> 'NumberArray':
        """Right multiplication."""
        return self.__mul__(other)

    def __truediv__(self, other) -> 'NumberArray':
        """Divide by scalar, Number, or NumberArray."""
        if isinstance(other, (int, float)):
            new_unc = None
            if self._uncertainty is not None:
                new_unc = self._uncertainty / abs(other)
            return NumberArray(
                quantities=self._quantities / other,
                unit=self._unit,
                uncertainty=new_unc,
            )

        if isinstance(other, Number):
            result_q = self._quantities / other.quantity
            result_unit = self._unit / other.unit

            new_unc = self._propagate_div_uncertainty(
                self._quantities, self._uncertainty,
                other.quantity, other.uncertainty
            )
            return NumberArray(quantities=result_q, unit=result_unit, uncertainty=new_unc)

        if isinstance(other, NumberArray):
            # Allow numpy broadcasting - shapes must be broadcast-compatible
            try:
                result_q = self._quantities / other._quantities
            except ValueError as e:
                raise ValueError(
                    f"Shapes {self.shape} and {other.shape} are not broadcast-compatible"
                ) from e

            # Cache unit division (expensive due to UnitProduct.__init__)
            unit_key = (self._unit, other._unit)
            if unit_key in _unit_div_cache:
                result_unit = _unit_div_cache[unit_key]
            else:
                result_unit = self._unit / other._unit
                _unit_div_cache[unit_key] = result_unit

            new_unc = self._propagate_div_uncertainty(
                self._quantities, self._uncertainty,
                other._quantities, other._uncertainty
            )
            return NumberArray(quantities=result_q, unit=result_unit, uncertainty=new_unc)

        return NotImplemented

    def __rtruediv__(self, other) -> 'NumberArray':
        """Right division (other / self)."""
        if isinstance(other, (int, float)):
            result_q = other / self._quantities

            new_unc = None
            if self._uncertainty is not None:
                # For c = a/x, δc = |c| * |δx/x|
                rel_unc = np.where(
                    self._quantities != 0,
                    np.abs(self._uncertainty / self._quantities),
                    0
                )
                new_unc = np.abs(result_q) * rel_unc

            # Unit is 1/self.unit
            inv_unit = _none / self._unit
            return NumberArray(quantities=result_q, unit=inv_unit, uncertainty=new_unc)

        return NotImplemented

    def __add__(self, other) -> 'NumberArray':
        """Add NumberArray or Number (same unit required)."""
        if isinstance(other, Number):
            self._check_same_unit(other.unit)
            result_q = self._quantities + other.quantity
            new_unc = self._propagate_add_uncertainty(
                self._uncertainty, other.uncertainty
            )
            return NumberArray(quantities=result_q, unit=self._unit, uncertainty=new_unc)

        if isinstance(other, NumberArray):
            self._check_same_unit(other._unit)
            # Allow numpy broadcasting - shapes must be broadcast-compatible
            try:
                result_q = self._quantities + other._quantities
            except ValueError as e:
                raise ValueError(
                    f"Shapes {self.shape} and {other.shape} are not broadcast-compatible"
                ) from e

            new_unc = self._propagate_add_uncertainty(
                self._uncertainty, other._uncertainty
            )
            return NumberArray(quantities=result_q, unit=self._unit, uncertainty=new_unc)

        return NotImplemented

    def __radd__(self, other) -> 'NumberArray':
        """Right addition."""
        return self.__add__(other)

    def __sub__(self, other) -> 'NumberArray':
        """Subtract NumberArray or Number (same unit required)."""
        if isinstance(other, Number):
            self._check_same_unit(other.unit)
            result_q = self._quantities - other.quantity
            new_unc = self._propagate_add_uncertainty(
                self._uncertainty, other.uncertainty
            )
            return NumberArray(quantities=result_q, unit=self._unit, uncertainty=new_unc)

        if isinstance(other, NumberArray):
            self._check_same_unit(other._unit)
            # Allow numpy broadcasting - shapes must be broadcast-compatible
            try:
                result_q = self._quantities - other._quantities
            except ValueError as e:
                raise ValueError(
                    f"Shapes {self.shape} and {other.shape} are not broadcast-compatible"
                ) from e

            new_unc = self._propagate_add_uncertainty(
                self._uncertainty, other._uncertainty
            )
            return NumberArray(quantities=result_q, unit=self._unit, uncertainty=new_unc)

        return NotImplemented

    def __rsub__(self, other) -> 'NumberArray':
        """Right subtraction (other - self)."""
        if isinstance(other, Number):
            self._check_same_unit(other.unit)
            result_q = other.quantity - self._quantities
            new_unc = self._propagate_add_uncertainty(
                other.uncertainty, self._uncertainty
            )
            return NumberArray(quantities=result_q, unit=self._unit, uncertainty=new_unc)

        return NotImplemented

    def __neg__(self) -> 'NumberArray':
        """Negation."""
        return NumberArray(
            quantities=-self._quantities,
            unit=self._unit,
            uncertainty=self._uncertainty,
        )

    def __pos__(self) -> 'NumberArray':
        """Unary positive (returns copy)."""
        return NumberArray(
            quantities=self._quantities.copy(),
            unit=self._unit,
            uncertainty=self._uncertainty if isinstance(self._uncertainty, float)
                        else self._uncertainty.copy() if self._uncertainty is not None
                        else None,
        )

    def __abs__(self) -> 'NumberArray':
        """Absolute value."""
        return NumberArray(
            quantities=np.abs(self._quantities),
            unit=self._unit,
            uncertainty=self._uncertainty,
        )

    # -------------------------------------------------------------------------
    # Comparison Operators
    # -------------------------------------------------------------------------

    def __eq__(self, other) -> 'NDArray[np.bool_]':
        """Element-wise equality comparison. Returns boolean array."""
        if isinstance(other, NumberArray):
            self._check_same_unit(other._unit)
            return self._quantities == other._quantities
        if isinstance(other, Number):
            self._check_same_unit(other.unit)
            return self._quantities == other.quantity
        if isinstance(other, (int, float)):
            return self._quantities == other
        return NotImplemented

    def __ne__(self, other) -> 'NDArray[np.bool_]':
        """Element-wise inequality comparison. Returns boolean array."""
        if isinstance(other, NumberArray):
            self._check_same_unit(other._unit)
            return self._quantities != other._quantities
        if isinstance(other, Number):
            self._check_same_unit(other.unit)
            return self._quantities != other.quantity
        if isinstance(other, (int, float)):
            return self._quantities != other
        return NotImplemented

    def __lt__(self, other) -> 'NDArray[np.bool_]':
        """Element-wise less-than comparison. Returns boolean array."""
        if isinstance(other, NumberArray):
            self._check_same_unit(other._unit)
            return self._quantities < other._quantities
        if isinstance(other, Number):
            self._check_same_unit(other.unit)
            return self._quantities < other.quantity
        if isinstance(other, (int, float)):
            return self._quantities < other
        return NotImplemented

    def __le__(self, other) -> 'NDArray[np.bool_]':
        """Element-wise less-than-or-equal comparison. Returns boolean array."""
        if isinstance(other, NumberArray):
            self._check_same_unit(other._unit)
            return self._quantities <= other._quantities
        if isinstance(other, Number):
            self._check_same_unit(other.unit)
            return self._quantities <= other.quantity
        if isinstance(other, (int, float)):
            return self._quantities <= other
        return NotImplemented

    def __gt__(self, other) -> 'NDArray[np.bool_]':
        """Element-wise greater-than comparison. Returns boolean array."""
        if isinstance(other, NumberArray):
            self._check_same_unit(other._unit)
            return self._quantities > other._quantities
        if isinstance(other, Number):
            self._check_same_unit(other.unit)
            return self._quantities > other.quantity
        if isinstance(other, (int, float)):
            return self._quantities > other
        return NotImplemented

    def __ge__(self, other) -> 'NDArray[np.bool_]':
        """Element-wise greater-than-or-equal comparison. Returns boolean array."""
        if isinstance(other, NumberArray):
            self._check_same_unit(other._unit)
            return self._quantities >= other._quantities
        if isinstance(other, Number):
            self._check_same_unit(other.unit)
            return self._quantities >= other.quantity
        if isinstance(other, (int, float)):
            return self._quantities >= other
        return NotImplemented

    def _check_same_unit(self, other_unit) -> None:
        """Raise ValueError if units don't match for addition/subtraction."""
        if self._unit != other_unit:
            raise ValueError(
                f"Cannot add/subtract quantities with different units: "
                f"{self._format_unit()} vs {other_unit}"
            )

    def _propagate_mul_uncertainty(
        self,
        a: 'NDArray',
        ua: Union[float, 'NDArray', None],
        b: Union[float, 'NDArray'],
        ub: Union[float, None],
    ) -> Union[float, 'NDArray', None]:
        """Propagate uncertainty through multiplication."""
        if ua is None and ub is None:
            return None

        # Convert to arrays for uniform handling
        a_arr = np.asarray(a)
        b_arr = np.asarray(b)

        # Relative uncertainties
        if ua is not None:
            rel_a = np.where(a_arr != 0, np.abs(ua) / np.abs(a_arr), 0.0)
        else:
            rel_a = np.zeros_like(a_arr)

        if ub is not None:
            rel_b = np.where(b_arr != 0, np.abs(ub) / np.abs(b_arr), 0.0)
        else:
            rel_b = np.zeros_like(b_arr)

        rel_c = np.sqrt(rel_a**2 + rel_b**2)
        result = np.abs(a_arr * b_arr) * rel_c

        # Return scalar if result is uniform and both inputs were scalar uncertainty
        if isinstance(ua, (float, type(None))) and isinstance(ub, (float, type(None))):
            if result.size == 1:
                return float(result.flat[0])
            if np.allclose(result, result.flat[0]):
                return float(result.flat[0])

        return result

    def _propagate_div_uncertainty(
        self,
        a: 'NDArray',
        ua: Union[float, 'NDArray', None],
        b: Union[float, 'NDArray'],
        ub: Union[float, None],
    ) -> Union[float, 'NDArray', None]:
        """Propagate uncertainty through division (same as multiplication)."""
        return self._propagate_mul_uncertainty(a, ua, b, ub)

    def _propagate_add_uncertainty(
        self,
        ua: Union[float, 'NDArray', None],
        ub: Union[float, 'NDArray', None],
    ) -> Union[float, 'NDArray', None]:
        """Propagate uncertainty through addition/subtraction."""
        if ua is None and ub is None:
            return None

        if ua is None:
            return ub
        if ub is None:
            return ua

        # Quadrature addition
        result = np.sqrt(np.asarray(ua)**2 + np.asarray(ub)**2)

        # Return scalar if both inputs were scalar
        if isinstance(ua, float) and isinstance(ub, float):
            return float(result)

        return result

    # -------------------------------------------------------------------------
    # Conversion
    # -------------------------------------------------------------------------

    def to(self, target: Union[Unit, UnitProduct], graph=None) -> 'NumberArray':
        """Convert all quantities to a different unit.

        Parameters
        ----------
        target : Unit or UnitProduct
            The target unit to convert to.
        graph : ConversionGraph, optional
            The conversion graph to use. Defaults to the global default graph.

        Returns
        -------
        NumberArray
            A new NumberArray with converted quantities.

        Examples
        --------
        >>> from ucon import units
        >>> heights = NumberArray([1, 2, 3], unit=units.meter)
        >>> heights_ft = heights.to(units.foot)
        """
        from ucon.graph import get_default_graph

        # Check scale factor cache first
        cache_key = (self._unit, target)
        if cache_key in _scale_factor_cache:
            factor = _scale_factor_cache[cache_key]
            new_unc = None
            if self._uncertainty is not None:
                new_unc = self._uncertainty * abs(factor)
            return NumberArray(
                quantities=self._quantities * factor,
                unit=target,
                uncertainty=new_unc,
            )

        # Normalize to UnitProduct
        src = self._unit if isinstance(self._unit, UnitProduct) else UnitProduct.from_unit(self._unit)
        dst = target if isinstance(target, UnitProduct) else UnitProduct.from_unit(target)

        # Scale-only conversion (no graph needed)
        if self._is_scale_only_conversion(src, dst):
            factor = src.fold_scale() / dst.fold_scale()
            _scale_factor_cache[cache_key] = factor  # Cache it
            new_unc = None
            if self._uncertainty is not None:
                new_unc = self._uncertainty * abs(factor)
            return NumberArray(
                quantities=self._quantities * factor,
                unit=target,
                uncertainty=new_unc,
            )

        # Graph-based conversion
        if graph is None:
            graph = get_default_graph()

        conversion_map = graph.convert(src=src, dst=dst)

        # Apply map to array
        converted = conversion_map(self._quantities)

        # Propagate uncertainty through conversion
        new_unc = None
        if self._uncertainty is not None:
            derivative = np.abs(conversion_map.derivative(self._quantities))
            new_unc = derivative * self._uncertainty

        return NumberArray(quantities=converted, unit=target, uncertainty=new_unc)

    def _is_scale_only_conversion(self, src: UnitProduct, dst: UnitProduct) -> bool:
        """Check if conversion is just a scale change (same base units)."""
        if len(src.factors) != len(dst.factors):
            return False

        src_by_dim = {}
        dst_by_dim = {}
        for f, exp in src.factors.items():
            src_by_dim[f.unit.dimension] = (f.unit, exp)
        for f, exp in dst.factors.items():
            dst_by_dim[f.unit.dimension] = (f.unit, exp)

        if src_by_dim.keys() != dst_by_dim.keys():
            return False

        for dim in src_by_dim:
            src_unit, src_exp = src_by_dim[dim]
            dst_unit, dst_exp = dst_by_dim[dim]
            if src_unit != dst_unit or abs(src_exp - dst_exp) > 1e-12:
                return False

        return True

    # -------------------------------------------------------------------------
    # NumPy Integration
    # -------------------------------------------------------------------------

    def __array__(self, dtype=None) -> 'NDArray':
        """Support np.asarray(number_array)."""
        if dtype is None:
            return self._quantities
        return self._quantities.astype(dtype)

    def sum(self) -> Number:
        """Sum all quantities."""
        total = float(np.sum(self._quantities))

        # Uncertainty propagation for sum
        unc = None
        if self._uncertainty is not None:
            if isinstance(self._uncertainty, float):
                # Uniform uncertainty: σ_sum = σ * sqrt(n)
                unc = self._uncertainty * math.sqrt(len(self))
            else:
                # Per-element: σ_sum = sqrt(Σσᵢ²)
                unc = float(np.sqrt(np.sum(self._uncertainty**2)))

        return Number(quantity=total, unit=self._unit, uncertainty=unc)

    def mean(self) -> Number:
        """Compute the mean."""
        avg = float(np.mean(self._quantities))

        # Uncertainty propagation for mean
        unc = None
        if self._uncertainty is not None:
            if isinstance(self._uncertainty, float):
                # Uniform uncertainty: σ_mean = σ / sqrt(n)
                unc = self._uncertainty / math.sqrt(len(self))
            else:
                # Per-element: σ_mean = sqrt(Σσᵢ²) / n
                unc = float(np.sqrt(np.sum(self._uncertainty**2)) / len(self))

        return Number(quantity=avg, unit=self._unit, uncertainty=unc)

    def std(self, ddof: int = 0) -> Number:
        """Compute the standard deviation."""
        s = float(np.std(self._quantities, ddof=ddof))
        return Number(quantity=s, unit=self._unit, uncertainty=None)

    def min(self) -> Number:
        """Return the minimum value."""
        idx = np.argmin(self._quantities)
        return self[idx]  # type: ignore

    def max(self) -> Number:
        """Return the maximum value."""
        idx = np.argmax(self._quantities)
        return self[idx]  # type: ignore


# Export check
__all__ = ['NumberArray']
