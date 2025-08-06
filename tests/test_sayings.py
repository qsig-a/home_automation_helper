import pytest
from unittest.mock import patch, MagicMock
import mysql.connector

from app.sayings.sayings import GetSingleRandSfwS, GetSingleRandNsfwS
from app.config import Settings

@pytest.fixture
def mock_settings_db_enabled() -> Settings:
    """Returns a Settings instance with DB enabled and dummy connection details."""
    return Settings(
        saying_db_enable="1",
        saying_db_user="testuser",
        saying_db_pass="testpass",
        saying_db_host="testhost",
        saying_db_port=3306,
        saying_db_name="testdb"
    )

@pytest.fixture
def mock_settings_db_disabled() -> Settings:
    """Returns a Settings instance with DB disabled."""
    return Settings(saying_db_enable="0")

@pytest.mark.parametrize(
    "saying_function, table_name",
    [
        (GetSingleRandSfwS, "sfw_quotes"),
        (GetSingleRandNsfwS, "nsfw_quotes"),
    ]
)
class TestSayingFunctions:

    def test_db_disabled(self, saying_function, table_name, mock_settings_db_disabled):
        with patch("app.sayings.sayings._fetch_quote_from_table") as mock_fetch:
            result = saying_function(settings=mock_settings_db_disabled)
            assert result is None
            mock_fetch.assert_not_called()

    @patch("app.sayings.sayings._db_connection")
    def test_quote_found(self, mock_db_conn: MagicMock, saying_function, table_name, mock_settings_db_enabled):
        expected_quote = "This is a test quote."
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (expected_quote,)

        # This is how you mock a context manager
        mock_conn_context = MagicMock()
        mock_conn_context.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        mock_db_conn.return_value = mock_conn_context

        result = saying_function(settings=mock_settings_db_enabled)

        assert result == expected_quote
        mock_db_conn.assert_called_once_with(mock_settings_db_enabled)
        expected_query = f"SELECT quote FROM {table_name} ORDER BY RAND() LIMIT 1"
        mock_cursor.execute.assert_called_once_with(expected_query)

    @patch("app.sayings.sayings._db_connection")
    def test_no_quote_found(self, mock_db_conn: MagicMock, saying_function, table_name, mock_settings_db_enabled):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None

        mock_conn_context = MagicMock()
        mock_conn_context.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        mock_db_conn.return_value = mock_conn_context

        result = saying_function(settings=mock_settings_db_enabled)

        assert result is None

    @patch("app.sayings.sayings._db_connection")
    def test_db_connection_error(self, mock_db_conn: MagicMock, saying_function, table_name, mock_settings_db_enabled):
        mock_db_conn.side_effect = ConnectionError("Simulated DB connection error")

        with pytest.raises(ConnectionError, match="Simulated DB connection error"):
            saying_function(settings=mock_settings_db_enabled)

    @patch("app.sayings.sayings._db_connection")
    def test_db_cursor_execute_error(self, mock_db_conn: MagicMock, saying_function, table_name, mock_settings_db_enabled):
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = mysql.connector.Error("Simulated cursor execution error")

        mock_conn_context = MagicMock()
        mock_conn_context.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        mock_db_conn.return_value = mock_conn_context

        with pytest.raises(ConnectionError, match="Database query failed"):
            saying_function(settings=mock_settings_db_enabled)
