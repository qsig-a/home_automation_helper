import time
import asyncio
from unittest.mock import MagicMock
from app.config import get_settings
import app.sayings.sayings

settings = get_settings()
settings.saying_db_enable = '1'
settings.saying_db_user = 'testuser'
settings.saying_db_pass = 'testpass'
settings.saying_db_host = 'testhost'
settings.saying_db_port = 3306
settings.saying_db_name = 'testdb'

mock_db_conn = MagicMock()
mock_cursor = MagicMock()
mock_cursor.fetchone.return_value = ('This is a test quote.',)
mock_db_conn.cursor.return_value.__enter__.return_value = mock_cursor

# Simulate real database connection delay
def mock_connect(*args, **kwargs):
    time.sleep(0.01) # Simulate network/connection latency
    return mock_db_conn

app.sayings.sayings.mysql = MagicMock()
app.sayings.sayings.mysql.connector.connect.side_effect = mock_connect

# 1. Test without pool (baseline)
# Force clear pool to simulate old behavior
app.sayings.sayings._connection_pool = None

start_no_pool = time.time()
for _ in range(100):
    app.sayings.sayings.GetSingleRandSfwS(settings)
end_no_pool = time.time()
time_no_pool = end_no_pool - start_no_pool

# 2. Test with pool
# Mock the pool behavior
mock_pool = MagicMock()
mock_pool.get_connection.return_value = mock_db_conn
app.sayings.sayings._connection_pool = mock_pool

start_with_pool = time.time()
for _ in range(100):
    app.sayings.sayings.GetSingleRandSfwS(settings)
end_with_pool = time.time()
time_with_pool = end_with_pool - start_with_pool

print(f"Time taken without pool (simulated 10ms connect delay): {time_no_pool:.4f}s")
print(f"Time taken with pool    (simulated 10ms connect delay): {time_with_pool:.4f}s")

if time_no_pool > 0:
    improvement = ((time_no_pool - time_with_pool) / time_no_pool) * 100
    print(f"Performance improvement: {improvement:.2f}%")
