# ucon/pandas.py
#
# Pandas integration for ucon.

"""
Pandas integration for ucon.

This module provides NumberSeries and a pandas accessor for working with
unit-aware Series data.

Requires: pip install ucon[pandas]

Example:
    >>> import pandas as pd
    >>> from ucon import units
    >>> from ucon.pandas import NumberSeries
    >>>
    >>> heights = NumberSeries(pd.Series([1.7, 1.8, 1.9]), unit=units.meter)
    >>> heights.to(units.foot)
    <NumberSeries [5.577, 5.905, 6.233] ft>
    >>>
    >>> # Or using the accessor:
    >>> df = pd.DataFrame({'height': [1.7, 1.8, 1.9]})
    >>> df['height'].ucon.with_unit(units.meter).to(units.foot)
"""

from __future__ import annotations

import math
from typing import Union, TYPE_CHECKING, Iterator, Optional

try:
    import pandas as pd
    _HAS_PANDAS = True
except ImportError:
    _HAS_PANDAS = False
    pd = None  # type: ignore

if TYPE_CHECKING:
    import pandas as pd

from ucon.core import Unit, UnitProduct, UnitFactor, Scale, Number, _none


def _require_pandas() -> None:
    """Raise ImportError if pandas is not available."""
    if not _HAS_PANDAS:
        raise ImportError(
            "Pandas is required for NumberSeries. "
            "Install with: pip install ucon[pandas]"
        )


class NumberSeries:
    """
    A pandas Series with an associated unit.

    Combines a pandas Series of magnitudes with a unit, enabling vectorized
    arithmetic and conversion while preserving pandas functionality.

    Parameters
    ----------
    series : pd.Series
        The numeric values.
    unit : Unit or UnitProduct, optional
        The unit for all values. Defaults to dimensionless.
    uncertainty : float or pd.Series, optional
        Uncertainty value(s). If scalar, applies uniformly to all elements.
        If Series, must have the same index.

    Examples
    --------
    >>> import pandas as pd
    >>> from ucon import units
    >>> from ucon.pandas import NumberSeries

    Create from Series:

    >>> heights = NumberSeries(pd.Series([1.7, 1.8, 1.9]), unit=units.meter)
    >>> len(heights)
    3

    Vectorized conversion:

    >>> heights_ft = heights.to(units.foot)

    With uncertainty:

    >>> temps = NumberSeries(pd.Series([20, 21, 22]), unit=units.celsius, uncertainty=0.5)
    """

    __slots__ = ('_series', '_unit', '_uncertainty')

    def __init__(
        self,
        series: 'pd.Series',
        unit: Union[Unit, UnitProduct, None] = None,
        uncertainty: Union[float, 'pd.Series', None] = None,
    ):
        _require_pandas()

        if not isinstance(series, pd.Series):
            series = pd.Series(series)

        self._series: pd.Series = series.astype(float)
        self._unit = unit if unit is not None else _none

        if uncertainty is not None:
            if isinstance(uncertainty, (int, float)):
                self._uncertainty: Union[float, pd.Series, None] = float(uncertainty)
            else:
                self._uncertainty = pd.Series(uncertainty, dtype=float)
                if len(self._uncertainty) != len(self._series):
                    raise ValueError(
                        f"Uncertainty length {len(self._uncertainty)} does not match "
                        f"series length {len(self._series)}"
                    )
        else:
            self._uncertainty = None

    @property
    def series(self) -> 'pd.Series':
        """The underlying pandas Series."""
        return self._series

    @property
    def values(self) -> 'pd.Series':
        """Alias for series (for compatibility)."""
        return self._series

    @property
    def unit(self) -> Union[Unit, UnitProduct]:
        """The unit shared by all values."""
        return self._unit

    @property
    def uncertainty(self) -> Union[float, 'pd.Series', None]:
        """The uncertainty (scalar or per-element Series)."""
        return self._uncertainty

    @property
    def index(self) -> 'pd.Index':
        """The pandas index."""
        return self._series.index

    def __len__(self) -> int:
        """Return the number of elements."""
        return len(self._series)

    @property
    def shape(self) -> tuple:
        """Shape of the series."""
        return self._series.shape

    @property
    def dtype(self) -> 'pd.api.types.CategoricalDtype':
        """Data type of the series."""
        return self._series.dtype

    @property
    def dimension(self):
        """The physical dimension of the quantities."""
        if hasattr(self._unit, 'dimension'):
            return self._unit.dimension
        return None

    def __getitem__(self, key) -> Union[Number, 'NumberSeries']:
        """Index or slice the series."""
        val = self._series[key]

        # Determine uncertainty for the selection
        if self._uncertainty is None:
            unc = None
        elif isinstance(self._uncertainty, float):
            unc = self._uncertainty
        else:
            unc = self._uncertainty[key]

        # Return Number for scalar, NumberSeries for slice
        if isinstance(val, (int, float)):
            unc_val = float(unc) if unc is not None and not isinstance(unc, float) else unc
            return Number(quantity=float(val), unit=self._unit, uncertainty=unc_val)
        else:
            return NumberSeries(series=val, unit=self._unit, uncertainty=unc)

    def __iter__(self) -> Iterator[Number]:
        """Iterate as Number instances."""
        for idx in self._series.index:
            yield self[idx]  # type: ignore

    def __repr__(self) -> str:
        """String representation."""
        # Format values with truncation for large series
        if len(self._series) <= 6:
            vals_str = ', '.join(f'{x:.4g}' for x in self._series)
        else:
            head = ', '.join(f'{x:.4g}' for x in self._series.iloc[:3])
            tail = ', '.join(f'{x:.4g}' for x in self._series.iloc[-3:])
            vals_str = f'{head}, ..., {tail}'

        unit_str = self._format_unit()

        if self._uncertainty is None:
            return f'<NumberSeries [{vals_str}] {unit_str}>'
        elif isinstance(self._uncertainty, float):
            return f'<NumberSeries [{vals_str}] \u00b1 {self._uncertainty:.4g} {unit_str}>'
        else:
            return f'<NumberSeries [{vals_str}] \u00b1 [...] {unit_str}>'

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

    def __mul__(self, other) -> 'NumberSeries':
        """Multiply by scalar, Number, or NumberSeries."""
        if isinstance(other, (int, float)):
            new_unc = None
            if self._uncertainty is not None:
                new_unc = self._uncertainty * abs(other)
            return NumberSeries(
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
            return NumberSeries(series=result, unit=result_unit, uncertainty=new_unc)

        if isinstance(other, NumberSeries):
            if len(self) != len(other):
                raise ValueError(f"Length mismatch: {len(self)} vs {len(other)}")

            result = self._series * other._series
            result_unit = self._unit * other._unit
            new_unc = self._propagate_mul_uncertainty(
                self._series, self._uncertainty,
                other._series, other._uncertainty
            )
            return NumberSeries(series=result, unit=result_unit, uncertainty=new_unc)

        return NotImplemented

    def __rmul__(self, other) -> 'NumberSeries':
        """Right multiplication."""
        return self.__mul__(other)

    def __truediv__(self, other) -> 'NumberSeries':
        """Divide by scalar, Number, or NumberSeries."""
        if isinstance(other, (int, float)):
            new_unc = None
            if self._uncertainty is not None:
                new_unc = self._uncertainty / abs(other)
            return NumberSeries(
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
            return NumberSeries(series=result, unit=result_unit, uncertainty=new_unc)

        if isinstance(other, NumberSeries):
            if len(self) != len(other):
                raise ValueError(f"Length mismatch: {len(self)} vs {len(other)}")

            result = self._series / other._series
            result_unit = self._unit / other._unit
            new_unc = self._propagate_div_uncertainty(
                self._series, self._uncertainty,
                other._series, other._uncertainty
            )
            return NumberSeries(series=result, unit=result_unit, uncertainty=new_unc)

        return NotImplemented

    def __add__(self, other) -> 'NumberSeries':
        """Add NumberSeries or Number (same unit required)."""
        if isinstance(other, Number):
            self._check_same_unit(other.unit)
            result = self._series + other.quantity
            new_unc = self._propagate_add_uncertainty(
                self._uncertainty, other.uncertainty
            )
            return NumberSeries(series=result, unit=self._unit, uncertainty=new_unc)

        if isinstance(other, NumberSeries):
            self._check_same_unit(other._unit)
            if len(self) != len(other):
                raise ValueError(f"Length mismatch: {len(self)} vs {len(other)}")

            result = self._series + other._series
            new_unc = self._propagate_add_uncertainty(
                self._uncertainty, other._uncertainty
            )
            return NumberSeries(series=result, unit=self._unit, uncertainty=new_unc)

        return NotImplemented

    def __radd__(self, other) -> 'NumberSeries':
        """Right addition."""
        return self.__add__(other)

    def __sub__(self, other) -> 'NumberSeries':
        """Subtract NumberSeries or Number (same unit required)."""
        if isinstance(other, Number):
            self._check_same_unit(other.unit)
            result = self._series - other.quantity
            new_unc = self._propagate_add_uncertainty(
                self._uncertainty, other.uncertainty
            )
            return NumberSeries(series=result, unit=self._unit, uncertainty=new_unc)

        if isinstance(other, NumberSeries):
            self._check_same_unit(other._unit)
            if len(self) != len(other):
                raise ValueError(f"Length mismatch: {len(self)} vs {len(other)}")

            result = self._series - other._series
            new_unc = self._propagate_add_uncertainty(
                self._uncertainty, other._uncertainty
            )
            return NumberSeries(series=result, unit=self._unit, uncertainty=new_unc)

        return NotImplemented

    def __neg__(self) -> 'NumberSeries':
        """Negation."""
        return NumberSeries(
            series=-self._series,
            unit=self._unit,
            uncertainty=self._uncertainty,
        )

    def __abs__(self) -> 'NumberSeries':
        """Absolute value."""
        return NumberSeries(
            series=self._series.abs(),
            unit=self._unit,
            uncertainty=self._uncertainty,
        )

    # -------------------------------------------------------------------------
    # Comparison Operators
    # -------------------------------------------------------------------------

    def __eq__(self, other) -> 'pd.Series':
        """Element-wise equality comparison. Returns boolean Series."""
        if isinstance(other, NumberSeries):
            self._check_same_unit(other._unit)
            return self._series == other._series
        if isinstance(other, Number):
            self._check_same_unit(other.unit)
            return self._series == other.quantity
        if isinstance(other, (int, float)):
            return self._series == other
        return NotImplemented

    def __ne__(self, other) -> 'pd.Series':
        """Element-wise inequality comparison. Returns boolean Series."""
        if isinstance(other, NumberSeries):
            self._check_same_unit(other._unit)
            return self._series != other._series
        if isinstance(other, Number):
            self._check_same_unit(other.unit)
            return self._series != other.quantity
        if isinstance(other, (int, float)):
            return self._series != other
        return NotImplemented

    def __lt__(self, other) -> 'pd.Series':
        """Element-wise less-than comparison. Returns boolean Series."""
        if isinstance(other, NumberSeries):
            self._check_same_unit(other._unit)
            return self._series < other._series
        if isinstance(other, Number):
            self._check_same_unit(other.unit)
            return self._series < other.quantity
        if isinstance(other, (int, float)):
            return self._series < other
        return NotImplemented

    def __le__(self, other) -> 'pd.Series':
        """Element-wise less-than-or-equal comparison. Returns boolean Series."""
        if isinstance(other, NumberSeries):
            self._check_same_unit(other._unit)
            return self._series <= other._series
        if isinstance(other, Number):
            self._check_same_unit(other.unit)
            return self._series <= other.quantity
        if isinstance(other, (int, float)):
            return self._series <= other
        return NotImplemented

    def __gt__(self, other) -> 'pd.Series':
        """Element-wise greater-than comparison. Returns boolean Series."""
        if isinstance(other, NumberSeries):
            self._check_same_unit(other._unit)
            return self._series > other._series
        if isinstance(other, Number):
            self._check_same_unit(other.unit)
            return self._series > other.quantity
        if isinstance(other, (int, float)):
            return self._series > other
        return NotImplemented

    def __ge__(self, other) -> 'pd.Series':
        """Element-wise greater-than-or-equal comparison. Returns boolean Series."""
        if isinstance(other, NumberSeries):
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
        a: 'pd.Series',
        ua: Union[float, 'pd.Series', None],
        b: Union[float, 'pd.Series'],
        ub: Union[float, None],
    ) -> Union[float, 'pd.Series', None]:
        """Propagate uncertainty through multiplication."""
        if ua is None and ub is None:
            return None

        # Relative uncertainties
        if ua is not None:
            rel_a = (abs(ua) / abs(a)).fillna(0).replace([float('inf')], 0)
        else:
            rel_a = 0

        if ub is not None:
            if isinstance(b, pd.Series):
                rel_b = (abs(ub) / abs(b)).fillna(0).replace([float('inf')], 0)
            else:
                rel_b = abs(ub) / abs(b) if b != 0 else 0
        else:
            rel_b = 0

        import numpy as np
        rel_c = np.sqrt(rel_a**2 + rel_b**2)
        result = abs(a * b) * rel_c

        # Return scalar if result is uniform
        if isinstance(result, pd.Series) and result.nunique() == 1:
            return float(result.iloc[0])

        return result

    def _propagate_div_uncertainty(
        self,
        a: 'pd.Series',
        ua: Union[float, 'pd.Series', None],
        b: Union[float, 'pd.Series'],
        ub: Union[float, None],
    ) -> Union[float, 'pd.Series', None]:
        """Propagate uncertainty through division (same as multiplication)."""
        return self._propagate_mul_uncertainty(a, ua, b, ub)

    def _propagate_add_uncertainty(
        self,
        ua: Union[float, 'pd.Series', None],
        ub: Union[float, 'pd.Series', None],
    ) -> Union[float, 'pd.Series', None]:
        """Propagate uncertainty through addition/subtraction."""
        if ua is None and ub is None:
            return None

        if ua is None:
            return ub
        if ub is None:
            return ua

        import numpy as np
        result = np.sqrt(ua**2 + ub**2)

        # Return scalar if both inputs were scalar
        if isinstance(ua, float) and isinstance(ub, float):
            return float(result)

        return result

    # -------------------------------------------------------------------------
    # Conversion
    # -------------------------------------------------------------------------

    def to(self, target: Union[Unit, UnitProduct], graph=None) -> 'NumberSeries':
        """Convert all values to a different unit.

        Parameters
        ----------
        target : Unit or UnitProduct
            The target unit to convert to.
        graph : ConversionGraph, optional
            The conversion graph to use. Defaults to the global default graph.

        Returns
        -------
        NumberSeries
            A new NumberSeries with converted values.
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
                new_unc = self._uncertainty * abs(factor)
            return NumberSeries(
                series=self._series * factor,
                unit=target,
                uncertainty=new_unc,
            )

        # Graph-based conversion
        if graph is None:
            graph = get_default_graph()

        conversion_map = graph.convert(src=src, dst=dst)

        # Apply map to series values
        converted = self._series.apply(conversion_map)

        # Propagate uncertainty through conversion
        new_unc = None
        if self._uncertainty is not None:
            derivative = self._series.apply(lambda x: abs(conversion_map.derivative(x)))
            new_unc = derivative * self._uncertainty

        return NumberSeries(series=converted, unit=target, uncertainty=new_unc)

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
    # Pandas Integration
    # -------------------------------------------------------------------------

    def to_frame(self, name: Optional[str] = None) -> 'pd.DataFrame':
        """Convert to DataFrame with unit in column name."""
        col_name = name or f'value ({self._format_unit()})'
        return pd.DataFrame({col_name: self._series})

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
        idx = self._series.idxmin()
        return self[idx]  # type: ignore

    def max(self) -> Number:
        """Return the maximum value."""
        idx = self._series.idxmax()
        return self[idx]  # type: ignore


# -----------------------------------------------------------------------------
# Pandas Accessor
# -----------------------------------------------------------------------------

if _HAS_PANDAS:
    @pd.api.extensions.register_series_accessor("ucon")
    class UconSeriesAccessor:
        """
        Pandas Series accessor for ucon unit operations.

        Enables syntax like:
            df['height'].ucon.with_unit(units.meter).to(units.foot)

        Examples
        --------
        >>> import pandas as pd
        >>> from ucon import units
        >>>
        >>> df = pd.DataFrame({'height_m': [1.7, 1.8, 1.9]})
        >>> heights = df['height_m'].ucon.with_unit(units.meter)
        >>> heights.to(units.foot)
        """

        def __init__(self, series: 'pd.Series'):
            self._series = series
            self._unit: Union[Unit, UnitProduct, None] = None
            self._uncertainty: Union[float, 'pd.Series', None] = None

        def with_unit(
            self,
            unit: Union[Unit, UnitProduct],
            uncertainty: Union[float, 'pd.Series', None] = None
        ) -> NumberSeries:
            """
            Associate a unit with this Series.

            Parameters
            ----------
            unit : Unit or UnitProduct
                The unit for the values.
            uncertainty : float or pd.Series, optional
                The measurement uncertainty.

            Returns
            -------
            NumberSeries
                A NumberSeries wrapping the data with unit metadata.
            """
            return NumberSeries(
                series=self._series,
                unit=unit,
                uncertainty=uncertainty,
            )

        def __call__(
            self,
            unit: Union[Unit, UnitProduct],
            uncertainty: Union[float, 'pd.Series', None] = None
        ) -> NumberSeries:
            """Shorthand for with_unit()."""
            return self.with_unit(unit, uncertainty)


# Export check
__all__ = ['NumberSeries']
if _HAS_PANDAS:
    __all__.append('UconSeriesAccessor')
