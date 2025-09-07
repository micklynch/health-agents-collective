"""
Core module for Health Agents Collective.
Provides shared utilities and configuration management.
"""

from .config import settings, get_fhir_url, get_agent_headers, validate_configuration

__all__ = ["settings", "get_fhir_url", "get_agent_headers", "validate_configuration"]