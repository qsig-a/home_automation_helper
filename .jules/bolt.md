## 2024-05-24 - [Avoid over-optimizing regex]
**Learning:** Checking string characters with regex `re.match` is actually ~4x faster than using `set(text).issubset(_ALLOWED_SET)` in Python for moderate sized strings.
**Action:** Leave the `re.compile` checks alone in Python strings.

## 2024-05-24 - [Pre-calculating Structural Templates]
**Learning:** In dynamically constructed structural layouts like Vestaboard grids (6x22 arrays), dynamically merging components (headers, bodies, footers) and transforming boundaries on every request incurs significant O(R*C) allocation and iteration overhead.
**Action:** When the structural layout is static, pre-calculate the flat templates at module load time. Using pre-calculated absolute index maps alongside fast C-level shallow copies (`[row[:] for row in template]`) and updating both state grids simultaneously eliminates redundant iteration overhead.

## 2024-05-24 - [Optimizing Inner Loops by Localizing Builtins and Globals]
**Learning:** In highly tight, performance-sensitive loops in Python (like processing a string character by character), looking up builtins (e.g., `ord()`) and globals (e.g., a precomputed lookup array) inside the loop incurs significant overhead on each iteration.
**Action:** Pre-bind builtins and globals to local variables (e.g., `_ord = ord`, `char_array = _CHAR_CODE_ARRAY`) before the loop. Local variable lookups are considerably faster in CPython than global or builtin lookups.

## 2024-05-24 - [Fast JSON decoding for large array structures]
**Learning:** Decoding large array structures (like 6x22 Vestaboard grid representations) from the database using standard library `json.loads` is a measurable bottleneck (~0.3ms per decode). `pydantic_core.from_json`, which is already available as a dependency, provides a >4x speedup due to its Rust implementation.
**Action:** For performance-sensitive data fetching, especially large JSON payloads from DB rows, replace standard library `json.loads` with `pydantic_core.from_json`. Make sure to catch `ValueError` instead of `json.JSONDecodeError`.

## 2025-02-13 - Extract Inline Helper Functions
**Learning:** In high-throughput route handlers (e.g., FastAPI endpoints), defining pure helper functions inline (as closures) causes unnecessary function object allocation overhead on every request.
**Action:** Define pure helper functions at the module level rather than inline to avoid this overhead.

## 2025-02-14 - Pre-instantiate Static Route Configurations
**Learning:** Defining static configuration objects (like `ActionConfig` dataclasses) directly within FastAPI route handlers causes identical, stateless objects to be re-instantiated on every single API request, adding unnecessary allocation and garbage collection overhead to the hot path.
**Action:** For static configurations that don't change per request, pre-instantiate them as module-level constants and reference those constants inside the route handlers.

## 2025-02-14 - Pure ASGI Middleware for simple headers
**Learning:** Using FastAPI's `@app.middleware("http")` (or `BaseHTTPMiddleware`) forces the allocation of new Request and Response objects for every single HTTP request. For simple tasks like appending static security headers, rewriting this as a pure ASGI middleware that directly manipulates the ASGI `message` dictionary avoids these allocations completely, yielding a >25% throughput increase on the hot path.
**Action:** When writing middleware that only modifies response headers or performs simple structural changes without needing full Request/Response parsing, use pure ASGI middleware and adhere to the ASGI spec (e.g., converting the headers tuple list before appending byte-encoded tuples).
