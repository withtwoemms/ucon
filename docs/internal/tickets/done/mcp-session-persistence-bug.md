# MCP Session State Does Not Persist Across Tool Calls

**Type:** Bug
**Severity:** High
**Component:** ucon.mcp.server

---

## Problem

Custom units defined via `define_unit()` are not resolvable when `define_conversion()` is called in a subsequent MCP request.

### Steps to Reproduce

1. Call `define_unit(name="slug", dimension="mass", aliases=["slug"])`
2. Call `define_conversion(src="slug", dst="kg", factor=14.5939)`
3. Observe: `define_conversion` fails with "unknown_unit" error for "slug"

### Expected Behavior

Units registered in step 1 should be resolvable in step 2 within the same MCP session.

### Actual Behavior

Each MCP tool call runs in a separate asyncio task, and `ContextVar` values do not persist across tasks.

---

## Root Cause Analysis

**File:** `ucon/mcp/server.py` (lines 42-53)

```python
_session_graph: ContextVar[ConversionGraph | None] = ContextVar(
    '_session_graph', default=None
)
```

`ContextVar` provides **task-local isolation** in asyncio:
- Request 1 (`define_unit`): Sets `_session_graph` in Task A
- Request 2 (`define_conversion`): Runs in Task B with **fresh** ContextVar context
- Task B's `_session_graph.get()` returns `None`, creating a new graph without the custom unit

### Why Tests Pass

Unit tests call functions synchronously in the same Python task, so ContextVars persist. The bug only manifests in actual MCP server usage where FastMCP spawns separate async tasks per request.

---

## Acceptance Criteria

- [ ] GIVEN a unit registered via `define_unit()` in one MCP request
      WHEN `define_conversion()` is called in a subsequent request (same session)
      THEN the unit must be resolvable

- [ ] GIVEN a conversion defined via `define_conversion()` in one request
      WHEN `convert()` is called in a subsequent request
      THEN the conversion must succeed

- [ ] GIVEN session state from prior requests
      WHEN `reset_session()` is called
      THEN all state must be cleared for future requests

- [ ] GIVEN the fix is applied
      WHEN existing unit tests run
      THEN all tests must pass

- [ ] GIVEN the new architecture
      WHEN tests inject mock SessionState
      THEN the system must use the injected state (injectability)

---

## Proposed Solution

Replace `ContextVar` with FastMCP's **lifespan context** and an injectable `SessionState` protocol:

1. Create `SessionState` protocol in `ucon/mcp/session.py`
2. Implement `DefaultSessionState` class
3. Use FastMCP `lifespan` parameter to create session state at server startup
4. Inject via `Context` parameter into tools
5. All tools access shared `SessionState` via `ctx.lifespan_context["session"]`

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FastMCP Server                        │
│  ┌─────────────────────────────────────────────────┐    │
│  │              Lifespan Context                    │    │
│  │         SessionState (shared instance)           │    │
│  └─────────────────────────────────────────────────┘    │
│                          │                               │
│         ┌────────────────┼────────────────┐             │
│         ▼                ▼                ▼             │
│   define_unit()    define_conversion()  convert()       │
│   (Task A)         (Task B)             (Task C)        │
│         All access SAME SessionState instance           │
└─────────────────────────────────────────────────────────┘
```

---

## Files Affected

| File | Change |
|------|--------|
| `ucon/mcp/session.py` | **New** - SessionState protocol, DefaultSessionState |
| `ucon/mcp/server.py` | Replace ContextVar with lifespan context injection |
| `ucon/mcp/__init__.py` | Export SessionState, DefaultSessionState |
| `tests/ucon/mcp/test_server.py` | Update tests for Context injection |

---

## Implementation Notes

### SessionState Protocol

```python
@runtime_checkable
class SessionState(Protocol):
    def get_graph(self) -> ConversionGraph: ...
    def get_constants(self) -> dict[str, Constant]: ...
    def reset(self) -> None: ...
```

### Lifespan Setup

```python
@asynccontextmanager
async def lifespan(app: FastMCP):
    yield {"session": DefaultSessionState()}

mcp = FastMCP("ucon", lifespan=lifespan)
```

### Tool Signature Update

```python
@mcp.tool()
def define_unit(
    name: str,
    dimension: str,
    aliases: list[str] | None = None,
    ctx: Context = None,  # Auto-injected by FastMCP
) -> UnitDefinitionResult | ConversionError:
    session = ctx.lifespan_context["session"]
    graph = session.get_graph()
    # ...
```

---

## Status

**Open** - Ready for implementation

---

## Closure Note (2026-07-12)

**Closed: fixed downstream.** The MCP server no longer lives in this repo
(`ucon/mcp/` removed; tests archived at `tests/ucon/.archive/mcp/`). The bug
was fixed in ucon-tools (>= v0.7.0) by implementing this ticket's proposed
solution: `SessionState` protocol + `DefaultSessionState`
(`ucon/tools/mcp/session.py`) injected via FastMCP lifespan context
(`ucon/tools/mcp/server.py`). Residual follow-ups (protocol-level
integration test; multi-client isolation decision) are tracked in ucon-tools
at `docs/internal/tickets/mcp-session-persistence-followups.md`.
