# ucon.basis.ops

Explicit cross-basis arithmetic for `Vector`. Pure-function helpers (`unify`, `multiply_via`, `divide_via`) that resolve a common basis through a `BasisGraph` before composing two vectors. Replaces the implicit cross-basis fallback that lived inside `Vector.__mul__` / `__truediv__` in v1.7.

::: ucon.basis.ops
    options:
      show_source: false
      members_order: source
      show_root_heading: false
      heading_level: 2
