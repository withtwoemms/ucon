#!/usr/bin/env python3
"""
Base-form drift detector for v1.3.0.
====================================

PURPOSE
-------
Validate that the hand-written ``base_form=...`` literals in
``ucon/units.py`` agree with the canonical decomposition that the v1.2.x
graph-propagation algorithm would have computed.

Until v1.4.0 introduces a TOML-as-source representation of the unit catalog,
the only way to catch a bad hand-written prefactor is to compare against an
authoritative source.  That source — for now — is the BFS propagator that
v1.3.0 has *deleted* from production code (``ucon/graph.py``) but which we
keep alive **here**, in this script, exclusively for verification.

LIFECYCLE
---------
- Authored: v1.3.0 (this release)
- Active:   v1.3.0 — v1.3.x maintenance window
- Retired:  v1.4.0, when ``ucon.toml`` becomes the source of truth and an
  equivalent stub generator (``scripts/generate_base_form_stubs.py``) takes
  over.

When v1.4.0 lands, **delete this file in the same PR** that introduces the
TOML loader.  Do not let it live on as a third source of truth.

USAGE
-----
    python scripts/generate_base_forms.py --check    # exit non-zero on drift
    python scripts/generate_base_forms.py --report   # human-readable diff
    python scripts/generate_base_forms.py --emit     # JSON dump of expected

CI integration: ``make base-forms-check`` runs ``--check``.

ALGORITHM
---------
1. Build a fresh ``ConversionGraph`` (which, after v1.3.0, no longer
   propagates ``base_form`` as a side effect).
2. For each SI dimension partition, run a BFS from the coherent reference
   unit (kg, m, s, ..., or newton, joule, pascal, ... for derived dimensions),
   computing each reachable unit's expected ``(prefactor, factors)`` tuple by
   applying the slope of each ``LinearMap``/``AffineMap`` edge.
3. Compare each computed pair to the unit's actual ``base_form`` attribute.
4. Report discrepancies.

The BFS implementation below is a **preserved copy** of the v1.2.x graph
propagation algorithm that v1.3.0 has deleted from ``ucon/graph.py``.  It
is intentionally inlined and not imported from production code, so that
deletion of the production version does not break this script.  Do **not**
refactor it to share code with ``ucon.graph``.

NON-GOALS
---------
- Does NOT modify ``ucon/units.py``.  Drift indicates either a bad hand-edit
  or a legitimate change that needs human review — never an automatic fix.
- Does NOT validate affine units (kelvin/celsius/fahrenheit/rankine/réaumur)
  or logarithmic units (decibel/bel/neper).  Those have ``base_form=None``
  by definition; the script asserts that they remain ``None``.
- Does NOT validate non-SI-basis units (CGS, Natural).  The deleted v1.2.x
  algorithm only ever computed ``base_form`` for SI-basis units, and v1.3.0
  preserves that behavior; CGS/Natural ``base_form`` values are tracked
  manually in ``ucon/units.py`` and verified by the regular test suite.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from pathlib import Path
from typing import Any

# Ensure we import from the local package, not a globally installed copy.
sys.path.insert(0, str(Path(__file__).parent.parent))

from ucon import units as ucon_units
from ucon.core import BaseForm, RebasedUnit, Unit
from ucon.graph import ConversionGraph, get_default_graph
from ucon.maps import AffineMap, LinearMap


# ----------------------------------------------------------------------
# Configuration: which units the v1.2.x BFS would have populated.
# ----------------------------------------------------------------------
# These two tables are an exact copy of the corresponding tables in the
# v1.2.x graph propagation algorithm, preserved here so the drift checker
# remains self-contained.

_SI_ROOT_NAMES = [
    ('MASS', 'kilogram'),
    ('LENGTH', 'meter'),
    ('TIME', 'second'),
    ('CURRENT', 'ampere'),
    ('TEMPERATURE', 'kelvin'),
    ('LUMINOUS_INTENSITY', 'candela'),
    ('AMOUNT_OF_SUBSTANCE', 'mole'),
    ('INFORMATION', 'bit'),
]

_COHERENT_SI_NAMES = {
    'force': 'newton',
    'energy': 'joule',
    'power': 'watt',
    'pressure': 'pascal',
    'voltage': 'volt',
    'resistance': 'ohm',
    'charge': 'coulomb',
    'frequency': 'hertz',
    'illuminance': 'lux',
    'capacitance': 'farad',
    'inductance': 'henry',
    'magnetic_flux': 'weber',
    'magnetic_flux_density': 'tesla',
    'conductance': 'siemens',
    'catalytic_activity': 'katal',
    'dynamic_viscosity': 'pascal_second',
    'kinematic_viscosity': 'square_meter_per_second',
    'acceleration': 'meter_per_second_squared',
    'wavenumber': 'reciprocal_meter',
    'radiant_exposure': 'joule_per_square_meter',
    'electric_dipole_moment': 'coulomb_meter',
    'exposure': 'coulomb_per_kilogram',
}

# Affine and logarithmic units MUST have base_form=None.  The drift script
# asserts this category remains ``None``; if any new affine/log unit lands,
# add it to this set explicitly.
_NULL_BASE_FORM_NAMES = {
    'celsius', 'fahrenheit', 'rankine', 'reaumur',
    # logarithmic / dimensionless level units have no (prefactor, factors)
    # representation either; uncomment if/when present:
    # 'decibel', 'bel', 'neper',
}


# ----------------------------------------------------------------------
# Preserved copy of the v1.2.x BFS algorithm.
# ----------------------------------------------------------------------
# Lightly adapted: returns a dict instead of mutating Unit instances.
# DO NOT import from ucon.graph — that version is deleted in v1.3.0.

def _compute_expected_base_forms(graph: ConversionGraph) -> dict[Unit, BaseForm]:
    """Walk the graph the way v1.2.x did and return the expected base_form
    for every reachable SI-basis unit.

    Pure function: does not mutate any Unit.  Returned dict is keyed by the
    actual ``Unit`` object so callers can compare against ``unit.base_form``
    directly.
    """
    from ucon.basis.builtin import SI as SI_BASIS
    from ucon.dimension import (
        AMOUNT_OF_SUBSTANCE,
        CURRENT,
        INFORMATION,
        LENGTH,
        LUMINOUS_INTENSITY,
        MASS,
        TEMPERATURE,
        TIME,
    )

    # Step 1: Resolve SI root units (one per base dimension).
    si_roots = {
        MASS: ucon_units.kilogram,
        LENGTH: ucon_units.meter,
        TIME: ucon_units.second,
        CURRENT: ucon_units.ampere,
        TEMPERATURE: ucon_units.kelvin,
        LUMINOUS_INTENSITY: ucon_units.candela,
        AMOUNT_OF_SUBSTANCE: ucon_units.mole,
        INFORMATION: ucon_units.bit,
    }

    # Step 2: Each root is self-referential: 1 U ≡ 1.0 × U^1.
    expected: dict[Unit, BaseForm] = {}
    for root in si_roots.values():
        expected[root] = BaseForm(factors=((root, 1.0),), prefactor=1.0)

    # Coherent reference unit lookup for derived SI dimensions.
    coherent_si = {
        name: getattr(ucon_units, var)
        for name, var in _COHERENT_SI_NAMES.items()
    }

    # Step 3: Walk every dimension partition in the graph.
    for dim, adjacency in graph._unit_edges.items():
        # Skip non-SI-basis dimensions (CGS, Natural, etc.).
        if not hasattr(dim, 'vector') or dim.vector.basis != SI_BASIS:
            continue
        # Skip pseudo-dimensions (angle, ratio, count, solid_angle).
        if getattr(dim, 'is_pseudo', False):
            continue

        base_expansion = dim.base_expansion()
        if not base_expansion:
            continue  # dimensionless

        # Translate the dimension's base expansion into a (Unit, exp) tuple.
        base_factors_list: list[tuple[Unit, float]] = []
        unsupported = False
        for base_dim, exp in sorted(
            base_expansion.items(), key=lambda item: item[0].name
        ):
            root_unit = si_roots.get(base_dim)
            if root_unit is None:
                unsupported = True
                break
            base_factors_list.append((root_unit, float(exp)))
        if unsupported:
            continue
        base_factors_tuple = tuple(base_factors_list)

        # Choose the reference unit for this dimension.
        ref_unit: Unit | None = None
        dim_name = getattr(dim, 'name', None)
        if dim in si_roots:
            ref_unit = si_roots[dim]
        elif dim_name in coherent_si:
            ref_unit = coherent_si[dim_name]
        else:
            for unit_node in adjacency:
                if isinstance(unit_node, RebasedUnit):
                    continue
                if unit_node in si_roots.values():
                    ref_unit = unit_node
                    break
        if ref_unit is None:
            for unit_node in adjacency:
                if not isinstance(unit_node, RebasedUnit):
                    ref_unit = unit_node
                    break
        if ref_unit is None:
            continue

        # The reference unit's coherent base_form has prefactor 1.0.
        if ref_unit not in expected:
            expected[ref_unit] = BaseForm(
                factors=base_factors_tuple, prefactor=1.0
            )

        # BFS outward, propagating prefactors via LinearMap/AffineMap slope.
        visited = {ref_unit}
        queue: deque = deque([ref_unit])
        while queue:
            current = queue.popleft()
            current_bf = expected.get(current)
            if current_bf is None or current not in adjacency:
                continue

            for neighbor, edge_map in adjacency[current].items():
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                if isinstance(neighbor, RebasedUnit):
                    continue
                if not isinstance(edge_map, (LinearMap, AffineMap)):
                    queue.append(neighbor)
                    continue
                try:
                    slope = edge_map.derivative(1.0)
                except (TypeError, AttributeError):
                    queue.append(neighbor)
                    continue
                if slope == 0:
                    queue.append(neighbor)
                    continue

                # 1 current = slope · neighbor  ⇒  1 neighbor = (1/slope) · current
                # In base units: 1 neighbor = (current.prefactor / slope) · base_product
                new_prefactor = current_bf.prefactor / slope
                if neighbor not in expected:
                    expected[neighbor] = BaseForm(
                        factors=current_bf.factors, prefactor=new_prefactor,
                    )
                queue.append(neighbor)

    return expected


# ----------------------------------------------------------------------
# Comparison + reporting helpers.
# ----------------------------------------------------------------------

# Numerical tolerance for prefactor comparison.  The BFS multiplies floats,
# so an exact equality check is not realistic; ``rel_tol`` follows the same
# convention used in the unit tests (1e-9 for "passes" / 1e-6 for "loose").
_REL_TOL = 1e-9


def _factors_match(a: tuple, b: tuple) -> bool:
    """Compare two ``factors`` tuples by Unit identity and float exponent."""
    if len(a) != len(b):
        return False
    da = {u: e for u, e in a}
    db = {u: e for u, e in b}
    if da.keys() != db.keys():
        return False
    return all(abs(da[u] - db[u]) < 1e-12 for u in da)


def _prefactor_match(a: float, b: float) -> bool:
    if a == b:
        return True
    if a == 0 or b == 0:
        return abs(a - b) < 1e-12
    return abs(a - b) / max(abs(a), abs(b)) < _REL_TOL


def _categorize(unit: Unit) -> str:
    if unit.name in _NULL_BASE_FORM_NAMES:
        return 'null-by-design'
    return 'tracked'


def _diff(actual: BaseForm | None, expected: BaseForm) -> str | None:
    """Return a one-line drift description, or ``None`` if they agree."""
    if actual is None:
        return f'actual=None expected=BaseForm(prefactor={expected.prefactor!r}, ' \
               f'factors={expected.factors!r})'
    if not _factors_match(actual.factors, expected.factors):
        return f'factors mismatch: actual={actual.factors!r} ' \
               f'expected={expected.factors!r}'
    if not _prefactor_match(actual.prefactor, expected.prefactor):
        return f'prefactor mismatch: actual={actual.prefactor!r} ' \
               f'expected={expected.prefactor!r}'
    return None


def _scan() -> tuple[list[tuple[str, str]], dict[str, Any]]:
    """Run the drift comparison.

    Returns ``(drifts, summary)`` where ``drifts`` is a list of
    ``(unit_name, message)`` pairs and ``summary`` is a count dict.
    """
    graph = get_default_graph()
    expected_map = _compute_expected_base_forms(graph)

    drifts: list[tuple[str, str]] = []
    summary = {
        'expected_count': len(expected_map),
        'compared': 0,
        'agreed': 0,
        'drifted': 0,
        'null_by_design': 0,
        'null_by_design_violations': 0,
    }

    # 1. Verify the affine/log units stay base_form=None.
    for name in _NULL_BASE_FORM_NAMES:
        unit = getattr(ucon_units, name, None)
        if unit is None:
            continue
        summary['null_by_design'] += 1
        if unit.base_form is not None:
            summary['null_by_design_violations'] += 1
            drifts.append(
                (name, f'expected base_form=None, found {unit.base_form!r}')
            )

    # 2. Verify each BFS-expected unit matches what units.py declares.
    #    Affine and logarithmic units are intentionally excluded from
    #    base_form (v1.3.0 policy) because the BFS slope ignores the affine
    #    offset; the slope-only number it would produce is misleading.
    for unit, expected_bf in expected_map.items():
        if unit.name in _NULL_BASE_FORM_NAMES:
            continue  # handled in step 1 above
        summary['compared'] += 1
        msg = _diff(unit.base_form, expected_bf)
        if msg is None:
            summary['agreed'] += 1
        else:
            summary['drifted'] += 1
            drifts.append((unit.name or repr(unit), msg))

    return drifts, summary


# ----------------------------------------------------------------------
# CLI entrypoint.
# ----------------------------------------------------------------------

def _format_baseform_for_emit(bf: BaseForm) -> dict[str, Any]:
    return {
        'prefactor': bf.prefactor,
        'factors': [[u.name, exp] for u, exp in bf.factors],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description='Detect drift between hand-written base_form literals '
                    'in ucon/units.py and the v1.2.x BFS oracle.',
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        '--check', action='store_true',
        help='Exit non-zero if any drift is detected (CI mode).',
    )
    mode.add_argument(
        '--report', action='store_true',
        help='Print a human-readable drift report.',
    )
    mode.add_argument(
        '--emit', action='store_true',
        help='Dump the expected base_form values as JSON.',
    )
    args = parser.parse_args(argv)

    drifts, summary = _scan()

    if args.emit:
        graph = get_default_graph()  # ensure construction
        expected = _compute_expected_base_forms(graph)
        payload = {
            (u.name or repr(u)): _format_baseform_for_emit(bf)
            for u, bf in expected.items()
        }
        json.dump(payload, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write('\n')
        return 0

    if args.report or args.check:
        print(
            f'compared={summary["compared"]} '
            f'agreed={summary["agreed"]} '
            f'drifted={summary["drifted"]} '
            f'null-by-design={summary["null_by_design"]}'
        )
        if drifts:
            print('\nDRIFT:')
            for name, msg in drifts:
                print(f'  {name}: {msg}')

    if args.check:
        return 1 if drifts else 0

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
