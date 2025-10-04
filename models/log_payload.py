from pydantic import BaseModel, Field
from models.log_level import LogLevel


class LogPayload(BaseModel):
    """Model representing a log payload for the central logging service."""
    application_name: str = Field(description="Name of the application")
    environment: str = Field(description="Environment (production, staging, development)")
    hostname: str = Field(description="Hostname of the server")
    level: LogLevel = Field(description="Log level")
    message: str = Field(description="Log message")
    timestamp: str = Field(description="ISO 8601 timestamp")
    trace_id: str = Field(description="Trace ID for distributed tracing")
    version: str = Field(description="Application version")
