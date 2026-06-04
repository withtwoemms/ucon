# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

"""
Deprecation-warning tests for ucon.

The v1.x deprecation tests (``get_unit_by_name``, ``using_graph``,
``set_default_graph``, ``reset_default_graph``, ``set_default_basis_graph``,
``reset_default_basis_graph``, ``UnitSystem.conversions``,
``UnitSystem.from_globals()``, ``UnitSystem(conversions=...)``,
``units.have()``, and the legacy ``_DIM_*_CACHE`` PEP-562 shims)
were retired when those symbols were removed in v2.0.

New deprecation cycles should add parametrized tests here following
the same pattern: verify that the symbol emits ``DeprecationWarning``
with a message citing the migration path.
"""
