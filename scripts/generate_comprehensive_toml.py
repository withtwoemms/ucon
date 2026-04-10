#!/usr/bin/env python3
"""
Generate examples/units/comprehensive.ucon.toml from the default graph.

Serializes the full default ConversionGraph to TOML via ``to_toml()``,
then collapses multi-line scalar arrays (vectors, matrix rows) onto
single lines for readability.

Usage:
    python scripts/generate_comprehensive_toml.py
"""
import re
from pathlib import Path

from ucon.graph import get_default_graph
from ucon.serialization import to_toml

OUTPUT = Path(__file__).resolve().parent.parent / "examples" / "units" / "comprehensive.ucon.toml"


def collapse_short_arrays(text: str) -> str:
    """Collapse multi-line TOML arrays of scalars onto single lines.

    Only collapses arrays whose elements are all scalars (int, float,
    string) — not arrays of inline tables like ``components``.
    """

    def _try_collapse(m: re.Match) -> str:
        body = m.group(1)
        # Skip arrays that contain inline tables ('{')
        if "{" in body:
            return m.group(0)
        items = [s.strip().rstrip(",") for s in body.strip().splitlines()]
        items = [s for s in items if s]
        return "[" + ", ".join(items) + "]"

    # Match arrays that span multiple lines: [ ... \n ... ]
    return re.sub(
        r"\[\n((?:[ \t]*[^\[\]{}\n]+,?\n)+)[ \t]*\]",
        _try_collapse,
        text,
    )


def main():
    graph = get_default_graph()
    to_toml(graph, OUTPUT)

    raw = OUTPUT.read_text()
    formatted = collapse_short_arrays(raw)
    OUTPUT.write_text(formatted)

    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
