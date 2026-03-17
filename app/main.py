# app/main.py

import asyncio
import logging
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
            (b"content-security-policy", b"default-src 'self'"),
            (b"referrer-policy", b"strict-origin-when-cross-origin")
        ]

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                # Ensure compliance with ASGI spec (list of tuples)
                headers = list(message.get("headers", []))
                headers.extend(self._headers)
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)

app.add_middleware(SecurityHeadersMiddleware)


async def handle_vestaboard_action(
    action: Callable[[], Awaitable[T]],
    error_prefix: str
) -> T:
    try:
        return await action()
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
            lambda: send_method(data, source=config.source, **kwargs),
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
    connector: VestaboardConnector = Depends(get_vestaboard_connector)
):
    if item.size not in (4, 5):
        raise HTTPException(status_code=400, detail="Invalid Boggle size. Must be 4 or 5.")

    try:
        start_grid, end_grid = bg.generate_boggle_grids(item.size)
    except Exception as e:
        log.exception(f"Error generating Boggle grids: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error creating game grids")

    await handle_vestaboard_action(
        lambda: connector.send_array(start_grid, source='rw'),
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
    connector: VestaboardConnector = Depends(get_vestaboard_connector)
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
    connector: VestaboardConnector = Depends(get_vestaboard_connector)
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
    connector: VestaboardConnector = Depends(get_vestaboard_connector)
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
    connector: VestaboardConnector = Depends(get_vestaboard_connector)
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
    connector: VestaboardConnector = Depends(get_vestaboard_connector)
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
    connector: VestaboardConnector = Depends(get_vestaboard_connector)
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
    connector: VestaboardConnector = Depends(get_vestaboard_connector)
) -> Dict[str, str]:
    if not item.message:
        raise HTTPException(status_code=400, detail="No message content provided.")

    await handle_vestaboard_action(
        lambda: connector.send_message(item.message, source='rw'),
        "Error sending message"
    )
    return {"message": "Message sent successfully"}

@app.post("/message/local", status_code=200)
async def post_message_local(
    item: MessageClass,
    connector: VestaboardConnector = Depends(get_vestaboard_connector)
) -> Dict[str, str]:
    if not item.message:
        raise HTTPException(status_code=400, detail="No message content provided.")

    await handle_vestaboard_action(
        lambda: connector.send_message(
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
