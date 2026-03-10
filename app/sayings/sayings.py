
import mysql.connector
from mysql.connector import pooling
import logging
import json
from contextlib import contextmanager
# from typing import Union # Reverted for Python 3.10+
from app.config import Settings

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

_connection_pool = None

ALLOWED_TABLES = {
    "sfw_quotes": {"id", "quote", "source"},
    "nsfw_quotes": {"id", "quote", "source"},
    "art": {"id", "art_data", "title"},
}

def init_db_pool(settings: Settings):
    """Initializes the MySQL connection pool."""
    global _connection_pool
    if settings.saying_db_enable != "1":
        log.info("Database disabled, not initializing connection pool.")
        return

    required_settings = [
        settings.saying_db_user,
        settings.saying_db_pass,
        settings.saying_db_host,
        settings.saying_db_port,
        settings.saying_db_name
    ]
    if not all(required_settings):
        log.error("Database configuration is incomplete, cannot initialize pool.")
        return

    try:
        _connection_pool = pooling.MySQLConnectionPool(
            pool_name="sayings_pool",
            pool_size=5,
            pool_reset_session=True,
            user=settings.saying_db_user,
            password=settings.saying_db_pass,
            host=settings.saying_db_host,
            port=int(settings.saying_db_port),
            database=settings.saying_db_name,
            connection_timeout=5
        )
        log.info("Database connection pool initialized.")
    except mysql.connector.Error as err:
        log.error(f"Error initializing connection pool: {err}")
    except ValueError as verr:
        log.error(f"Database configuration error for pool: {verr}")

def close_db_pool():
    """Closes the connection pool (no direct method, just cleanup reference)."""
    global _connection_pool
    if _connection_pool:
        # Note: MySQLConnectionPool does not have a close() method.
        # Connections returned to the pool are closed when the pool object is garbage collected.
        _connection_pool = None
        log.info("Database connection pool reference cleared.")

@contextmanager
def _db_connection(settings: Settings):
    """A context manager for a MySQL database connection that handles setup and teardown."""
    # Check if essential DB configuration is present
    required_settings = [
        settings.saying_db_user,
        settings.saying_db_pass,
        settings.saying_db_host,
        settings.saying_db_port,
        settings.saying_db_name
    ]
    if not all(required_settings):
        log.error("Database configuration is incomplete.")
        raise ConnectionError("Database configuration is incomplete.")

    global _connection_pool
    cnx = None

    try:
        if _connection_pool:
            cnx = _connection_pool.get_connection()
            log.debug("Obtained connection from pool.")
        else:
            # Fallback for testing or if pool initialization failed
            cnx = mysql.connector.connect(
                user=settings.saying_db_user,
                password=settings.saying_db_pass,
                host=settings.saying_db_host,
                port=int(settings.saying_db_port),
                database=settings.saying_db_name,
                connection_timeout=5
            )
            log.debug("Database connection successful (no pool).")
        yield cnx
    except mysql.connector.PoolError as err:
        log.error(f"Error getting connection from pool: {err}")
        raise ConnectionError(f"Database connection pool exhausted: {err}") from err
    except mysql.connector.Error as err:
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
            except mysql.connector.Error as err:
                log.warning(f"Error closing connection/returning to pool: {err}")

def _fetch_column_from_table(table_name: str, column_name: str, settings: Settings) -> str | None:
    """Fetches a random value from a given table and column using a managed DB connection."""
    result = _fetch_random_row(table_name, [column_name], settings)

    if result and result[0] is not None:
        log.debug(f"Value found in {table_name}.{column_name}.")
        return str(result[0])
    else:
        log.warning(f"No value found in table {table_name} or result was NULL.")
        return None

def _fetch_random_row(table_name: str, columns: list[str], settings: Settings) -> tuple | None:
    """Fetches a random row for specific columns from a given table."""
    if table_name not in ALLOWED_TABLES:
        raise ValueError(f"Invalid table name: {table_name}")
    for column_name in columns:
        if column_name not in ALLOWED_TABLES[table_name]:
            raise ValueError(f"Invalid column name: {column_name}")

    try:
        with _db_connection(settings) as cnx:
            with cnx.cursor() as cur:
                cols_str = ", ".join([f"t1.{c}" for c in columns])
                # Using f-string safely as table_name and columns come from trusted internal calls
                # Optimized approach: avoid full table scan by using an inner join on a random ID
                query = f'SELECT {cols_str} FROM {table_name} AS t1 JOIN (SELECT id FROM {table_name} WHERE id >= (SELECT FLOOR(RAND() * (MAX(id) - MIN(id) + 1)) + MIN(id) FROM {table_name}) ORDER BY id LIMIT 1) AS t2 ON t1.id = t2.id'
                log.debug(f"Executing query: {query}")
                cur.execute(query)
                return cur.fetchone()
    except mysql.connector.Error as err:
        log.error(f"Database query error in {table_name}: {err}")
        raise ConnectionError(f"Database query failed for {table_name}") from err

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

def GetSingleRandArt(settings: Settings) -> tuple[list, str] | None:
    """
    Gets a random Art array and title using provided application settings.
    Returns a tuple (art_data, title) or None if not found or on error.
    """
    if settings.saying_db_enable != "1":
         log.info("Art requested but sayings DB is disabled in settings.")
         return None

    row = _fetch_random_row("art", ["art_data", "title"], settings)

    if row:
        art_data_str, title = row
        try:
            art_data = json.loads(art_data_str)
            if isinstance(art_data, list):
                return (art_data, str(title) if title else "")
            else:
                log.warning("Art data is not a list.")
                return None
        except json.JSONDecodeError as e:
            log.error(f"Failed to decode art data: {e}")
            return None
    return None
