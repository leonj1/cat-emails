"""
Pydantic models for configuration endpoint responses.
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal


class DatabaseConfig(BaseModel):
    """Database configuration details"""
    type: Literal["mysql", "sqlite_local", "sqlite_cloud", "unknown"] = Field(
        ...,
        description="Type of database being used"
    )
    host: Optional[str] = Field(
        None,
        description="Database host (for MySQL/cloud SQLite)"
    )
    port: Optional[int] = Field(
        None,
        description="Database port (for MySQL)"
    )
    database_name: Optional[str] = Field(
        None,
        description="Database name"
    )
    path: Optional[str] = Field(
        None,
        description="SQLite database file path (for local SQLite)"
    )
    connection_pool_size: Optional[int] = Field(
        None,
        description="Connection pool size (for MySQL)"
    )


class LLMConfig(BaseModel):
    """LLM service configuration details"""
    provider: str = Field(
        ...,
        description="LLM provider (e.g., 'RequestYAI', 'OpenAI')"
    )
    model: str = Field(
        ...,
        description="LLM model being used"
    )
    base_url: Optional[str] = Field(
        None,
        description="Base URL for LLM API"
    )
    api_key_configured: bool = Field(
        ...,
        description="Whether an API key is configured (true/false only, no actual key)"
    )


class BackgroundProcessingConfig(BaseModel):
    """Background processing configuration"""
    enabled: bool = Field(
        ...,
        description="Whether background processing is enabled"
    )
    scan_interval_seconds: int = Field(
        ...,
        description="Interval between background scans in seconds"
    )
    lookback_hours: int = Field(
        ...,
        description="How many hours to look back when processing emails"
    )


class APIServiceConfig(BaseModel):
    """API service configuration"""
    host: str = Field(
        ...,
        description="API host"
    )
    port: int = Field(
        ...,
        description="API port"
    )
    api_key_required: bool = Field(
        ...,
        description="Whether API key authentication is required"
    )


class ConfigurationResponse(BaseModel):
    """Complete configuration response"""
    database: DatabaseConfig = Field(
        ...,
        description="Database configuration"
    )
    llm: LLMConfig = Field(
        ...,
        description="LLM service configuration"
    )
    background_processing: BackgroundProcessingConfig = Field(
        ...,
        description="Background processing configuration"
    )
    api_service: APIServiceConfig = Field(
        ...,
        description="API service configuration"
    )
    environment: str = Field(
        ...,
        description="Deployment environment (e.g., 'production', 'development', 'testing')"
    )
    version: str = Field(
        ...,
        description="API version"
    )
