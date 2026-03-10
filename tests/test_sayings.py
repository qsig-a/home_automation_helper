import pytest
from unittest.mock import patch, MagicMock
import mysql.connector
import json

from app.sayings.sayings import GetSingleRandSfwS, GetSingleRandNsfwS, GetSingleRandArt, init_db_pool, close_db_pool, _fetch_column_from_table, _fetch_random_row
import app.sayings.sayings as say
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
        with patch("app.sayings.sayings._fetch_column_from_table") as mock_fetch:
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
        expected_query = f"SELECT t1.quote FROM {table_name} AS t1 JOIN (SELECT id FROM {table_name} WHERE id >= (SELECT FLOOR(RAND() * (MAX(id) - MIN(id) + 1)) + MIN(id) FROM {table_name}) ORDER BY id LIMIT 1) AS t2 ON t1.id = t2.id"
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

class TestSayingsValidation:
    def test_fetch_column_invalid_table(self, mock_settings_db_enabled):
        with pytest.raises(ValueError, match="Invalid table name: invalid_table"):
            _fetch_column_from_table("invalid_table", "quote", mock_settings_db_enabled)

    def test_fetch_column_invalid_column(self, mock_settings_db_enabled):
        with pytest.raises(ValueError, match="Invalid column name: invalid_column"):
            _fetch_column_from_table("sfw_quotes", "invalid_column", mock_settings_db_enabled)

    def test_fetch_random_row_invalid_table(self, mock_settings_db_enabled):
        with pytest.raises(ValueError, match="Invalid table name: invalid_table"):
            _fetch_random_row("invalid_table", ["quote"], mock_settings_db_enabled)

    def test_fetch_random_row_invalid_column(self, mock_settings_db_enabled):
        with pytest.raises(ValueError, match="Invalid column name: invalid_column"):
            _fetch_random_row("sfw_quotes", ["quote", "invalid_column"], mock_settings_db_enabled)

class TestPoolFunctions:
    @patch("app.sayings.sayings.pooling.MySQLConnectionPool")
    def test_init_db_pool_enabled(self, mock_pool, mock_settings_db_enabled):
        say._connection_pool = None
        init_db_pool(mock_settings_db_enabled)
        mock_pool.assert_called_once_with(
            pool_name="sayings_pool",
            pool_size=5,
            pool_reset_session=True,
            user=mock_settings_db_enabled.saying_db_user,
            password=mock_settings_db_enabled.saying_db_pass,
            host=mock_settings_db_enabled.saying_db_host,
            port=mock_settings_db_enabled.saying_db_port,
            database=mock_settings_db_enabled.saying_db_name,
            connection_timeout=5
        )
        assert say._connection_pool is not None

    @patch("app.sayings.sayings.pooling.MySQLConnectionPool")
    def test_init_db_pool_disabled(self, mock_pool, mock_settings_db_disabled):
        say._connection_pool = None
        init_db_pool(mock_settings_db_disabled)
        mock_pool.assert_not_called()
        assert say._connection_pool is None

    @patch("app.sayings.sayings.pooling.MySQLConnectionPool")
    def test_close_db_pool(self, mock_pool, mock_settings_db_enabled):
        say._connection_pool = None
        init_db_pool(mock_settings_db_enabled)
        assert say._connection_pool is not None
        close_db_pool()
        assert say._connection_pool is None

    @patch("app.sayings.sayings.pooling.MySQLConnectionPool")
    @patch("app.sayings.sayings.log.error")
    def test_init_db_pool_mysql_error(self, mock_log_error, mock_pool, mock_settings_db_enabled):
        mock_pool.side_effect = mysql.connector.Error("Simulated pool initialization error")
        say._connection_pool = None
        init_db_pool(mock_settings_db_enabled)
        mock_log_error.assert_called_once_with("Error initializing connection pool: Simulated pool initialization error")
        assert say._connection_pool is None

class TestArtFunctions:
    def test_db_disabled(self, mock_settings_db_disabled):
        with patch("app.sayings.sayings._fetch_random_row") as mock_fetch:
            result = GetSingleRandArt(settings=mock_settings_db_disabled)
            assert result is None
            mock_fetch.assert_not_called()

    @patch("app.sayings.sayings._fetch_random_row")
    def test_art_found_valid_json(self, mock_fetch, mock_settings_db_enabled):
        expected_art = [[1, 2], [3, 4]]
        expected_title = "Mona Lisa"
        mock_fetch.return_value = (json.dumps(expected_art), expected_title)

        result = GetSingleRandArt(settings=mock_settings_db_enabled)

        assert result == (expected_art, expected_title)
        mock_fetch.assert_called_once_with("art", ["art_data", "title"], mock_settings_db_enabled)

    @patch("app.sayings.sayings._fetch_random_row")
    def test_art_found_invalid_json(self, mock_fetch, mock_settings_db_enabled):
        mock_fetch.return_value = ("invalid json", "Some Title")

        result = GetSingleRandArt(settings=mock_settings_db_enabled)

        assert result is None

    @patch("app.sayings.sayings._fetch_random_row")
    def test_art_found_not_list(self, mock_fetch, mock_settings_db_enabled):
        mock_fetch.return_value = (json.dumps({"key": "value"}), "Some Title") # Not a list

        result = GetSingleRandArt(settings=mock_settings_db_enabled)

        assert result is None

    @patch("app.sayings.sayings._fetch_random_row")
    def test_no_art_found(self, mock_fetch, mock_settings_db_enabled):
        mock_fetch.return_value = None

        result = GetSingleRandArt(settings=mock_settings_db_enabled)

        assert result is None
