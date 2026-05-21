# ucon.formulas

Named relationships between input kinds and an output kind. A
`FormulaRegistry` indexes `KindFormula` instances by name and by input-kind
tuple, with commutative two-input formulas mirrored automatically.

New in v1.9.0 as an opt-in preview surface — formulas are not yet wired to
`Number` arithmetic. See [API › Formulas](../api.md#formulas) for usage and
the [Kind-of-Quantity Problem](../../architecture/kind-of-quantity.md) for
the conceptual framing.

::: ucon.formulas
    options:
      show_source: false
      members_order: source
      show_root_heading: false
      heading_level: 2
