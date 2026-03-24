
from mysql.connector import pooling, Error, PoolError, connect
import logging
from pydantic_core import from_json
from contextlib import contextmanager
# from typing import Union # Reverted for Python 3.10+
from app.config import Settings

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

_connection_pool = None
_db_configured_cache = None

ALLOWED_TABLES = {
    "sfw_quotes": {"id", "quote", "source"},
    "nsfw_quotes": {"id", "quote", "source"},
    "art": {"id", "art_data", "title"},
}

# 🛡️ Sentinel: Pre-defined static SQL queries to prevent SQL injection vulnerabilities
# that can arise from dynamic query construction (even with allowlists).
_STATIC_QUERIES: dict[tuple[str, tuple[str, ...]], str] = {
    ("sfw_quotes", ("quote",)): (
        "SELECT t1.quote FROM sfw_quotes AS t1 "
        "JOIN (SELECT id FROM sfw_quotes WHERE id >= "
        "(SELECT FLOOR(RAND() * (MAX(id) - MIN(id) + 1)) + MIN(id) FROM sfw_quotes) "
        "ORDER BY id LIMIT 1) AS t2 ON t1.id = t2.id"
    ),
    ("nsfw_quotes", ("quote",)): (
        "SELECT t1.quote FROM nsfw_quotes AS t1 "
        "JOIN (SELECT id FROM nsfw_quotes WHERE id >= "
        "(SELECT FLOOR(RAND() * (MAX(id) - MIN(id) + 1)) + MIN(id) FROM nsfw_quotes) "
        "ORDER BY id LIMIT 1) AS t2 ON t1.id = t2.id"
    ),
    ("art", ("art_data", "title")): (
        "SELECT t1.art_data, t1.title FROM art AS t1 "
        "JOIN (SELECT id FROM art WHERE id >= "
        "(SELECT FLOOR(RAND() * (MAX(id) - MIN(id) + 1)) + MIN(id) FROM art) "
        "ORDER BY id LIMIT 1) AS t2 ON t1.id = t2.id"
    ),
}

def _is_db_configured(settings: Settings) -> bool:
    """Checks if essential DB configuration is present and caches the result."""
    global _db_configured_cache
    if _db_configured_cache is None:
        _db_configured_cache = bool(
            settings.saying_db_user and
            settings.saying_db_pass and
            settings.saying_db_host and
            settings.saying_db_port and
            settings.saying_db_name
        )
    return _db_configured_cache


def _acquire_connection(settings: Settings):
    """Acquires a database connection, either from the pool or directly."""
    global _connection_pool
    if _connection_pool:
        cnx = _connection_pool.get_connection()
        log.debug("Obtained connection from pool.")
        return cnx

    # Fallback for testing or if pool initialization failed
    cnx = connect(
        user=settings.saying_db_user,
        password=settings.saying_db_pass.get_secret_value() if settings.saying_db_pass else None,
        host=settings.saying_db_host,
        port=int(settings.saying_db_port),
        database=settings.saying_db_name,
        connection_timeout=5
    )
    log.debug("Database connection successful (no pool).")
    return cnx


def init_db_pool(settings: Settings):
    """Initializes the MySQL connection pool."""
    global _connection_pool
    if settings.saying_db_enable != "1":
        log.info("Database disabled, not initializing connection pool.")
        return

    if not _is_db_configured(settings):
        log.error("Database configuration is incomplete, cannot initialize pool.")
        return

    try:
        _connection_pool = pooling.MySQLConnectionPool(
            pool_name="sayings_pool",
            pool_size=5,
            pool_reset_session=True,
            user=settings.saying_db_user,
            password=settings.saying_db_pass.get_secret_value() if settings.saying_db_pass else None,
            host=settings.saying_db_host,
            port=int(settings.saying_db_port),
            database=settings.saying_db_name,
            connection_timeout=5
        )
        log.info("Database connection pool initialized.")
    except Error as err:
        log.error(f"Error initializing connection pool: {err}")
    except ValueError as verr:
        log.error(f"Database configuration error for pool: {verr}")

def close_db_pool():
    """Closes the database connection pool."""
    global _connection_pool
    if _connection_pool is not None:
        # Note: MySQLConnectionPool does not have a close() method.
        # Connections returned to the pool are closed when the pool object is garbage collected.
        _connection_pool = None
        log.info("Database connection pool reference cleared.")

@contextmanager
def _db_connection(settings: Settings):
    """A context manager for a MySQL database connection that handles setup and teardown."""
    if not _is_db_configured(settings):
        log.error("Database configuration is incomplete.")
        raise ConnectionError("Database configuration is incomplete.")

    cnx = None

    try:
        cnx = _acquire_connection(settings)
        yield cnx
    except PoolError as err:
        log.error(f"Error getting connection from pool: {err}")
        raise ConnectionError(f"Database connection pool exhausted: {err}") from err
    except Error as err:
        log.error(f"Error connecting to database: {err}")
        raise ConnectionError(f"Database connection failed: {err}") from err
    except ValueError as verr:
        log.error(f"Database configuration error (e.g., non-integer port): {verr}")
        raise ConnectionError(f"Database configuration error: {verr}") from verr
    finally:
        if cnx and cnx.is_connected():
            try:
                cnx.close()
                log.debug("Database connection returned to pool or closed.")
            except Error as err:
                log.warning(f"Error closing connection/returning to pool: {err}")

def _fetch_column_from_table(table_name: str, column_name: str, settings: Settings) -> str | None:
    """Fetches a random value from a given table and column using a managed DB connection."""
    result = _fetch_random_row(table_name, (column_name,), settings)

    if result and result[0] is not None:
        # 🛡️ Sentinel: Use repr() to prevent log injection.
        log.debug(f"Value found in {repr(table_name)}.{repr(column_name)}.")
        return str(result[0])
    else:
        # 🛡️ Sentinel: Use repr() to prevent log injection.
        log.warning(f"No value found in table {repr(table_name)} or result was NULL.")
        return None

def _fetch_random_row(table_name: str, columns: tuple[str, ...], settings: Settings) -> tuple | None:
    """Fetches a random row for specific columns from a given table."""
    cache_key = (table_name, columns)
    query = _STATIC_QUERIES.get(cache_key)

    if not query:
        # 🛡️ Sentinel: Validate input and prevent SQL injection.
        # We use repr() when logging or raising exceptions with untrusted input to prevent log injection.
        if table_name not in ALLOWED_TABLES:
            log.warning(f"Invalid table access attempt: {repr(table_name)}")
            raise ValueError(f"Invalid table name: {repr(table_name)}")
        for column_name in columns:
            if column_name not in ALLOWED_TABLES[table_name]:
                log.warning(f"Invalid column access attempt: {repr(column_name)} for table {repr(table_name)}")
                raise ValueError(f"Invalid column name: {repr(column_name)}")

        # If it is in ALLOWED_TABLES but not in _STATIC_QUERIES, it's a valid schema access
        # but the query isn't pre-defined. We strictly forbid dynamic construction.
        log.error(f"No static query defined for table {repr(table_name)} with columns {repr(columns)}")
        raise ValueError("No static query defined for the requested data.")

    try:
        with _db_connection(settings) as cnx:
            with cnx.cursor() as cur:
                log.debug(f"Executing query: {query}")
                cur.execute(query)
                return cur.fetchone()
    except Error as err:
        # 🛡️ Sentinel: Use repr() to prevent log injection.
        log.error(f"Database query error in {repr(table_name)}: {err}")
        raise ConnectionError(f"Database query failed for {repr(table_name)}") from err

# --- Public Functions ---

def GetSingleRandSfwS(settings: Settings) -> str | None: # Reverted
    """
    Gets a random SFW quote using provided application settings.
    Returns the quote string or None if not found or on error.
    """
    if settings.saying_db_enable != "1":
         log.info("SFW quote requested but sayings DB is disabled in settings.")
         return None # Or raise an exception if preferred
    return _fetch_column_from_table("sfw_quotes", "quote", settings)

def GetSingleRandNsfwS(settings: Settings) -> str | None: # Reverted
    """
    Gets a random NSFW quote using provided application settings.
    Returns the quote string or None if not found or on error.
    """
    if settings.saying_db_enable != "1":
         log.info("NSFW quote requested but sayings DB is disabled in settings.")
         return None # Or raise an exception if preferred
    return _fetch_column_from_table("nsfw_quotes", "quote", settings)

def GetSingleRandArt(settings: Settings) -> tuple[list[list[int]], str] | None:
    """
    Gets a random Art array and title using provided application settings.
    Returns a tuple (art_data, title) or None if not found or on error.
    """
    if settings.saying_db_enable != "1":
         log.info("Art requested but sayings DB is disabled in settings.")
         return None

    row = _fetch_random_row("art", ("art_data", "title"), settings)

    if row:
        art_data_str, title = row
        try:
            art_data = from_json(art_data_str)
            if isinstance(art_data, list):
                return (art_data, str(title) if title else "")
            else:
                log.warning("Art data is not a list.")
                return None
        except ValueError as e:
            log.error(f"Failed to decode art data: {e}")
            return None
    return None
