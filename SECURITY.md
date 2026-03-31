# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | Yes       |
| < 1.0   | No        |

## Reporting a Vulnerability

If you discover a security vulnerability in ucon, please report it
responsibly via email:

**info@radiativity.co**

Include:

- A description of the vulnerability
- Steps to reproduce
- Affected version(s)
- Any suggested fix, if available

You should receive an acknowledgment within 72 hours. Security patches
will be released as soon as a fix is verified, typically within 14 days
of confirmation.

Please do **not** open a public GitHub issue for security vulnerabilities.

## Scope

ucon is a pure-Python library for unit conversion and dimensional analysis.
It does not handle network I/O, authentication, or file system writes in
its core operation. The primary attack surface is:

- **Parsing untrusted unit expressions** — The `parse()` function and
  `get_unit_by_name()` accept string input. These use a recursive-descent
  parser with bounded recursion; they do not call `eval()` or `exec()`.
- **Loading unit packages from TOML** — `load_package()` reads TOML files
  using the standard library `tomllib` (Python 3.11+) or the `tomli`
  backport. It does not execute arbitrary code from package files.
- **Optional dependencies** — NumPy, Pandas, Polars, and Pydantic are
  optional. Vulnerabilities in those libraries are outside ucon's scope
  but users should keep them updated.

## Dependency Policy

ucon has two runtime dependencies, both used only on older Python versions:

| Dependency          | Purpose                              | Python versions |
|---------------------|--------------------------------------|-----------------|
| `typing_extensions` | Backported typing constructs         | < 3.9           |
| `tomli`             | TOML parsing (stdlib in 3.11+)       | < 3.11          |

On Python 3.11+, ucon has **zero** runtime dependencies.

Optional integration dependencies (NumPy, Pandas, Polars, Pydantic) are
the user's responsibility to keep updated.

## Design Considerations

- No use of `eval()`, `exec()`, `pickle`, or `subprocess` anywhere in
  the library.
- All conversion logic is data-driven through registered `Map` objects
  (pure arithmetic functions).
- The `ConversionGraph` performs BFS path-finding with bounded search
  (partitioned by dimension), preventing unbounded computation on
  adversarial inputs.
