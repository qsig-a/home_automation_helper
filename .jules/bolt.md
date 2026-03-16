## 2024-05-24 - [Avoid over-optimizing regex]
**Learning:** Checking string characters with regex `re.match` is actually ~4x faster than using `set(text).issubset(_ALLOWED_SET)` in Python for moderate sized strings.
**Action:** Leave the `re.compile` checks alone in Python strings.

## 2024-05-24 - [Pre-calculating Structural Templates]
**Learning:** In dynamically constructed structural layouts like Vestaboard grids (6x22 arrays), dynamically merging components (headers, bodies, footers) and transforming boundaries on every request incurs significant O(R*C) allocation and iteration overhead.
**Action:** When the structural layout is static, pre-calculate the flat templates at module load time. Using pre-calculated absolute index maps alongside fast C-level shallow copies (`[row[:] for row in template]`) and updating both state grids simultaneously eliminates redundant iteration overhead.

## 2024-05-24 - [Fast JSON decoding for large array structures]
**Learning:** Decoding large array structures (like 6x22 Vestaboard grid representations) from the database using standard library `json.loads` is a measurable bottleneck (~0.3ms per decode). `pydantic_core.from_json`, which is already available as a dependency, provides a >4x speedup due to its Rust implementation.
**Action:** For performance-sensitive data fetching, especially large JSON payloads from DB rows, replace standard library `json.loads` with `pydantic_core.from_json`. Make sure to catch `ValueError` instead of `json.JSONDecodeError`.

## 2025-02-13 - Extract Inline Helper Functions
**Learning:** In high-throughput route handlers (e.g., FastAPI endpoints), defining pure helper functions inline (as closures) causes unnecessary function object allocation overhead on every request.
**Action:** Define pure helper functions at the module level rather than inline to avoid this overhead.

## 2025-02-14 - Pre-instantiate Static Route Configurations
**Learning:** Defining static configuration objects (like `ActionConfig` dataclasses) directly within FastAPI route handlers causes identical, stateless objects to be re-instantiated on every single API request, adding unnecessary allocation and garbage collection overhead to the hot path.
**Action:** For static configurations that don't change per request, pre-instantiate them as module-level constants and reference those constants inside the route handlers.

## 2025-02-15 - FastAPI BaseHTTPMiddleware Overhead
**Learning:** FastAPI's `@app.middleware("http")` (which utilizes `BaseHTTPMiddleware`) incurs significant processing overhead by creating new internal `Request` and `Response` objects (and the associated `anyio` stream overhead) for every single incoming request.
**Action:** For simple header modifications, implement a pure ASGI middleware class that operates directly on the raw scope dictionary. This bypasses the FastAPI Request/Response instantiation layer entirely, resulting in massive performance gains (e.g. reducing middleware processing time by ~84%).