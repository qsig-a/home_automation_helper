# tests/conftest.py - Shared fixtures for pytest
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

from app.main import app, get_settings, get_vestaboard_connector # Import the dependency functions
from app.config import Settings
from app.connectors.vestaboard import VestaboardConnector


@pytest.fixture
def mock_settings() -> Settings:
    """
    Fixture to provide a mock Settings object.
    Tests can override specific attributes on the returned object.
    """
    settings = Settings()
    # Default to DB being disabled for most tests unless overridden
    settings.saying_db_enable = "0"
    settings.vestaboard_api_key = "test_api_key"
    settings.vestaboard_api_secret = "test_api_secret"
    return settings


@pytest.fixture
def mock_vestaboard_connector() -> AsyncMock:
    """
    Fixture to provide a mock VestaboardConnector.
    The methods are AsyncMocks.
    """
    connector = AsyncMock(spec=VestaboardConnector)
    connector.send_message = AsyncMock(return_value=None)
    connector.send_array = AsyncMock(return_value=None)
    connector.close = AsyncMock(return_value=None) # Ensure close is also an AsyncMock if called with await
    return connector


@pytest.fixture
def client(
    mock_settings: Settings,
    mock_vestaboard_connector: AsyncMock
) -> TestClient:
    """
    Fixture to provide a TestClient for the FastAPI app,
    with dependencies overridden for settings and Vestaboard connector.
    """

    # Dependency override functions
    def override_get_settings():
        return mock_settings

    def override_get_vestaboard_connector():
        return mock_vestaboard_connector

    # Apply the overrides
    app.dependency_overrides[get_settings] = override_get_settings # Use the imported function as key
    app.dependency_overrides[get_vestaboard_connector] = override_get_vestaboard_connector # Use the imported function as key
    
    # Create the TestClient
    test_client = TestClient(app)
    yield test_client # Use yield to ensure lifespan events are handled if any are critical for tests

    # Clean up overrides after tests are done
    app.dependency_overrides.clear()
