# Support & Backward-Compatibility Policy

## Semantic Versioning

ucon follows [Semantic Versioning 2.0.0](https://semver.org/) starting
with v1.0.0:

- **MAJOR** (X.0.0) — breaking changes to the public API
- **MINOR** (1.X.0) — new features, new units, new dimensions (backward-compatible)
- **PATCH** (1.0.X) — bug fixes, documentation, performance improvements

## Public API Surface

The public API is everything listed in `ucon.__all__` plus:

- All symbols exported by `ucon.units` and `ucon.constants`
- Submodule imports documented in the API reference
  (`ucon.maps`, `ucon.graph`, `ucon.basis`, `ucon.contexts`,
  `ucon.resolver`, `ucon.parsing`, `ucon.packages`)
- Integration modules (`ucon.integrations.numpy`, `.pandas`, `.polars`,
  `.pydantic`)

Symbols prefixed with `_` are internal and may change without notice.

## Long-Term Support

**v1.0.x is a Long-Term Support (LTS) release line.**

- Security and critical bug fixes for a minimum of **2 years** from
  the v1.0.0 release date.
- No breaking changes within the 1.x series.
- LTS patch releases will be tagged as needed (1.0.1, 1.0.2, ...).

Future major versions (2.0, 3.0) will overlap with the prior LTS line
by at least 6 months to allow migration time.

## Deprecation Policy

Before removing or renaming a public symbol:

1. The symbol is marked deprecated with a `DeprecationWarning` for at
   least **one minor release cycle** (e.g., deprecated in 1.2, removable
   in 2.0).
2. The deprecation warning includes a message naming the replacement.
3. Deprecated symbols continue to function identically until removal.

Exceptions: symbols that pose a security risk may be removed in a patch
release without a deprecation cycle.

## Python Version Support

ucon tracks the [Python release lifecycle](https://devguide.python.org/versions/).
At any given time, ucon supports all Python versions that have not
reached end-of-life.

| Python | Status          |
|--------|-----------------|
| 3.9+   | Fully supported |
| 3.7–3.8| Best-effort     |

When a Python version reaches end-of-life, support for it may be dropped
in the next minor release of ucon. Dropping a Python version is not
considered a breaking change.

## Reporting Issues

- **Bugs and feature requests**: [GitHub Issues](https://github.com/withtwoemms/ucon/issues)
- **Security vulnerabilities**: See [SECURITY.md](SECURITY.md)
