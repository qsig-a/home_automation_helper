import pytest
from unittest.mock import patch, MagicMock
import mysql.connector # To mock mysql.connector.Error if needed by _get_db_connection mock

from app.sayings.sayings import GetSingleRandSfwS, GetSingleRandNsfwS, _get_db_connection
from app.config import Settings # Used for type hinting and creating test instances


@pytest.fixture
def mock_settings_db_enabled() -> Settings:
    """Returns a Settings instance with DB enabled and dummy connection details."""
    settings = Settings()
    settings.saying_db_enable = "1"
    settings.saying_db_user = "testuser"
    settings.saying_db_pass = "testpass"
    settings.saying_db_host = "testhost"
    settings.saying_db_port = 3306
    settings.saying_db_name = "testdb"
    return settings

@pytest.fixture
def mock_settings_db_disabled() -> Settings:
    """Returns a Settings instance with DB disabled."""
    settings = Settings()
    settings.saying_db_enable = "0"
    return settings


# Parametrize to run tests for both SFW and NSFW functions
@pytest.mark.parametrize(
    "saying_function, table_name",
    [
        (GetSingleRandSfwS, "sfw_quotes"),
        (GetSingleRandNsfwS, "nsfw_quotes"),
    ]
)
class TestSayingFunctions:

    def test_db_disabled(self, saying_function, table_name, mock_settings_db_disabled):
        """
        Tests that the saying function returns None when the database is disabled
        and does not attempt to connect.
        """
        with patch("app.sayings.sayings._get_db_connection") as mock_get_conn:
            result = saying_function(settings=mock_settings_db_disabled)
            assert result is None
            mock_get_conn.assert_not_called()

    @patch("app.sayings.sayings._get_db_connection")
    def test_quote_found(self, mock_get_conn: MagicMock, saying_function, table_name, mock_settings_db_enabled):
        """
        Tests successful quote retrieval when the database is enabled.
        """
        expected_quote = "This is a test quote."
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (expected_quote,) # DB returns a tuple
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        result = saying_function(settings=mock_settings_db_enabled)

        assert result == expected_quote
        mock_get_conn.assert_called_once_with(mock_settings_db_enabled)
        mock_conn.cursor.assert_called_once_with() # Corrected: no dictionary=True argument
        expected_query = f"SELECT quote FROM {table_name} ORDER BY RAND() LIMIT 1"
        mock_cursor.execute.assert_called_once_with(expected_query)
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch("app.sayings.sayings._get_db_connection")
    def test_no_quote_found(self, mock_get_conn: MagicMock, saying_function, table_name, mock_settings_db_enabled):
        """
        Tests behavior when no quote is found in the database.
        """
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None # Simulate no quote found
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        result = saying_function(settings=mock_settings_db_enabled)

        assert result is None
        mock_get_conn.assert_called_once_with(mock_settings_db_enabled)
        expected_query = f"SELECT quote FROM {table_name} ORDER BY RAND() LIMIT 1"
        mock_cursor.execute.assert_called_once_with(expected_query)

    @patch("app.sayings.sayings._get_db_connection")
    def test_db_connection_error(self, mock_get_conn: MagicMock, saying_function, table_name, mock_settings_db_enabled):
        """
        Tests behavior when _get_db_connection raises a database error.
        """
        # Simulate mysql.connector.Error (or a subclass like InterfaceError)
        mock_get_conn.side_effect = mysql.connector.Error("Simulated DB connection error")

        result = saying_function(settings=mock_settings_db_enabled)
        
        assert result is None
        mock_get_conn.assert_called_once_with(mock_settings_db_enabled)

    @patch("app.sayings.sayings._get_db_connection")
    def test_db_cursor_execute_error(self, mock_get_conn: MagicMock, saying_function, table_name, mock_settings_db_enabled):
        """
        Tests behavior when cursor.execute() raises a database error.
        """
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        # Simulate mysql.connector.Error (or a subclass like ProgrammingError)
        mock_cursor.execute.side_effect = mysql.connector.Error("Simulated cursor execution error")
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        result = saying_function(settings=mock_settings_db_enabled)

        assert result is None
        mock_get_conn.assert_called_once_with(mock_settings_db_enabled)
        expected_query = f"SELECT quote FROM {table_name} ORDER BY RAND() LIMIT 1"
        mock_cursor.execute.assert_called_once_with(expected_query)
        # Ensure resources are closed even if execute fails mid-try block
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch("app.sayings.sayings._get_db_connection")
    def test_db_cursor_fetchone_error(self, mock_get_conn: MagicMock, saying_function, table_name, mock_settings_db_enabled):
        """
        Tests behavior when cursor.fetchone() raises an error.
        """
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = mysql.connector.Error("Simulated fetchone error")
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        result = saying_function(settings=mock_settings_db_enabled)

        assert result is None
        mock_get_conn.assert_called_once_with(mock_settings_db_enabled)
        expected_query = f"SELECT quote FROM {table_name} ORDER BY RAND() LIMIT 1"
        mock_cursor.execute.assert_called_once_with(expected_query)
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()


# Remove or keep the initial setup test if desired
# def test_initial_sayings_setup():
#     assert True


# --- Tests for _get_db_connection ---
class TestGetDBConnection:

    @patch("app.sayings.sayings.mysql.connector.connect")
    def test_successful_connection(self, mock_mysql_connect: MagicMock, mock_settings_db_enabled: Settings):
        """
        Tests that _get_db_connection returns a connection object on success
        and calls mysql.connector.connect with correct parameters.
        """
        mock_conn_obj = MagicMock(spec=mysql.connector.MySQLConnection)
        mock_mysql_connect.return_value = mock_conn_obj

        conn = _get_db_connection(settings=mock_settings_db_enabled)

        assert conn == mock_conn_obj
        mock_mysql_connect.assert_called_once_with(
            user=mock_settings_db_enabled.saying_db_user,
            password=mock_settings_db_enabled.saying_db_pass,
            host=mock_settings_db_enabled.saying_db_host,
            port=int(mock_settings_db_enabled.saying_db_port),
            database=mock_settings_db_enabled.saying_db_name,
            connection_timeout=5
        )

    def test_incomplete_settings(self, mock_settings_db_enabled: Settings):
        """
        Tests that _get_db_connection returns None if settings are incomplete.
        """
        incomplete_settings = mock_settings_db_enabled
        incomplete_settings.saying_db_user = None # Make one setting missing

        with patch("app.sayings.sayings.log.error") as mock_log_error:
            conn = _get_db_connection(settings=incomplete_settings)
            assert conn is None
            mock_log_error.assert_called_once_with("Database configuration is incomplete in settings.")
        
        # Restore for other tests if settings object is shared (pytest fixtures are usually per-test)
        mock_settings_db_enabled.saying_db_user = "testuser" 

    @patch("app.sayings.sayings.mysql.connector.connect")
    def test_connection_raises_mysql_error(self, mock_mysql_connect: MagicMock, mock_settings_db_enabled: Settings):
        """
        Tests that _get_db_connection returns None if mysql.connector.connect raises an error.
        """
        mock_mysql_connect.side_effect = mysql.connector.Error("Simulated connection failure")

        with patch("app.sayings.sayings.log.error") as mock_log_error:
            conn = _get_db_connection(settings=mock_settings_db_enabled)
            assert conn is None
            mock_log_error.assert_called_once_with("Error connecting to database: Simulated connection failure")

    @patch("app.sayings.sayings.mysql.connector.connect")
    def test_connection_raises_value_error_on_port(self, mock_mysql_connect: MagicMock, mock_settings_db_enabled: Settings):
        """
        Tests that _get_db_connection returns None if port conversion raises ValueError.
        (This is less likely with Pydantic models but tests defense in depth).
        """
        # Pydantic model should ensure port is int, but if it somehow gets a bad string:
        original_port = mock_settings_db_enabled.saying_db_port
        mock_settings_db_enabled.saying_db_port = "not-a-number" # type: ignore 
        
        # We don't even need to mock mysql.connector.connect for this,
        # as the error should happen before. If connect was called, it would be an error in the test.
        mock_mysql_connect.side_effect = ValueError("This should ideally not be called if port conversion fails first")

        with patch("app.sayings.sayings.log.error") as mock_log_error:
            conn = _get_db_connection(settings=mock_settings_db_enabled)
            assert conn is None
            # The error message check depends on where the int conversion happens.
            # In the provided sayings.py, it's `port=int(settings.saying_db_port)`.
            # So, a ValueError from that `int()` conversion is caught by the second except block.
            assert "Database configuration error" in mock_log_error.call_args[0][0]
            assert "invalid literal for int()" in str(mock_log_error.call_args[0][0]).lower() # Corrected: Check within the first arg
        
        mock_settings_db_enabled.saying_db_port = original_port # Restore
