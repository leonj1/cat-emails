#!/usr/bin/env python3
"""
Test script for the /api/config endpoint.
"""
import os
import sys
from unittest.mock import MagicMock

# Mock SettingsService before api_service is imported
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

# Set minimal environment variables for testing
os.environ.setdefault("REQUESTYAI_API_KEY", "test-key-for-config-endpoint")
os.environ.setdefault("DATABASE_PATH", "./email_summaries/summaries.db")

from fastapi.testclient import TestClient
from api_service import app

def test_config_endpoint():
    """Test the configuration endpoint returns expected structure."""
    client = TestClient(app)
    
    # Make request to config endpoint
    response = client.get("/api/config")
    
    print("Status Code:", response.status_code)
    print("\nResponse JSON:")
    import json
    print(json.dumps(response.json(), indent=2))
    
    # Validate response structure
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    data = response.json()
    
    # Check top-level keys
    assert "database" in data
    assert "llm" in data
    assert "background_processing" in data
    assert "api_service" in data
    assert "environment" in data
    assert "version" in data
    
    # Check database config
    db_config = data["database"]
    assert "type" in db_config
    assert db_config["type"] in ["mysql", "sqlite_local", "sqlite_cloud", "unknown"]
    assert "connected" in db_config
    assert "connection_status" in db_config

    # Check database env_vars if MySQL type (SQLite doesn't include env_vars)
    if db_config["type"] == "mysql":
        assert "env_vars" in db_config
        env_vars = db_config["env_vars"]
        assert "host_var" in env_vars
        assert env_vars["host_var"] == "MYSQL_HOST"
        assert "host_value" in env_vars
        assert "name_var" in env_vars
        assert env_vars["name_var"] == "MYSQL_DATABASE"
        assert "name_value" in env_vars
        assert "user_var" in env_vars
        assert env_vars["user_var"] == "MYSQL_USER"
        assert "user_value" in env_vars
        # Verify password and port are NOT included
        assert "password_var" not in env_vars
        assert "password_value" not in env_vars
        assert "port_var" not in env_vars
        assert "port_value" not in env_vars
    
    # Check LLM config
    llm_config = data["llm"]
    assert "provider" in llm_config
    assert "model" in llm_config
    assert "api_key_configured" in llm_config
    assert llm_config["api_key_configured"]  # We set REQUESTYAI_API_KEY
    
    # Check background processing config
    bg_config = data["background_processing"]
    assert "enabled" in bg_config
    assert "scan_interval_seconds" in bg_config
    assert "lookback_hours" in bg_config
    
    # Check API service config
    api_config = data["api_service"]
    assert "host" in api_config
    assert "port" in api_config
    assert "api_key_required" in api_config
    
    print("\n✅ All validation checks passed!")
    
    return data


if __name__ == "__main__":
    try:
        config_data = test_config_endpoint()
        print("\n" + "="*60)
        print("Configuration Summary:")
        print("="*60)
        print(f"Database Type: {config_data['database']['type']}")
        print(f"LLM Provider: {config_data['llm']['provider']}")
        print(f"LLM Model: {config_data['llm']['model']}")
        print(f"Background Processing: {'Enabled' if config_data['background_processing']['enabled'] else 'Disabled'}")
        print(f"Environment: {config_data['environment']}")
        print("="*60)
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
