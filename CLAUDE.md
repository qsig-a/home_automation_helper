# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A FastAPI service that drives a [Vestaboard](https://www.vestaboard.com/) split-flap display. It can push random quotes and pixel "art" (pulled from a MySQL database), run a timed Boggle game, and post arbitrary messages. Every board-writing endpoint comes in two variants:

- **RW / cloud** (`source='rw'`) — posts to the Vestaboard Read-Write cloud API (`https://rw.vestaboard.com`). Text is rendered into the grid server-side by Vestaboard.
- **Local** (`source='local'`) — posts to a device on the LAN (`http://<ip>:7000`). Only initialized when `VESTABOARD_LOCAL_API_IP` is set. Accepts character arrays only (text is converted to a 6×22 grid client-side) and supports transition options (`strategy`, `step_interval_ms`, `step_size`).

## Commands

Tooling is Poetry (`pyproject.toml`). Common tasks:

```bash
poetry install                                   # install deps (incl. dev/test)
poetry run uvicorn app.main:app --reload         # run locally (http://127.0.0.1:8000)
poetry run pytest                                # run all tests
poetry run pytest tests/test_main.py             # single file
poetry run pytest tests/test_main.py::test_name  # single test
poetry run pytest -v                             # verbose
```

CI (`.github/workflows/tests.yml`) runs `poetry run pytest` with `PYTHONPATH` set to the repo root, across Python 3.10/3.11/3.12.

Notes:
- **Run with uvicorn, not `fastapi run`.** The `fastapi[standard]` extra (which provides `fastapi-cli`) is intentionally *not* a dependency; only `uvicorn[standard]` is. The container `CMD` and the docs use `uvicorn app.main:app`.
- If `poetry` is unavailable in your environment, a working fallback is a venv + `pip install` of the deps in `pyproject.toml`, running pytest with the repo root on `PYTHONPATH`.
- Source files use **CRLF** line endings; don't bulk-reformat them to LF (it produces huge no-op diffs).

## Architecture

### Request → board flow (the core abstraction)

Quote and art endpoints share one generic pipeline in `app/main.py`:

- `ActionConfig` (dataclass) bundles a data-fetch `func`, `success_message`, `error_message`, and `source`. Each endpoint has a module-level `_*_CONFIG` constant.
- `_get_and_send_base(config, ..., send_method_name, process_result)` runs the pipeline: fetch data (`asyncio.to_thread`, since DB access is sync) → `process_result` shapes it (`_process_quote` / `_process_art`) → send via `getattr(connector, send_method_name)` (`send_message` for quotes, `send_array` for art).
- `get_and_send_quote` / `get_and_send_art` are thin wrappers selecting the send method and processor.

### Fingerprint re-roll (why endpoints don't 502 on duplicates)

The RW API returns **HTTP 409 (`FingerprintMatch`)** when the message equals what's already on the board. Handling spans three layers:

1. `vestaboard.py::_post_rw` translates a 409 into `VestaboardFingerprintError` (a `VestaboardError` subclass), everything else into generic `VestaboardError`.
2. `main.py::handle_vestaboard_action` **re-raises** `VestaboardFingerprintError` instead of mapping it to 502, so callers can decide.
3. `_get_and_send_base` catches it and re-draws a *different* random item, up to `MAX_FINGERPRINT_RETRIES` (3). If all attempts still match, it returns a graceful 200 (`"... (already displayed on board; no change made)"`), not an error.

### Error mapping

`handle_vestaboard_action(awaitable, error_prefix)` centralizes connector-exception → HTTP-status mapping: `422` invalid chars, `503` auth, `502` other Vestaboard errors, `500` unexpected; `VestaboardFingerprintError` is re-raised. **It awaits a coroutine passed in**, so retry loops must build a fresh `connector.send_...()` coroutine on each attempt.

### Connector — `app/connectors/vestaboard.py`

`VestaboardConnector` owns two `httpx.AsyncClient`s (RW always; Local only if an IP is configured). `send_message` posts `{"text": ...}` to RW or converts to an array for Local; `send_array` posts raw 6×22 grids. `convert_text_to_array` maps characters via `CHAR_CODE_MAP` (with a precomputed `_CHAR_CODE_ARRAY` fast path). Exception hierarchy: `VestaboardError` → `VestaboardAuthError` / `VestaboardInvalidCharsError` / `VestaboardFingerprintError`.

### Data layer — `app/sayings/sayings.py`

MySQL access for random quotes/art, **security-hardened**:
- Queries are **not** built dynamically. Only the predefined entries in `_STATIC_QUERIES` are allowed, gated by an `ALLOWED_TABLES` allowlist; any other table/column request raises `ValueError`. **Adding a new DB-backed source requires adding both an `ALLOWED_TABLES` entry and a `_STATIC_QUERIES` entry.**
- Random selection uses an id-range trick (`FLOOR(RAND() * ...)` over `MIN(id)/MAX(id)`), not `ORDER BY RAND()`.
- Uses a MySQL connection **pool** (`init_db_pool` / `close_db_pool`, driven by the app lifespan), falling back to a direct connection if the pool isn't initialized.
- Gated by `SAYING_DB_ENABLE` (must be `"1"`); otherwise the `GetSingleRand*` functions return `None` → endpoints respond 404. Art is stored as a JSON list in `art.art_data`.

### Games — `app/games/boggle.py`

Generates a start and end 6×22 grid from Boggle dice sets. `POST /games/boggle` sends the start grid immediately (RW) and schedules a background task that sleeps 200s and then sends the end grid.

### Config — `app/config.py`

`Settings` (pydantic-settings) loads from `.env` / env vars. Secrets are `SecretStr` — call `.get_secret_value()` to read them. `get_settings()` is `lru_cache`d and injected as a FastAPI dependency.

### Cross-cutting hardening — `app/main.py`, `app/middleware/security.py`

- `rate_limiter` dependency: per-client-IP limit (1 request / 15s), returns `429` with a `Retry-After` header; applied to all board-mutating endpoints.
- `PayloadSizeLimitMiddleware`: rejects bodies over 1MB (`413`).
- `SecurityHeadersMiddleware`: strict security headers, masks the `Server` header.
- Middleware order is intentional (payload limit inner, security headers outer) — see the comments before `add_middleware` calls.
- Lifespan: startup initializes the Vestaboard connector and DB pool; shutdown closes both.

## Environment variables

`SAYING_DB_ENABLE` defaults to `"0"` (DB off — quote/art endpoints return 404 until set to `"1"`). Others: `SAYING_DB_USER`, `SAYING_DB_PASS`, `SAYING_DB_HOST`, `SAYING_DB_PORT`, `SAYING_DB_NAME`, `VESTABOARD_RW_API_KEY`, `VESTABOARD_LOCAL_API_KEY`, `VESTABOARD_LOCAL_API_IP`.

## Testing conventions

Tests fully mock external systems — see `tests/conftest.py` fixtures: `mock_settings` (DB disabled by default), `mock_vestaboard_connector` (async-mocked send methods), and `client` (a `TestClient` with `get_settings`/`get_vestaboard_connector` dependency-overridden). Endpoint tests typically mock `app.main.get_and_send_quote` / `get_and_send_art`; pipeline behavior (e.g. re-roll in `test_quote_reroll.py`) is tested by calling those functions with an `ActionConfig` and a mocked connector.
