import os
from unittest.mock import patch
from pydantic import SecretStr

from app.config import Settings, get_settings


def test_settings_default_values():
    """Test that Settings initializes with expected default values."""
    # Ensure no environment variables are interfering with the test
    with patch.dict(os.environ, {}, clear=True):
        settings = Settings()

    assert settings.saying_db_user is None
    assert settings.saying_db_pass is None
    assert settings.saying_db_host is None
    assert settings.saying_db_port == 3306
    assert settings.saying_db_name is None
    assert settings.saying_db_enable == "0"
    assert settings.vestaboard_rw_api_key is None
    assert settings.vestaboard_local_api_key is None
    assert settings.vestaboard_local_api_ip is None


def test_settings_from_env_vars():
    """Test that Settings correctly loads from environment variables."""
    env_vars = {
        "SAYING_DB_USER": "test_user",
        "SAYING_DB_PASS": "test_pass_secret",
        "SAYING_DB_HOST": "localhost",
        "SAYING_DB_PORT": "3307",
        "SAYING_DB_NAME": "test_db",
        "SAYING_DB_ENABLE": "1",
        "VESTABOARD_RW_API_KEY": "rw_secret_key",
        "VESTABOARD_LOCAL_API_KEY": "local_secret_key",
        "VESTABOARD_LOCAL_API_IP": "192.168.1.100",
    }

    with patch.dict(os.environ, env_vars, clear=True):
        settings = Settings()

    assert settings.saying_db_user == "test_user"
    assert isinstance(settings.saying_db_pass, SecretStr)
    assert settings.saying_db_pass.get_secret_value() == "test_pass_secret"
    assert settings.saying_db_host == "localhost"
    assert settings.saying_db_port == 3307
    assert settings.saying_db_name == "test_db"
    assert settings.saying_db_enable == "1"

    assert isinstance(settings.vestaboard_rw_api_key, SecretStr)
    assert settings.vestaboard_rw_api_key.get_secret_value() == "rw_secret_key"

    assert isinstance(settings.vestaboard_local_api_key, SecretStr)
    assert settings.vestaboard_local_api_key.get_secret_value() == "local_secret_key"

    assert settings.vestaboard_local_api_ip == "192.168.1.100"


def test_get_settings_lru_cache():
    """Test that get_settings uses lru_cache and returns the same instance."""
    # Clear cache before testing to ensure a clean state
    get_settings.cache_clear()

    settings_1 = get_settings()
    settings_2 = get_settings()

    # Both calls should return the exact same object reference
    assert settings_1 is settings_2

    get_settings.cache_clear()
