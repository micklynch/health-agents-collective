"""
Configuration management for Health Agents Collective.
Handles environment variables and application settings.
"""

import os
from typing import Optional

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load .env files. A .env.local file can be used to override variables for local development.
load_dotenv()
load_dotenv(".env.local", override=True)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # FHIR Server Configuration
    fhir_base_url: str = "http://192.168.68.211:8080/fhir"
    fhir_version: str = "R4"

    # Agent Configuration
    agent_name: str = "health-agents-collective"
    agent_version: str = "1.0.0"

    # A2A Protocol Configuration
    a2a_enabled: bool = True
    a2a_endpoint: Optional[str] = None

    # MCP Configuration
    mcp_enabled: bool = True
    mcp_server_name: str = "fhir-server"

    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Logfire Configuration
    logfire_token: Optional[str] = None
    logfire_project_name: str = "healthcare-agents-collective"
    logfire_environment: str = "development"

    # Security Configuration
    api_key: Optional[str] = None
    enable_cors: bool = True

    # Open Router Configuration
    open_router_api_key: Optional[str] = None
    open_router_base_url: Optional[str] = None

    class Config:
        # .env files are loaded using python-dotenv
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_fhir_url() -> str:
    """Get the complete FHIR server URL."""
    return f"{settings.fhir_base_url}/{settings.fhir_version}"


def get_agent_headers() -> dict:
    """Get standard headers for agent requests."""
    headers = {
        "Content-Type": "application/fhir+json",
        "Accept": "application/fhir+json",
        "User-Agent": f"{settings.agent_name}/{settings.agent_version}",
    }
    
    if settings.api_key:
        headers["Authorization"] = f"Bearer {settings.api_key}"
    
    return headers


def validate_configuration() -> bool:
    """Validate that required configuration is present."""
    required_vars = ["fhir_base_url"]
    
    for var in required_vars:
        if not getattr(settings, var):
            raise ValueError(f"Required configuration variable '{var}' is missing")
    
    return True
