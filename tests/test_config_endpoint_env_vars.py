"""
Unit tests for the /api/config endpoint database env_vars field.

Tests that the configuration endpoint correctly returns database environment
variable names and values (host, name, user) while excluding sensitive
data (password, port).
"""
import os
import unittest
from unittest.mock import patch, MagicMock

# Set minimal environment variables before importing api_service
os.environ.setdefault("REQUESTYAI_API_KEY", "test-key")

from fastapi.testclient import TestClient
from models.config_response import DatabaseConfig, DatabaseEnvVars


class TestDatabaseEnvVarsModel(unittest.TestCase):
    """Test the DatabaseEnvVars Pydantic model."""

    def test_database_env_vars_default_values(self):
        """Test that DatabaseEnvVars has correct default variable names."""
        env_vars = DatabaseEnvVars()
        self.assertEqual(env_vars.host_var, "DATABASE_HOST")
        self.assertEqual(env_vars.name_var, "DATABASE_NAME")
        self.assertEqual(env_vars.user_var, "DATABASE_USER")
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
        self.assertEqual(env_vars.host_var, "DATABASE_HOST")
        self.assertEqual(env_vars.host_value, "db.example.com")
        self.assertEqual(env_vars.name_var, "DATABASE_NAME")
        self.assertEqual(env_vars.name_value, "my_database")
        self.assertEqual(env_vars.user_var, "DATABASE_USER")
        self.assertEqual(env_vars.user_value, "db_user")

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


class TestConfigEndpointEnvVars(unittest.TestCase):
    """Integration tests for the /api/config endpoint env_vars field."""

    @patch.dict(os.environ, {
        "DATABASE_HOST": "mysql.example.com",
        "DATABASE_NAME": "production_db",
        "DATABASE_USER": "prod_user",
        "DATABASE_PASSWORD": "secret_password",  # Should NOT appear in response
        "DATABASE_PORT": "3307",  # Should NOT appear in env_vars
        "REQUESTYAI_API_KEY": "test-key"
    }, clear=False)
    def test_mysql_config_includes_env_vars(self):
        """Test that MySQL configuration includes env_vars with correct values."""
        # Import here to get fresh module with patched env
        from api_service import _get_database_config

        config = _get_database_config()

        self.assertEqual(config.type, "mysql")
        self.assertIsNotNone(config.env_vars)

        # Check env var names
        self.assertEqual(config.env_vars.host_var, "DATABASE_HOST")
        self.assertEqual(config.env_vars.name_var, "DATABASE_NAME")
        self.assertEqual(config.env_vars.user_var, "DATABASE_USER")

        # Check env var values
        self.assertEqual(config.env_vars.host_value, "mysql.example.com")
        self.assertEqual(config.env_vars.name_value, "production_db")
        self.assertEqual(config.env_vars.user_value, "prod_user")

    @patch.dict(os.environ, {
        "DATABASE_HOST": "mysql.example.com",
        "DATABASE_PASSWORD": "super_secret",
        "REQUESTYAI_API_KEY": "test-key"
    }, clear=False)
    def test_env_vars_excludes_password(self):
        """Test that password is never included in env_vars."""
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

    @patch.dict(os.environ, {
        "DATABASE_HOST": "mysql.example.com",
        "DATABASE_PORT": "3307",
        "REQUESTYAI_API_KEY": "test-key"
    }, clear=False)
    def test_env_vars_excludes_port(self):
        """Test that port is never included in env_vars."""
        from api_service import _get_database_config

        config = _get_database_config()

        self.assertIsNotNone(config.env_vars)

        # Serialize to dict and verify no port fields
        env_vars_dict = config.env_vars.model_dump()
        self.assertNotIn("port_var", env_vars_dict)
        self.assertNotIn("port_value", env_vars_dict)

    @patch.dict(os.environ, {
        "DATABASE_PATH": "/var/lib/app/data.db",
        "REQUESTYAI_API_KEY": "test-key"
    }, clear=False)
    def test_sqlite_config_no_env_vars(self):
        """Test that SQLite configuration doesn't include env_vars."""
        # Clear MySQL-related env vars for this test
        env_backup = {}
        for key in ["DATABASE_HOST", "DATABASE_USER", "DATABASE_URL"]:
            if key in os.environ:
                env_backup[key] = os.environ.pop(key)

        try:
            from api_service import _get_database_config

            config = _get_database_config()

            self.assertEqual(config.type, "sqlite_local")
            self.assertIsNone(config.env_vars)
        finally:
            # Restore env vars
            os.environ.update(env_backup)

    @patch.dict(os.environ, {
        "DATABASE_USER": "only_user_set",
        "REQUESTYAI_API_KEY": "test-key"
    }, clear=False)
    def test_partial_env_vars_handled(self):
        """Test that partial environment configuration is handled correctly."""
        from api_service import _get_database_config

        config = _get_database_config()

        self.assertEqual(config.type, "mysql")
        self.assertIsNotNone(config.env_vars)

        # Only user should have a value
        self.assertEqual(config.env_vars.user_value, "only_user_set")
        # Host should be None since not set
        self.assertIsNone(config.env_vars.host_value)


if __name__ == "__main__":
    unittest.main()
