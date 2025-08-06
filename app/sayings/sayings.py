
import mysql.connector
import logging
from contextlib import contextmanager
# from typing import Union # Reverted for Python 3.10+
from app.config import Settings

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

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

    cnx = None
    try:
        cnx = mysql.connector.connect(
            user=settings.saying_db_user,
            password=settings.saying_db_pass,
            host=settings.saying_db_host,
            port=int(settings.saying_db_port),
            database=settings.saying_db_name,
            connection_timeout=5
        )
        log.debug("Database connection successful.")
        yield cnx
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
                log.debug("Database connection closed.")
            except mysql.connector.Error as err:
                log.warning(f"Error closing connection: {err}")

def _fetch_quote_from_table(table_name: str, settings: Settings) -> str | None:
    """Fetches a random quote from a given table using a managed DB connection."""
    try:
        with _db_connection(settings) as cnx:
            with cnx.cursor() as cur:
                # Using f-string safely as table_name comes from trusted internal calls
                query = f'SELECT quote FROM {table_name} ORDER BY RAND() LIMIT 1'
                log.debug(f"Executing query: {query}")
                cur.execute(query)
                result = cur.fetchone()

                if result and result[0] is not None:
                    log.debug(f"Quote found in {table_name}.")
                    return str(result[0])
                else:
                    log.warning(f"No quote found in table {table_name} or result was NULL.")
                    return None
    except mysql.connector.Error as err:
        log.error(f"Database query error in {table_name}: {err}")
        # Propagate as a standard error for the caller to handle
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
    return _fetch_quote_from_table("sfw_quotes", settings)

def GetSingleRandNsfwS(settings: Settings) -> str | None: # Reverted
    """
    Gets a random NSFW quote using provided application settings.
    Returns the quote string or None if not found or on error.
    """
    if settings.saying_db_enable != "1":
         log.info("NSFW quote requested but sayings DB is disabled in settings.")
         return None # Or raise an exception if preferred
    return _fetch_quote_from_table("nsfw_quotes", settings)