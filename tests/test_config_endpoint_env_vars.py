"""
Unit tests for _get_database_config() env_vars handling.

Tests that the database configuration function correctly returns database
environment variable names and values (host, name, user) while excluding
sensitive data (password, port).

IMPORTANT: This project uses MYSQL_* environment variables ONLY.
The DATABASE_* naming convention is NOT supported.
"""
import os
import unittest
from unittest.mock import patch, MagicMock
import sys

# Mock SettingsService before api_service is imported
# NOTE: We use sys.modules manipulation here because api_service.py instantiates
# SettingsService at the module level (global scope). To prevent the real SettingsService
# from attempting to connect to the database (which would fail in this test environment),
# we must inject a mock into sys.modules BEFORE api_service is imported.
# This ensures that 'from services.settings_service import SettingsService' inside
# api_service uses our mock class.

# IMPORTANT: Save the original module so we can restore it after tests complete
# This prevents polluting other tests that import SettingsService
_original_settings_module = sys.modules.get('services.settings_service')

mock_settings_module = MagicMock()
# Configure the mock to return a dictionary with strings when get_connection_status is called
mock_repo = MagicMock()
mock_repo.get_connection_status.return_value = {
    "connected": False,
    "status": "Mocked Connection",
    "error": None,
    "details": {
        "host": "mock_host",
        "port": 3306,
        "database": "mock_db",
        "pool_size": 5
    }
}
mock_settings_instance = MagicMock()
mock_settings_instance.repository = mock_repo
mock_settings_module.SettingsService.return_value = mock_settings_instance

sys.modules['services.settings_service'] = mock_settings_module


def _restore_settings_module():
    """Restore the original settings_service module after tests."""
    if _original_settings_module is not None:
        sys.modules['services.settings_service'] = _original_settings_module
    elif 'services.settings_service' in sys.modules:
        del sys.modules['services.settings_service']


# Register cleanup with atexit for when run standalone
import atexit
atexit.register(_restore_settings_module)

# Also use pytest module-level teardown to restore after this test module completes
import pytest

@pytest.fixture(scope="module", autouse=True)
def restore_settings_module_after_tests():
    """Pytest fixture to restore settings_service module after all tests in this module."""
    yield  # Run all tests in this module
    _restore_settings_module()

# Set minimal environment variables before importing api_service
os.environ.setdefault("REQUESTYAI_API_KEY", "test-key")

from models.config_response import DatabaseConfig, DatabaseEnvVars


class TestDatabaseEnvVarsModel(unittest.TestCase):
    """Test the DatabaseEnvVars Pydantic model."""

    def test_database_env_vars_default_values(self):
        """Test that DatabaseEnvVars has correct default variable names (MYSQL_* only)."""
        env_vars = DatabaseEnvVars()
        self.assertEqual(env_vars.host_var, "MYSQL_HOST")
        self.assertEqual(env_vars.name_var, "MYSQL_DATABASE")
        self.assertEqual(env_vars.user_var, "MYSQL_USER")
        self.assertIsNone(env_vars.host_value)
        self.assertIsNone(env_vars.name_value)
        self.assertIsNone(env_vars.user_value)

    def test_database_env_vars_with_values(self):
        """Test DatabaseEnvVars with actual values."""
        env_vars = DatabaseEnvVars(
            host_value="db.example.com",
            name_value="my_database",
            user_value="db_user"
        )
        self.assertEqual(env_vars.host_var, "MYSQL_HOST")
        self.assertEqual(env_vars.host_value, "db.example.com")
        self.assertEqual(env_vars.name_var, "MYSQL_DATABASE")
        self.assertEqual(env_vars.name_value, "my_database")
        self.assertEqual(env_vars.user_var, "MYSQL_USER")
        self.assertEqual(env_vars.user_value, "db_user")

    def test_only_mysql_env_vars_in_model(self):
        """Test that only MYSQL_* env var names are used, not DATABASE_*."""
        env_vars = DatabaseEnvVars()
        env_vars_dict = env_vars.model_dump()

        # Verify all *_var fields use MYSQL_ prefix
        for key, value in env_vars_dict.items():
            if key.endswith("_var"):
                self.assertTrue(
                    value.startswith("MYSQL_"),
                    f"Expected {key} to use MYSQL_ prefix, got: {value}"
                )
                self.assertFalse(
                    value.startswith("DATABASE_"),
                    f"DATABASE_* env vars are not supported, found: {value}"
                )

    def test_database_env_vars_excludes_password_and_port(self):
        """Test that DatabaseEnvVars model doesn't include password or port fields."""
        env_vars = DatabaseEnvVars()
        # Verify password and port fields don't exist in the model
        self.assertFalse(hasattr(env_vars, 'password_var'))
        self.assertFalse(hasattr(env_vars, 'password_value'))
        self.assertFalse(hasattr(env_vars, 'port_var'))
        self.assertFalse(hasattr(env_vars, 'port_value'))


class TestDatabaseConfigWithEnvVars(unittest.TestCase):
    """Test DatabaseConfig includes env_vars field."""

    def test_database_config_with_env_vars(self):
        """Test DatabaseConfig can include env_vars."""
        env_vars = DatabaseEnvVars(
            host_value="localhost",
            name_value="test_db",
            user_value="test_user"
        )
        config = DatabaseConfig(
            type="mysql",
            host="localhost",
            port=3306,
            database_name="test_db",
            connected=True,
            connection_status="Connected",
            env_vars=env_vars
        )
        self.assertIsNotNone(config.env_vars)
        self.assertEqual(config.env_vars.host_value, "localhost")
        self.assertEqual(config.env_vars.name_value, "test_db")
        self.assertEqual(config.env_vars.user_value, "test_user")

    def test_database_config_without_env_vars(self):
        """Test DatabaseConfig works without env_vars (e.g., for SQLite)."""
        config = DatabaseConfig(
            type="sqlite_local",
            path="/path/to/db.sqlite",
            connected=True,
            connection_status="Connected"
        )
        self.assertIsNone(config.env_vars)


class TestGetDatabaseConfigEnvVars(unittest.TestCase):
    """Unit tests for _get_database_config() env_vars handling."""

    @patch('api_service.settings_service')
    @patch.dict(os.environ, {
        "MYSQL_HOST": "mysql.example.com",
        "MYSQL_DATABASE": "production_db",
        "MYSQL_USER": "prod_user",
        "MYSQL_PASSWORD": "secret_password",  # Should NOT appear in response
        "MYSQL_PORT": "3307",  # Should NOT appear in env_vars
        "REQUESTYAI_API_KEY": "test-key"
    }, clear=False)
    def test_mysql_config_includes_env_vars(self, mock_settings_service):
        """Test that MySQL configuration includes env_vars with correct values."""
        # Mock repository to return proper connection status
        mock_settings_service.repository.get_connection_status.return_value = {
            "connected": False,
            "status": "Mocked Connection",
            "error": None,
            "details": {}
        }

        # Import here to get fresh module with patched env
        from api_service import _get_database_config

        config = _get_database_config()

        self.assertEqual(config.type, "mysql")
        self.assertIsNotNone(config.env_vars)

        # Check env var names are MYSQL_* only
        self.assertEqual(config.env_vars.host_var, "MYSQL_HOST")
        self.assertEqual(config.env_vars.name_var, "MYSQL_DATABASE")
        self.assertEqual(config.env_vars.user_var, "MYSQL_USER")

        # Check env var values
        self.assertEqual(config.env_vars.host_value, "mysql.example.com")
        self.assertEqual(config.env_vars.name_value, "production_db")
        self.assertEqual(config.env_vars.user_value, "prod_user")

    @patch('api_service.settings_service')
    @patch.dict(os.environ, {
        "MYSQL_HOST": "mysql.example.com",
        "MYSQL_PASSWORD": "super_secret",
        "REQUESTYAI_API_KEY": "test-key"
    }, clear=False)
    def test_env_vars_excludes_password(self, mock_settings_service):
        """Test that password is never included in env_vars."""
        # Mock repository to return proper connection status
        mock_settings_service.repository.get_connection_status.return_value = {
            "connected": False,
            "status": "Mocked Connection",
            "error": None,
            "details": {}
        }

        from api_service import _get_database_config

        config = _get_database_config()

        self.assertIsNotNone(config.env_vars)

        # Serialize to dict and verify no password fields
        env_vars_dict = config.env_vars.model_dump()
        self.assertNotIn("password_var", env_vars_dict)
        self.assertNotIn("password_value", env_vars_dict)

        # Also verify no value contains the password
        for value in env_vars_dict.values():
            if value is not None:
                self.assertNotEqual(value, "super_secret")

    @patch('api_service.settings_service')
    @patch.dict(os.environ, {
        "MYSQL_HOST": "mysql.example.com",
        "MYSQL_PORT": "3307",
        "REQUESTYAI_API_KEY": "test-key"
    }, clear=False)
    def test_env_vars_excludes_port(self, mock_settings_service):
        """Test that port is never included in env_vars."""
        # Mock repository to return proper connection status
        mock_settings_service.repository.get_connection_status.return_value = {
            "connected": False,
            "status": "Mocked Connection",
            "error": None,
            "details": {}
        }

        from api_service import _get_database_config

        config = _get_database_config()

        self.assertIsNotNone(config.env_vars)

        # Serialize to dict and verify no port fields
        env_vars_dict = config.env_vars.model_dump()
        self.assertNotIn("port_var", env_vars_dict)
        self.assertNotIn("port_value", env_vars_dict)

    @patch('api_service.settings_service')
    @patch.dict(os.environ, {
        "MYSQL_HOST": "mysql.example.com",
        "MYSQL_PORT": "",  # Empty string - Railway sets this
        "MYSQL_POOL_SIZE": "",  # Empty string
        "REQUESTYAI_API_KEY": "test-key"
    }, clear=False)
    def test_empty_string_port_uses_default(self, mock_settings_service):
        """Test that empty string MYSQL_PORT falls back to default 3306.

        Railway may set environment variables to empty strings instead of
        leaving them unset, which would cause int('') to fail.
        """
        # Mock repository to return proper connection status
        mock_settings_service.repository.get_connection_status.return_value = {
            "connected": False,
            "status": "Mocked Connection",
            "error": None,
            "details": {}
        }

        from api_service import _get_database_config

        # This should NOT raise ValueError: invalid literal for int() with base 10: ''
        config = _get_database_config()

        self.assertEqual(config.type, "mysql")
        self.assertEqual(config.port, 3306)  # Default port
        self.assertEqual(config.connection_pool_size, 5)  # Default pool size

    @patch('api_service.settings_service')
    @patch.dict(os.environ, {
        "DATABASE_PATH": "/var/lib/app/data.db",
        "REQUESTYAI_API_KEY": "test-key"
    }, clear=False)
    def test_sqlite_config_no_longer_supported(self, mock_settings_service):
        """Test that SQLite configuration is no longer supported and defaults to MySQL."""
        # Clear MySQL-related env vars for this test
        env_backup = {}
        for key in ["MYSQL_HOST", "MYSQL_USER", "MYSQL_URL"]:
            if key in os.environ:
                env_backup[key] = os.environ.pop(key)
        
        # Mock repository to report disconnected
        mock_settings_service.repository.get_connection_status.return_value = {
            "connected": False, 
            "status": "Not connected", 
            "error": None,
            "details": {}
        }

        try:
            from api_service import _get_database_config

            config = _get_database_config()

            # Should return mysql type even without MySQL env vars (default behavior)
            self.assertEqual(config.type, "mysql")
            # Should still have env_vars object (empty/default)
            self.assertIsNotNone(config.env_vars)
        finally:
            # Restore env vars
            os.environ.update(env_backup)

    @patch('api_service.settings_service')
    @patch.dict(os.environ, {
        "MYSQL_USER": "only_user_set",
        "REQUESTYAI_API_KEY": "test-key"
    }, clear=False)
    def test_partial_env_vars_handled(self, mock_settings_service):
        """Test that partial environment configuration is handled correctly."""
        # Mock repository to return proper connection status
        mock_settings_service.repository.get_connection_status.return_value = {
            "connected": False,
            "status": "Mocked Connection",
            "error": None,
            "details": {}
        }

        from api_service import _get_database_config

        config = _get_database_config()

        self.assertEqual(config.type, "mysql")
        self.assertIsNotNone(config.env_vars)

        # Only user should have a value
        self.assertEqual(config.env_vars.user_value, "only_user_set")
        # Host should be None since not set
        self.assertIsNone(config.env_vars.host_value)

    @patch('api_service.settings_service')
    @patch.dict(os.environ, {
        "MYSQL_HOST": "mysql.example.com",
        "MYSQL_DATABASE": "test_db",
        "MYSQL_USER": "test_user",
        "REQUESTYAI_API_KEY": "test-key"
    }, clear=False)
    def test_only_mysql_env_vars_in_config_response(self, mock_settings_service):
        """Test that only MYSQL_* env vars are returned in config, not DATABASE_*."""
        # Mock repository to return proper connection status
        mock_settings_service.repository.get_connection_status.return_value = {
            "connected": False,
            "status": "Mocked Connection",
            "error": None,
            "details": {}
        }

        from api_service import _get_database_config

        config = _get_database_config()

        self.assertEqual(config.type, "mysql")
        self.assertIsNotNone(config.env_vars)

        # Verify all var names use MYSQL_ prefix
        self.assertTrue(config.env_vars.host_var.startswith("MYSQL_"))
        self.assertTrue(config.env_vars.name_var.startswith("MYSQL_"))
        self.assertTrue(config.env_vars.user_var.startswith("MYSQL_"))

        # Verify no DATABASE_* prefix is used
        self.assertFalse(config.env_vars.host_var.startswith("DATABASE_"))
        self.assertFalse(config.env_vars.name_var.startswith("DATABASE_"))
        self.assertFalse(config.env_vars.user_var.startswith("DATABASE_"))


if __name__ == "__main__":
    unittest.main()
