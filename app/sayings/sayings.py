
import mysql.connector
import logging
# from typing import Union # Reverted for Python 3.10+
from app.config import Settings

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

def _get_db_connection(settings: Settings) -> mysql.connector.MySQLConnection | None: # Reverted
    """
    Establishes and returns a MySQL database connection using provided settings.
    Returns None if configuration is incomplete or connection fails.
    """
    # Check if essential DB configuration is present
    required_settings = [
        settings.saying_db_user,
        settings.saying_db_pass,
        settings.saying_db_host,
        settings.saying_db_port,
        settings.saying_db_name
    ]
    if not all(s is not None for s in required_settings):
        log.error("Database configuration is incomplete in settings.")
        # Optionally raise ValueError("Incomplete database configuration.")
        return None

    try:
        cnx = mysql.connector.connect(
            user=settings.saying_db_user,
            password=settings.saying_db_pass,
            host=settings.saying_db_host,
            port=int(settings.saying_db_port), # Ensure port is int
            database=settings.saying_db_name,
            connection_timeout=5 # Add a connection timeout
        )
        log.debug("Database connection successful.")
        return cnx
    except mysql.connector.Error as err:
        log.error(f"Error connecting to database: {err}")
        return None
    except ValueError as verr:
        log.error(f"Database configuration error (e.g., non-integer port): {verr}")
        return None


def _get_random_quote_from_db(table_name: str, settings: Settings) -> str | None: # Reverted
    """
    Connects to the DB using settings, fetches a random quote from the specified table.
    Ensures resources are closed properly. Returns the quote string or None.
    """
    cnx = None
    cur = None
    try:
        cnx = _get_db_connection(settings)
        if not cnx:
            # Error already logged in _get_db_connection
            return None

        # Using f-string safely here as table_name comes from trusted internal calls.
        # Be cautious if table_name could ever be derived from external input.
        q_string = f'SELECT quote FROM {table_name} ORDER BY RAND() LIMIT 1'

        cur = cnx.cursor()
        log.debug(f"Executing query: {q_string}")
        cur.execute(q_string)
        result = cur.fetchone() # Returns a tuple (quote,) or None

        if result and result[0] is not None:
            log.debug(f"Quote found in {table_name}.")
            return str(result[0]) # Return the quote string
        else:
            log.warning(f"No quote found in table {table_name} or result was NULL.")
            return None

    except mysql.connector.Error as err:
        # Log the error that occurred during query execution
        log.error(f"Database query error fetching quote from {table_name}: {err}")
        return None # Return None on error
    finally:
        # Ensure cursor and connection are closed
        if cur:
            try:
                cur.close()
                log.debug("Database cursor closed.")
            except mysql.connector.Error as err:
                 log.warning(f"Error closing cursor: {err}")
        if cnx and cnx.is_connected():
            try:
                cnx.close()
                log.debug("Database connection closed.")
            except mysql.connector.Error as err:
                 log.warning(f"Error closing connection: {err}")


# --- Public Functions ---

def GetSingleRandSfwS(settings: Settings) -> str | None: # Reverted
    """
    Gets a random SFW quote using provided application settings.
    Returns the quote string or None if not found or on error.
    """
    if settings.saying_db_enable != "1":
         log.info("SFW quote requested but sayings DB is disabled in settings.")
         return None # Or raise an exception if preferred
    return _get_random_quote_from_db("sfw_quotes", settings)

def GetSingleRandNsfwS(settings: Settings) -> str | None: # Reverted
    """
    Gets a random NSFW quote using provided application settings.
    Returns the quote string or None if not found or on error.
    """
    if settings.saying_db_enable != "1":
         log.info("NSFW quote requested but sayings DB is disabled in settings.")
         return None # Or raise an exception if preferred
    return _get_random_quote_from_db("nsfw_quotes", settings)