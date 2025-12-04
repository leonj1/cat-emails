"""
Centralized constants for the Cat-Emails application.

This module provides a single source of truth for configuration constants
used across the application, preventing hardcoded duplicates and ensuring consistency.
"""

# LLM Service Configuration
DEFAULT_REQUESTYAI_BASE_URL = "https://router.requesty.ai/v1"
"""Default base URL for RequestYAI API endpoints.

This is the correct endpoint that returns HTTP 401 (Unauthorized) when auth is missing,
indicating a valid API endpoint. The old endpoint (api.requesty.ai/openai/v1) returns
HTTP 404 (Not Found), indicating it's invalid or deprecated.

Can be overridden via environment variables:
- REQUESTYAI_BASE_URL (preferred)
- REQUESTY_BASE_URL (legacy)
"""
