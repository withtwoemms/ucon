# ucon/polars.py
#
# Polars integration for ucon.

"""
Polars integration for ucon.

This module provides NumberColumn for working with unit-aware Polars Series.

Requires: pip install ucon[polars]

Example:
    >>> import polars as pl
    >>> from ucon import units
    >>> from ucon.polars import NumberColumn
    >>>
    >>> heights = NumberColumn(pl.Series([1.7, 1.8, 1.9]), unit=units.meter)
    >>> heights.to(units.foot)
    <NumberColumn [5.577, 5.905, 6.233] ft>
"""

from __future__ import annotations

import math
from typing import Union, TYPE_CHECKING, Iterator, Optional

try:
    import polars as pl
    HAS_POLARS = True
except ImportError:
    HAS_POLARS = False
    pl = None  # type: ignore

if TYPE_CHECKING:
    import polars as pl

from ucon.core import Unit, UnitProduct, UnitFactor, Scale, Number, _none


def _require_polars() -> None:
    """Raise ImportError if polars is not available."""
    if not HAS_POLARS:
        raise ImportError(
            "Polars is required for NumberColumn. "
            "Install with: pip install ucon[polars]"
        )


class NumberColumn:
    """
    A Polars Series with an associated unit.

    Combines a Polars Series of magnitudes with a unit, enabling vectorized
    arithmetic and conversion.

    Parameters
    ----------
    series : pl.Series
        The numeric values.
    unit : Unit or UnitProduct, optional
        The unit for all values. Defaults to dimensionless.
    uncertainty : float or pl.Series, optional
        Uncertainty value(s). If scalar, applies uniformly to all elements.
        If Series, must have the same length.

    Examples
    --------
    >>> import polars as pl
    >>> from ucon import units
    >>> from ucon.polars import NumberColumn

    Create from Series:

    >>> heights = NumberColumn(pl.Series([1.7, 1.8, 1.9]), unit=units.meter)
    >>> len(heights)
    3

    Vectorized conversion:

    >>> heights_ft = heights.to(units.foot)
    """

    __slots__ = ('_series', '_unit', '_uncertainty')

    def __init__(
        self,
        series: 'pl.Series',
        unit: Union[Unit, UnitProduct, None] = None,
        uncertainty: Union[float, 'pl.Series', None] = None,
    ):
        _require_polars()

        if not isinstance(series, pl.Series):
            series = pl.Series(series)

        self._series: pl.Series = series.cast(pl.Float64)
        self._unit = unit if unit is not None else _none

        if uncertainty is not None:
            if isinstance(uncertainty, (int, float)):
                self._uncertainty: Union[float, pl.Series, None] = float(uncertainty)
            else:
                self._uncertainty = uncertainty.cast(pl.Float64)
                if len(self._uncertainty) != len(self._series):
                    raise ValueError(
                        f"Uncertainty length {len(self._uncertainty)} does not match "
                        f"series length {len(self._series)}"
                    )
        else:
            self._uncertainty = None

    @property
    def series(self) -> 'pl.Series':
        """The underlying Polars Series."""
        return self._series

    @property
    def unit(self) -> Union[Unit, UnitProduct]:
        """The unit shared by all values."""
        return self._unit

    @property
    def uncertainty(self) -> Union[float, 'pl.Series', None]:
        """The uncertainty (scalar or per-element Series)."""
        return self._uncertainty

    def __len__(self) -> int:
        """Return the number of elements."""
        return len(self._series)

    @property
    def shape(self) -> tuple:
        """Shape of the series."""
        return self._series.shape

    @property
    def dtype(self):
        """Data type of the series."""
        return self._series.dtype

    @property
    def dimension(self):
        """The physical dimension of the quantities."""
        if hasattr(self._unit, 'dimension'):
            return self._unit.dimension
        return None

    def __getitem__(self, key) -> Union[Number, 'NumberColumn']:
        """Index or slice the series."""
        if isinstance(key, int):
            val = self._series[key]

            if self._uncertainty is None:
                unc = None
            elif isinstance(self._uncertainty, float):
                unc = self._uncertainty
            else:
                unc = float(self._uncertainty[key])

            return Number(quantity=float(val), unit=self._unit, uncertainty=unc)
        else:
            # Slice
            sliced = self._series[key]
            if self._uncertainty is None:
                unc = None
            elif isinstance(self._uncertainty, float):
                unc = self._uncertainty
            else:
                unc = self._uncertainty[key]
            return NumberColumn(series=sliced, unit=self._unit, uncertainty=unc)

    def __iter__(self) -> Iterator[Number]:
        """Iterate as Number instances."""
        for i in range(len(self)):
            yield self[i]  # type: ignore

    def __repr__(self) -> str:
        """String representation."""
        vals = self._series.to_list()
        if len(vals) <= 6:
            vals_str = ', '.join(f'{x:.4g}' for x in vals)
        else:
            head = ', '.join(f'{x:.4g}' for x in vals[:3])
            tail = ', '.join(f'{x:.4g}' for x in vals[-3:])
            vals_str = f'{head}, ..., {tail}'

        unit_str = self._format_unit()

        if self._uncertainty is None:
            return f'<NumberColumn [{vals_str}] {unit_str}>'
        elif isinstance(self._uncertainty, float):
            return f'<NumberColumn [{vals_str}] \u00b1 {self._uncertainty:.4g} {unit_str}>'
        else:
            return f'<NumberColumn [{vals_str}] \u00b1 [...] {unit_str}>'

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

    def __mul__(self, other) -> 'NumberColumn':
        """Multiply by scalar, Number, or NumberColumn."""
        if isinstance(other, (int, float)):
            new_unc = None
            if self._uncertainty is not None:
                if isinstance(self._uncertainty, float):
                    new_unc = self._uncertainty * abs(other)
                else:
                    new_unc = self._uncertainty * abs(other)
            return NumberColumn(
                series=self._series * other,
                unit=self._unit,
                uncertainty=new_unc,
            )

        if isinstance(other, Number):
            result = self._series * other.quantity
            result_unit = self._unit * other.unit

            new_unc = self._propagate_mul_uncertainty(
                self._series, self._uncertainty,
                other.quantity, other.uncertainty
            )
            return NumberColumn(series=result, unit=result_unit, uncertainty=new_unc)

        if isinstance(other, NumberColumn):
            if len(self) != len(other):
                raise ValueError(f"Length mismatch: {len(self)} vs {len(other)}")

            result = self._series * other._series
            result_unit = self._unit * other._unit
            new_unc = self._propagate_mul_uncertainty(
                self._series, self._uncertainty,
                other._series, other._uncertainty
            )
            return NumberColumn(series=result, unit=result_unit, uncertainty=new_unc)

        return NotImplemented

    def __rmul__(self, other) -> 'NumberColumn':
        """Right multiplication."""
        return self.__mul__(other)

    def __truediv__(self, other) -> 'NumberColumn':
        """Divide by scalar, Number, or NumberColumn."""
        if isinstance(other, (int, float)):
            new_unc = None
            if self._uncertainty is not None:
                if isinstance(self._uncertainty, float):
                    new_unc = self._uncertainty / abs(other)
                else:
                    new_unc = self._uncertainty / abs(other)
            return NumberColumn(
                series=self._series / other,
                unit=self._unit,
                uncertainty=new_unc,
            )

        if isinstance(other, Number):
            result = self._series / other.quantity
            result_unit = self._unit / other.unit

            new_unc = self._propagate_div_uncertainty(
                self._series, self._uncertainty,
                other.quantity, other.uncertainty
            )
            return NumberColumn(series=result, unit=result_unit, uncertainty=new_unc)

        if isinstance(other, NumberColumn):
            if len(self) != len(other):
                raise ValueError(f"Length mismatch: {len(self)} vs {len(other)}")

            result = self._series / other._series
            result_unit = self._unit / other._unit
            new_unc = self._propagate_div_uncertainty(
                self._series, self._uncertainty,
                other._series, other._uncertainty
            )
            return NumberColumn(series=result, unit=result_unit, uncertainty=new_unc)

        return NotImplemented

    def __add__(self, other) -> 'NumberColumn':
        """Add NumberColumn or Number (same unit required)."""
        if isinstance(other, Number):
            self._check_same_unit(other.unit)
            result = self._series + other.quantity
            new_unc = self._propagate_add_uncertainty(
                self._uncertainty, other.uncertainty
            )
            return NumberColumn(series=result, unit=self._unit, uncertainty=new_unc)

        if isinstance(other, NumberColumn):
            self._check_same_unit(other._unit)
            if len(self) != len(other):
                raise ValueError(f"Length mismatch: {len(self)} vs {len(other)}")

            result = self._series + other._series
            new_unc = self._propagate_add_uncertainty(
                self._uncertainty, other._uncertainty
            )
            return NumberColumn(series=result, unit=self._unit, uncertainty=new_unc)

        return NotImplemented

    def __radd__(self, other) -> 'NumberColumn':
        """Right addition."""
        return self.__add__(other)

    def __sub__(self, other) -> 'NumberColumn':
        """Subtract NumberColumn or Number (same unit required)."""
        if isinstance(other, Number):
            self._check_same_unit(other.unit)
            result = self._series - other.quantity
            new_unc = self._propagate_add_uncertainty(
                self._uncertainty, other.uncertainty
            )
            return NumberColumn(series=result, unit=self._unit, uncertainty=new_unc)

        if isinstance(other, NumberColumn):
            self._check_same_unit(other._unit)
            if len(self) != len(other):
                raise ValueError(f"Length mismatch: {len(self)} vs {len(other)}")

            result = self._series - other._series
            new_unc = self._propagate_add_uncertainty(
                self._uncertainty, other._uncertainty
            )
            return NumberColumn(series=result, unit=self._unit, uncertainty=new_unc)

        return NotImplemented

    def __neg__(self) -> 'NumberColumn':
        """Negation."""
        return NumberColumn(
            series=-self._series,
            unit=self._unit,
            uncertainty=self._uncertainty,
        )

    def __abs__(self) -> 'NumberColumn':
        """Absolute value."""
        return NumberColumn(
            series=self._series.abs(),
            unit=self._unit,
            uncertainty=self._uncertainty,
        )

    # -------------------------------------------------------------------------
    # Comparison Operators
    # -------------------------------------------------------------------------

    def __eq__(self, other) -> 'pl.Series':
        """Element-wise equality comparison. Returns boolean Series."""
        if isinstance(other, NumberColumn):
            self._check_same_unit(other._unit)
            return self._series == other._series
        if isinstance(other, Number):
            self._check_same_unit(other.unit)
            return self._series == other.quantity
        if isinstance(other, (int, float)):
            return self._series == other
        return NotImplemented

    def __ne__(self, other) -> 'pl.Series':
        """Element-wise inequality comparison. Returns boolean Series."""
        if isinstance(other, NumberColumn):
            self._check_same_unit(other._unit)
            return self._series != other._series
        if isinstance(other, Number):
            self._check_same_unit(other.unit)
            return self._series != other.quantity
        if isinstance(other, (int, float)):
            return self._series != other
        return NotImplemented

    def __lt__(self, other) -> 'pl.Series':
        """Element-wise less-than comparison. Returns boolean Series."""
        if isinstance(other, NumberColumn):
            self._check_same_unit(other._unit)
            return self._series < other._series
        if isinstance(other, Number):
            self._check_same_unit(other.unit)
            return self._series < other.quantity
        if isinstance(other, (int, float)):
            return self._series < other
        return NotImplemented

    def __le__(self, other) -> 'pl.Series':
        """Element-wise less-than-or-equal comparison. Returns boolean Series."""
        if isinstance(other, NumberColumn):
            self._check_same_unit(other._unit)
            return self._series <= other._series
        if isinstance(other, Number):
            self._check_same_unit(other.unit)
            return self._series <= other.quantity
        if isinstance(other, (int, float)):
            return self._series <= other
        return NotImplemented

    def __gt__(self, other) -> 'pl.Series':
        """Element-wise greater-than comparison. Returns boolean Series."""
        if isinstance(other, NumberColumn):
            self._check_same_unit(other._unit)
            return self._series > other._series
        if isinstance(other, Number):
            self._check_same_unit(other.unit)
            return self._series > other.quantity
        if isinstance(other, (int, float)):
            return self._series > other
        return NotImplemented

    def __ge__(self, other) -> 'pl.Series':
        """Element-wise greater-than-or-equal comparison. Returns boolean Series."""
        if isinstance(other, NumberColumn):
            self._check_same_unit(other._unit)
            return self._series >= other._series
        if isinstance(other, Number):
            self._check_same_unit(other.unit)
            return self._series >= other.quantity
        if isinstance(other, (int, float)):
            return self._series >= other
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
        a: 'pl.Series',
        ua: Union[float, 'pl.Series', None],
        b: Union[float, 'pl.Series'],
        ub: Union[float, None],
    ) -> Union[float, 'pl.Series', None]:
        """Propagate uncertainty through multiplication."""
        if ua is None and ub is None:
            return None

        # Relative uncertainties
        if ua is not None:
            if isinstance(ua, float):
                rel_a = ua / a.abs()
            else:
                rel_a = ua.abs() / a.abs()
            rel_a = rel_a.fill_nan(0).fill_null(0)
        else:
            rel_a = pl.Series([0.0] * len(a))

        if ub is not None:
            if isinstance(b, pl.Series):
                rel_b = abs(ub) / b.abs()
                rel_b = rel_b.fill_nan(0).fill_null(0)
            else:
                rel_b = abs(ub) / abs(b) if b != 0 else 0
        else:
            if isinstance(b, pl.Series):
                rel_b = pl.Series([0.0] * len(b))
            else:
                rel_b = 0

        rel_c = (rel_a**2 + rel_b**2).map_elements(math.sqrt, return_dtype=pl.Float64)
        result = (a * b).abs() * rel_c

        return result

    def _propagate_div_uncertainty(
        self,
        a: 'pl.Series',
        ua: Union[float, 'pl.Series', None],
        b: Union[float, 'pl.Series'],
        ub: Union[float, None],
    ) -> Union[float, 'pl.Series', None]:
        """Propagate uncertainty through division (same as multiplication)."""
        return self._propagate_mul_uncertainty(a, ua, b, ub)

    def _propagate_add_uncertainty(
        self,
        ua: Union[float, 'pl.Series', None],
        ub: Union[float, 'pl.Series', None],
    ) -> Union[float, 'pl.Series', None]:
        """Propagate uncertainty through addition/subtraction."""
        if ua is None and ub is None:
            return None

        if ua is None:
            return ub
        if ub is None:
            return ua

        if isinstance(ua, float) and isinstance(ub, float):
            return math.sqrt(ua**2 + ub**2)

        # Convert to series if needed
        if isinstance(ua, float):
            ua_sq = ua**2
        else:
            ua_sq = ua**2

        if isinstance(ub, float):
            ub_sq = ub**2
        else:
            ub_sq = ub**2

        result = (ua_sq + ub_sq).map_elements(math.sqrt, return_dtype=pl.Float64)
        return result

    # -------------------------------------------------------------------------
    # Conversion
    # -------------------------------------------------------------------------

    def to(self, target: Union[Unit, UnitProduct], graph=None) -> 'NumberColumn':
        """Convert all values to a different unit.

        Parameters
        ----------
        target : Unit or UnitProduct
            The target unit to convert to.
        graph : ConversionGraph, optional
            The conversion graph to use. Defaults to the global default graph.

        Returns
        -------
        NumberColumn
            A new NumberColumn with converted values.
        """
        from ucon.graph import get_default_graph

        # Normalize to UnitProduct
        src = self._unit if isinstance(self._unit, UnitProduct) else UnitProduct.from_unit(self._unit)
        dst = target if isinstance(target, UnitProduct) else UnitProduct.from_unit(target)

        # Scale-only conversion (no graph needed)
        if self._is_scale_only_conversion(src, dst):
            factor = src.fold_scale() / dst.fold_scale()
            new_unc = None
            if self._uncertainty is not None:
                if isinstance(self._uncertainty, float):
                    new_unc = self._uncertainty * abs(factor)
                else:
                    new_unc = self._uncertainty * abs(factor)
            return NumberColumn(
                series=self._series * factor,
                unit=target,
                uncertainty=new_unc,
            )

        # Graph-based conversion
        if graph is None:
            graph = get_default_graph()

        conversion_map = graph.convert(src=src, dst=dst)

        # Apply map to series values
        converted = self._series.map_elements(conversion_map, return_dtype=pl.Float64)

        # Propagate uncertainty through conversion
        new_unc = None
        if self._uncertainty is not None:
            derivative = self._series.map_elements(
                lambda x: abs(conversion_map.derivative(x)),
                return_dtype=pl.Float64
            )
            if isinstance(self._uncertainty, float):
                new_unc = derivative * self._uncertainty
            else:
                new_unc = derivative * self._uncertainty

        return NumberColumn(series=converted, unit=target, uncertainty=new_unc)

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
    # Reduction Operations
    # -------------------------------------------------------------------------

    def sum(self) -> Number:
        """Sum all values."""
        total = float(self._series.sum())

        unc = None
        if self._uncertainty is not None:
            if isinstance(self._uncertainty, float):
                unc = self._uncertainty * math.sqrt(len(self))
            else:
                unc = float(math.sqrt((self._uncertainty**2).sum()))

        return Number(quantity=total, unit=self._unit, uncertainty=unc)

    def mean(self) -> Number:
        """Compute the mean."""
        avg = float(self._series.mean())

        unc = None
        if self._uncertainty is not None:
            if isinstance(self._uncertainty, float):
                unc = self._uncertainty / math.sqrt(len(self))
            else:
                unc = float(math.sqrt((self._uncertainty**2).sum()) / len(self))

        return Number(quantity=avg, unit=self._unit, uncertainty=unc)

    def std(self, ddof: int = 1) -> Number:
        """Compute the standard deviation."""
        s = float(self._series.std(ddof=ddof))
        return Number(quantity=s, unit=self._unit, uncertainty=None)

    def min(self) -> Number:
        """Return the minimum value."""
        idx = self._series.arg_min()
        return self[idx]  # type: ignore

    def max(self) -> Number:
        """Return the maximum value."""
        idx = self._series.arg_max()
        return self[idx]  # type: ignore

    def to_list(self) -> list:
        """Convert to a list of Number instances."""
        return list(self)


# Export check
__all__ = ['NumberColumn', 'HAS_POLARS']
