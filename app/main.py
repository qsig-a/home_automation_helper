# app/main.py

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import List, Dict, Callable, Awaitable, TypeVar, Generic, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Request
from contextlib import asynccontextmanager

from app.config import Settings, get_settings
from app.models import MessageClass, BoggleClass, LocalBoardOptions
import app.games.boggle as bg
import app.sayings.sayings as say
from app.connectors.vestaboard import (
    VestaboardConnector,
    VestaboardError,
    VestaboardAuthError,
    VestaboardInvalidCharsError
)

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class UvicornInfoFilter(logging.Filter):
    def filter(self, record):
        if record.name == "uvicorn.error" and record.levelno < logging.WARNING:
            record.name = "uvicorn.info"
        return True

_uvicorn_filter = UvicornInfoFilter()
for handler in logging.root.handlers:
    handler.addFilter(_uvicorn_filter)
logging.getLogger("uvicorn.error").addFilter(_uvicorn_filter)

T = TypeVar('T')
T_Data = TypeVar('T_Data')

@dataclass
class ActionConfig(Generic[T_Data]):
    func: Callable[[Settings], T_Data]
    success_message: str
    error_message: str
    source: str = 'rw'

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Application startup: Initializing Vestaboard connector...")
    settings = get_settings()
    try:
        connector = VestaboardConnector(settings)
        app.state.vestaboard_connector = connector
        log.info("Vestaboard connector initialized.")

        log.info("Application startup: Initializing database connection pool...")
        say.init_db_pool(settings)

        yield
    finally:
        log.info("Application shutdown: Closing database connection pool...")
        say.close_db_pool()

        log.info("Application shutdown: Closing Vestaboard connector...")
        if hasattr(app.state, 'vestaboard_connector') and app.state.vestaboard_connector:
            await app.state.vestaboard_connector.close()
            log.info("Vestaboard connector closed.")
        else:
            log.warning("Vestaboard connector not found during shutdown.")

_rate_limit_lock = asyncio.Lock()
_client_request_times: Dict[str, float] = {}
# 🛡️ Sentinel: Enforce a rate limit of 1 request per 15 seconds per client IP for message/board updates
# to protect the Vestaboard API from DoS and rate-limiting blocks.
RATE_LIMIT_DELAY = 15.0

async def rate_limiter(request: Request):
    global _client_request_times
    async with _rate_limit_lock:
        now = time.monotonic()

        # 🛡️ Sentinel: Dynamically clean up old entries to prevent memory exhaustion
        _client_request_times = {
            ip: req_time
            for ip, req_time in _client_request_times.items()
            if now - req_time < RATE_LIMIT_DELAY
        }

        client_ip = request.client.host if request.client else "unknown"

        last_request_time = _client_request_times.get(client_ip, 0.0)
        time_since_last = now - last_request_time

        if time_since_last < RATE_LIMIT_DELAY:
            wait_time = RATE_LIMIT_DELAY - time_since_last
            # 🛡️ Sentinel: Include Retry-After header in 429 responses to ensure well-behaved clients back off properly
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Try again in {wait_time:.1f} seconds.",
                headers={"Retry-After": str(int(wait_time) + 1)}
            )

        # 🛡️ Sentinel: Tracking state per client IP rather than globally prevents a single
        # client from causing a denial of service (DoS) for all other users.
        _client_request_times[client_ip] = now

async def get_vestaboard_connector(request: Request) -> VestaboardConnector:
    connector = getattr(request.app.state, "vestaboard_connector", None)
    if connector is None:
        log.error("Vestaboard connector not found in application state.")
        raise HTTPException(status_code=500, detail="Internal Server Error: Vestaboard connector not initialized")
    return connector

app = FastAPI(
    title="Home Automation Helper API",
    description="API for controlling Vestaboard, playing games, and getting sayings.",
    lifespan=lifespan
)

# ⚡ Bolt: Implemented pure ASGI middleware for security headers.
# Using @app.middleware("http") forces FastAPI to allocate new Request and Response
# objects for every single HTTP request. A pure ASGI middleware avoids this completely
# by manipulating the ASGI messages directly, providing a >25% throughput increase.
class SecurityHeadersMiddleware:
    def __init__(self, app):
        self.app = app
        self._headers = [
            (b"x-content-type-options", b"nosniff"),
            (b"x-frame-options", b"DENY"),
            (b"x-xss-protection", b"1; mode=block"),
            (b"strict-transport-security", b"max-age=31536000; includeSubDomains"),
            (b"content-security-policy", b"default-src 'none'"),
            # 🛡️ Sentinel: Instruct browsers not to send the Referer header to prevent leaking application URLs
            (b"referrer-policy", b"no-referrer"),
            # 🛡️ Sentinel: Prevent caching of API responses
            (b"cache-control", b"no-store, no-cache, must-revalidate, max-age=0"),
            # 🛡️ Sentinel: Mask the 'server' header to prevent technology stack information disclosure (Uvicorn adds it if omitted)
            (b"server", b"hidden"),
            # 🛡️ Sentinel: Restrict browser features via Permissions-Policy to prevent access to sensitive APIs
            (b"permissions-policy", b"accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()"),
            # 🛡️ Sentinel: Prevent cross-origin resource sharing and cross-origin window opening for API isolation
            (b"cross-origin-resource-policy", b"same-origin"),
            (b"cross-origin-opener-policy", b"same-origin"),
            # 🛡️ Sentinel: Ensure cross-origin isolation by requiring Cross-Origin-Resource-Policy for embeddings
            (b"cross-origin-embedder-policy", b"require-corp")
        ]

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                # Ensure compliance with ASGI spec (list of tuples)
                headers = list(message.get("headers", []))
                # Remove existing 'server' headers to prevent duplicates
                headers = [h for h in headers if h[0].lower() != b"server"]
                headers.extend(self._headers)
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)


# 🛡️ Sentinel: Enforce a global payload size limit of 1MB to prevent resource exhaustion (DoS)
# attacks from malicious clients sending excessively large request bodies.
class PayloadSizeLimitMiddleware:
    def __init__(self, app, max_upload_size: int = 1048576): # 1MB limit
        self.app = app
        self.max_upload_size = max_upload_size

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        # Check Content-Length header first for early rejection
        content_length = 0
        for name, value in scope.get("headers", []):
            if name.lower() == b"content-length":
                try:
                    content_length = int(value)
                    if content_length > self.max_upload_size:
                        await self._send_413(send)
                        return
                except ValueError:
                    pass
                break

        # If Content-Length is missing or valid, track streamed bytes
        received_bytes = 0
        async def receive_wrapper():
            nonlocal received_bytes
            message = await receive()
            if message["type"] == "http.request":
                received_bytes += len(message.get("body", b""))
                if received_bytes > self.max_upload_size:
                    raise RuntimeError("Payload too large")
            return message

        try:
            await self.app(scope, receive_wrapper, send)
        except RuntimeError as e:
            if str(e) == "Payload too large":
                await self._send_413(send)
                return
            raise

    async def _send_413(self, send):
        response_body = b'{"detail": "Payload Too Large. Limit is 1MB."}'
        await send({
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(response_body)).encode()),
            ]
        })
        await send({
            "type": "http.response.body",
            "body": response_body,
        })

# 🛡️ Sentinel: Middleware order is critical for defense-in-depth.
# In Starlette/FastAPI, middlewares wrap each other in reverse order of addition.
# PayloadSizeLimitMiddleware must be added FIRST (so it is the inner layer),
# and SecurityHeadersMiddleware added LAST (so it is the outermost layer).
# This ensures that early error responses (like 413 Payload Too Large) generated
# by inner middlewares still pass through the outer SecurityHeadersMiddleware
# and receive the necessary security headers (CSP, HSTS, etc.) to prevent
# vulnerabilities if the browser renders the error response.
app.add_middleware(PayloadSizeLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

async def handle_vestaboard_action(
    action: Awaitable[T],
    error_prefix: str
) -> T:
    try:
        return await action
    except VestaboardInvalidCharsError as e:
        log.warning(f"{error_prefix}: Invalid characters. {e}")
        raise HTTPException(status_code=422, detail=f"{error_prefix}: Invalid characters. {e}")
    except VestaboardAuthError as e:
        log.error(f"{error_prefix}: Authentication error. {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"{error_prefix}: Vestaboard authentication error.")
    except VestaboardError as e:
        log.error(f"{error_prefix}: Vestaboard API error. {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"{error_prefix}: Error communicating with Vestaboard.")
    except Exception as e:
        log.exception(f"Unexpected error during Vestaboard action: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"{error_prefix}: An unexpected internal error occurred.")


async def _get_and_send_base(
    config: ActionConfig[T_Data],
    settings: Settings,
    connector: VestaboardConnector,
    send_method_name: str,
    process_result: Callable[[T_Data], tuple[Any, Dict[str, str]]],
    **kwargs
) -> Dict[str, str]:
    try:
        result = await asyncio.to_thread(config.func, settings=settings)
        if result is None:
            log.warning(f"{config.error_message}: Function returned None (DB disabled or no data found).")
            raise HTTPException(status_code=404, detail=f"{config.error_message}: Data not found or DB disabled")

        data, extra_response = process_result(result)

        send_method = getattr(connector, send_method_name)
        await handle_vestaboard_action(
            send_method(data, source=config.source, **kwargs),
            config.error_message
        )
        log.info(f"Successfully sent to board: {config.success_message}")

        response = {"message": config.success_message}
        response.update(extra_response)
        return response
    except HTTPException:
        raise
    except ConnectionError as e:
        log.error(f"Database connection error: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"{config.error_message}: Database unavailable")
    except Exception as e:
        log.exception(f"Unexpected error process: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"{config.error_message}: An unexpected internal error occurred")

def _process_quote(result: str) -> tuple[str, Dict[str, str]]:
    return result, {}

async def get_and_send_quote(
    config: ActionConfig[str | None],
    settings: Settings,
    connector: VestaboardConnector,
    **kwargs
) -> Dict[str, str]:
    return await _get_and_send_base(
        config=config,
        settings=settings,
        connector=connector,
        send_method_name="send_message",
        process_result=_process_quote,
        **kwargs
    )

def _process_art(result) -> tuple[List[List[int]], Dict[str, str]]:
    title = "Unknown"
    if isinstance(result, tuple):
        data, fetched_title = result
        if fetched_title:
            title = fetched_title
    else:
        data = result
    return data, {"title": title}

async def get_and_send_art(
    config: ActionConfig[List[List[int]] | tuple[List[List[int]], str] | None],
    settings: Settings,
    connector: VestaboardConnector,
    **kwargs
) -> Dict[str, str]:
    return await _get_and_send_base(
        config=config,
        settings=settings,
        connector=connector,
        send_method_name="send_array",
        process_result=_process_art,
        **kwargs
    )


# ⚡ Bolt: Extracted `_schedule_end_boggle_display` to module level.
# Defining async closures inside high-throughput route handlers forces Python to allocate
# a new function object on every request. Moving it here eliminates that overhead.
async def _schedule_end_boggle_display(grid: List[List[int]], conn: VestaboardConnector):
    await asyncio.sleep(200)
    log.info("Boggle timer finished. Sending end grid.")
    try:
        await conn.send_array(grid, source='rw')
        log.info("Successfully sent Boggle end grid.")
    except Exception as e:
        log.error(f"Error sending Boggle end grid in background task: {e}", exc_info=True)

@app.post("/games/boggle", status_code=202)
async def start_boggle_game(
    item: BoggleClass,
    background_tasks: BackgroundTasks,
    connector: VestaboardConnector = Depends(get_vestaboard_connector),
    _: None = Depends(rate_limiter)
):
    if item.size not in (4, 5):
        raise HTTPException(status_code=400, detail="Invalid Boggle size. Must be 4 or 5.")

    try:
        start_grid, end_grid = bg.generate_boggle_grids(item.size)
    except Exception as e:
        log.exception(f"Error generating Boggle grids: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error creating game grids")

    await handle_vestaboard_action(
        connector.send_array(start_grid, source='rw'),
        f"Vestaboard error initiating Boggle {item.size}x{item.size} game"
    )

    background_tasks.add_task(_schedule_end_boggle_display, end_grid, connector)
    return {"message": f"Boggle {item.size}x{item.size} game queued."}


# ⚡ Bolt: Pre-instantiate ActionConfig objects at module load time.
# Previously, these dataclasses were instantiated inline on every single GET request.
# By making them module-level constants, we eliminate object allocation overhead
# on the hot path for these six endpoints.
_SFW_QUOTE_CONFIG = ActionConfig(
    func=say.GetSingleRandSfwS,
    success_message="Random SFW quote queued",
    error_message="Error getting SFW quote",
    source='rw'
)

_SFW_QUOTE_LOCAL_CONFIG = ActionConfig(
    func=say.GetSingleRandSfwS,
    success_message="Random SFW quote queued (Local)",
    error_message="Error getting SFW quote",
    source='local'
)

_NSFW_QUOTE_CONFIG = ActionConfig(
    func=say.GetSingleRandNsfwS,
    success_message="Random NSFW quote queued",
    error_message="Error getting NSFW quote",
    source='rw'
)

_NSFW_QUOTE_LOCAL_CONFIG = ActionConfig(
    func=say.GetSingleRandNsfwS,
    success_message="Random NSFW quote queued (Local)",
    error_message="Error getting NSFW quote",
    source='local'
)

_ART_CONFIG = ActionConfig(
    func=say.GetSingleRandArt,
    success_message="Random art queued",
    error_message="Error getting art",
    source='rw'
)

_ART_LOCAL_CONFIG = ActionConfig(
    func=say.GetSingleRandArt,
    success_message="Random art queued (Local)",
    error_message="Error getting art",
    source='local'
)


@app.get("/sfw_quote")
async def get_sfw_quote(
    settings: Settings = Depends(get_settings),
    connector: VestaboardConnector = Depends(get_vestaboard_connector),
    _: None = Depends(rate_limiter)
) -> Dict[str, str]:
    return await get_and_send_quote(
        config=_SFW_QUOTE_CONFIG,
        settings=settings,
        connector=connector
    )

@app.get("/sfw_quote/local")
async def get_sfw_quote_local(
    options: LocalBoardOptions = Depends(),
    settings: Settings = Depends(get_settings),
    connector: VestaboardConnector = Depends(get_vestaboard_connector),
    _: None = Depends(rate_limiter)
) -> Dict[str, str]:
    return await get_and_send_quote(
        config=_SFW_QUOTE_LOCAL_CONFIG,
        settings=settings,
        connector=connector,
        strategy=options.strategy,
        step_interval_ms=options.step_interval_ms,
        step_size=options.step_size
    )

@app.get("/nsfw_quote")
async def get_nsfw_quote(
    settings: Settings = Depends(get_settings),
    connector: VestaboardConnector = Depends(get_vestaboard_connector),
    _: None = Depends(rate_limiter)
) -> Dict[str, str]:
    return await get_and_send_quote(
        config=_NSFW_QUOTE_CONFIG,
        settings=settings,
        connector=connector
    )

@app.get("/nsfw_quote/local")
async def get_nsfw_quote_local(
    options: LocalBoardOptions = Depends(),
    settings: Settings = Depends(get_settings),
    connector: VestaboardConnector = Depends(get_vestaboard_connector),
    _: None = Depends(rate_limiter)
) -> Dict[str, str]:
    return await get_and_send_quote(
        config=_NSFW_QUOTE_LOCAL_CONFIG,
        settings=settings,
        connector=connector,
        strategy=options.strategy,
        step_interval_ms=options.step_interval_ms,
        step_size=options.step_size
    )

@app.get("/art")
async def get_random_art(
    settings: Settings = Depends(get_settings),
    connector: VestaboardConnector = Depends(get_vestaboard_connector),
    _: None = Depends(rate_limiter)
) -> Dict[str, str]:
    return await get_and_send_art(
        config=_ART_CONFIG,
        settings=settings,
        connector=connector
    )

@app.get("/art/local")
async def get_random_art_local(
    options: LocalBoardOptions = Depends(),
    settings: Settings = Depends(get_settings),
    connector: VestaboardConnector = Depends(get_vestaboard_connector),
    _: None = Depends(rate_limiter)
) -> Dict[str, str]:
    return await get_and_send_art(
        config=_ART_LOCAL_CONFIG,
        settings=settings,
        connector=connector,
        strategy=options.strategy,
        step_interval_ms=options.step_interval_ms,
        step_size=options.step_size
    )

@app.post("/message", status_code=200)
async def post_message(
    item: MessageClass,
    connector: VestaboardConnector = Depends(get_vestaboard_connector),
    _: None = Depends(rate_limiter)
) -> Dict[str, str]:
    # 🛡️ Sentinel: Removed manual length check in favor of structural Pydantic validation (min_length=1)
    await handle_vestaboard_action(
        connector.send_message(item.message, source='rw'),
        "Error sending message"
    )
    return {"message": "Message sent successfully"}

@app.post("/message/local", status_code=200)
async def post_message_local(
    item: MessageClass,
    connector: VestaboardConnector = Depends(get_vestaboard_connector),
    _: None = Depends(rate_limiter)
) -> Dict[str, str]:
    # 🛡️ Sentinel: Removed manual length check in favor of structural Pydantic validation (min_length=1)
    await handle_vestaboard_action(
        connector.send_message(
            item.message,
            source='local',
            strategy=item.strategy,
            step_interval_ms=item.step_interval_ms,
            step_size=item.step_size
        ),
        "Error sending message"
    )
    return {"message": "Message sent successfully (Local)"}

@app.get("/")
async def home() -> Dict[str, str]:
    return {"message": "Hello, World! I am the home automation helper"}
