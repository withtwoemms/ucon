# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
ucon.core.scale
===============

Magnitude prefix types: :class:`Exponent` and :class:`Scale`.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache, reduce, total_ordering
from typing import TYPE_CHECKING, Dict, Tuple, Union

if TYPE_CHECKING:
    from ucon.core.unit import Unit, UnitFactor
    from ucon.core.product import UnitProduct


@total_ordering
class Exponent:
    """
    Represents a **base–exponent pair** (e.g., 10³ or 2¹⁰).

    Provides comparison and division semantics used internally to represent
    magnitude prefixes (e.g., kilo, mega, micro).
    """
    bases = {2: math.log2, 10: math.log10}

    __slots__ = ("base", "power")

    def __init__(self, base: int, power: Union[int, float]):
        if base not in self.bases.keys():
            raise ValueError(f'Only the following bases are supported: {reduce(lambda a,b: f"{a}, {b}", self.bases.keys())}')
        self.base = base
        self.power = power

    @property
    def evaluated(self) -> float:
        """Return the numeric value of base ** power."""
        return self.base ** self.power

    def parts(self) -> Tuple[int, Union[int, float]]:
        """Return (base, power) tuple, used for Scale lookups."""
        return self.base, self.power

    def __eq__(self, other: 'Exponent'):
        if not isinstance(other, Exponent):
            raise TypeError(f'Cannot compare Exponent to non-Exponent type: {type(other)}')
        return self.evaluated == other.evaluated

    def __lt__(self, other: 'Exponent'):
        if not isinstance(other, Exponent):
            return NotImplemented
        return self.evaluated < other.evaluated

    def __hash__(self):
        # Hash by rounded numeric equivalence to maintain cross-base consistency
        return hash(round(self.evaluated, 15))

    # ---------- Arithmetic Semantics ----------

    def __truediv__(self, other: 'Exponent'):
        """
        Divide two Exponents.
        - If bases match, returns a relative Exponent.
        - If bases differ, returns a numeric ratio (float).
        """
        if not isinstance(other, Exponent):
            return NotImplemented
        if self.base == other.base:
            return Exponent(self.base, self.power - other.power)
        return self.evaluated / other.evaluated

    def __mul__(self, other: 'Exponent'):
        if not isinstance(other, Exponent):
            return NotImplemented
        if self.base == other.base:
            return Exponent(self.base, self.power + other.power)
        return float(self.evaluated * other.evaluated)

    def __pow__(self, exponent: Union[int, float]) -> "Exponent":
        """
        Raise this Exponent to a numeric power.

        Example:
            Exponent(10, 3) ** 2
            # → Exponent(base=10, power=6)
        """
        return Exponent(self.base, self.power * exponent)

    # ---------- Conversion Utilities ----------

    def to_base(self, new_base: int) -> "Exponent":
        """
        Convert this Exponent to another base representation.

        Example:
            Exponent(2, 10).to_base(10)
            # → Exponent(base=10, power=3.010299956639812)
        """
        if new_base not in self.bases:
            supported = ", ".join(map(str, self.bases))
            raise ValueError(f"Unsupported base {new_base!r}. Supported bases: {supported}")
        new_power = self.bases[new_base](self.evaluated)
        return Exponent(new_base, new_power)

    # ---------- Numeric Interop ----------

    def __float__(self) -> float:
        return float(self.evaluated)

    def __int__(self) -> int:
        return int(self.evaluated)

    # ---------- Representation ----------

    def __repr__(self) -> str:
        return f"Exponent(base={self.base}, power={self.power})"

    def __str__(self) -> str:
        return f"{self.base}^{self.power}"


# --------------------------------------------------------------------------------------
# Scale (with descriptor)
# --------------------------------------------------------------------------------------

@dataclass(frozen=True)
class _ScaleDescriptor:
    exponent: Exponent
    shorthand: str
    alias: str

    @property
    def evaluated(self) -> float:
        return self.exponent.evaluated

    @property
    def base(self) -> int:
        return self.exponent.base

    @property
    def power(self) -> Union[int, float]:
        return self.exponent.power

    def parts(self) -> Tuple[int, Union[int, float]]:
        return (self.base, self.power)

    def __repr__(self):
        tag = self.alias or self.shorthand or "1"
        return f"<_ScaleDescriptor {tag}: {self.base}^{self.power}>"


@total_ordering
class Scale(Enum):
    # Binary
    exbi  = _ScaleDescriptor(Exponent(2, 60), "Ei", "exbi")
    pebi  = _ScaleDescriptor(Exponent(2, 50), "Pi", "pebi")
    tebi  = _ScaleDescriptor(Exponent(2, 40), "Ti", "tebi")
    gibi  = _ScaleDescriptor(Exponent(2, 30), "Gi", "gibi")
    mebi  = _ScaleDescriptor(Exponent(2, 20), "Mi", "mebi")
    kibi  = _ScaleDescriptor(Exponent(2, 10), "Ki", "kibi")

    # Decimal
    peta  = _ScaleDescriptor(Exponent(10, 15), "P", "peta")
    tera  = _ScaleDescriptor(Exponent(10, 12), "T", "tera")
    giga  = _ScaleDescriptor(Exponent(10, 9),  "G", "giga")
    mega  = _ScaleDescriptor(Exponent(10, 6),  "M", "mega")
    kilo  = _ScaleDescriptor(Exponent(10, 3),  "k", "kilo")
    hecto = _ScaleDescriptor(Exponent(10, 2),  "h", "hecto")
    deca  = _ScaleDescriptor(Exponent(10, 1),  "da", "deca")
    one   = _ScaleDescriptor(Exponent(10, 0),  "",  "")
    deci  = _ScaleDescriptor(Exponent(10,-1),  "d", "deci")
    centi = _ScaleDescriptor(Exponent(10,-2),  "c", "centi")
    milli = _ScaleDescriptor(Exponent(10,-3),  "m", "milli")
    micro = _ScaleDescriptor(Exponent(10,-6),  "µ", "micro")
    nano  = _ScaleDescriptor(Exponent(10,-9),  "n", "nano")
    pico  = _ScaleDescriptor(Exponent(10,-12), "p", "pico")
    femto = _ScaleDescriptor(Exponent(10,-15), "f", "femto")

    @property
    def descriptor(self) -> _ScaleDescriptor:
        return self.value

    @property
    def shorthand(self) -> str:
        return self.value.shorthand

    @property
    def alias(self) -> str:
        return self.value.alias

    @staticmethod
    @lru_cache(maxsize=1)
    def all() -> Dict[Tuple[int, int], str]:
        return {(s.value.base, s.value.power): s.name for s in Scale}

    @classmethod
    @lru_cache(maxsize=1)
    def _decimal_scales(cls):
        return [s for s in cls if s.value.base == 10]

    @classmethod
    @lru_cache(maxsize=1)
    def _binary_scales(cls):
        return [s for s in cls if s.value.base == 2]

    @staticmethod
    @lru_cache(maxsize=1)
    def by_value() -> Dict[float, str]:
        """
        Return a map from evaluated numeric value → Scale name.
        Cached after first access.
        """
        return {round(s.value.exponent.evaluated, 15): s.name for s in Scale}

    @classmethod
    def nearest(cls, value: float, include_binary: bool = False, undershoot_bias: float = 0.75) -> "Scale":
        if value == 0:
            return Scale.one
        abs_val = abs(value)
        candidates = list(cls) if include_binary else cls._decimal_scales()

        def distance(scale: "Scale") -> float:
            ratio = abs_val / scale.value.evaluated
            diff = math.log10(ratio)
            if ratio < 1:
                diff /= undershoot_bias
            return abs(diff)

        return min(candidates, key=distance)

    def __eq__(self, other: 'Scale'):
        return self.value.exponent == other.value.exponent

    def __gt__(self, other: 'Scale'):
        return self.value.exponent > other.value.exponent

    def __hash__(self):
        e = self.value.exponent
        return hash((e.base, round(e.power, 12)))

    def __mul__(self, other):
        # Import here to avoid circular import at class definition time.
        # Scale.__mul__ references Unit and UnitProduct which are defined
        # in sibling modules within the same core package.
        from ucon.core.unit import Unit, UnitFactor
        from ucon.core.product import UnitProduct

        # --- Case 1: applying Scale to simple Unit --------------------
        if isinstance(other, Unit):
            return UnitProduct({UnitFactor(unit=other, scale=self): 1})

        # --- Case 2: other cases are NOT handled here -----------------
        # UnitProduct scaling is handled solely by UnitProduct.__rmul__
        if isinstance(other, UnitProduct):
            return NotImplemented

        # --- Case 3: Scale * Scale algebra ----------------------------
        if isinstance(other, Scale):
            if self is Scale.one:
                return other
            if other is Scale.one:
                return self

            result = self.value.exponent * other.value.exponent
            include_binary = 2 in {self.value.base, other.value.base}

            if isinstance(result, Exponent):
                match = Scale.all().get(result.parts())
                if match:
                    return Scale[match]

            return Scale.nearest(float(result), include_binary=include_binary)

        return NotImplemented

    def __truediv__(self, other):
        if not isinstance(other, Scale):
            return NotImplemented
        if self == other:
            return Scale.one
        result = self.value.exponent / other.value.exponent
        if isinstance(result, Exponent):
            match = Scale.all().get(result.parts())
            if match:
                return Scale[match]
        include_binary = 2 in {self.value.base, other.value.base}
        return Scale.nearest(float(result), include_binary=include_binary)

    def __pow__(self, power):
        result = self.value.exponent ** power
        if isinstance(result, Exponent):
            match = Scale.all().get(result.parts())
            if match:
                return Scale[match]
        include_binary = self.value.base == 2
        return Scale.nearest(float(result), include_binary=include_binary)
