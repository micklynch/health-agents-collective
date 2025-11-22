"""
MCP server configuration for Triage agent.

This module provides the MCP server configuration for the healthcare triage system.
"""

import os
import sys
from pydantic_ai.mcp import MCPServerStdio

from src.core.config import settings

# Pull the FHIR endpoint from configuration
fhir_server_url = settings.fhir_base_url

# Triage MCP server
server = MCPServerStdio(
    command=sys.executable,
    args=["-m", "src.mcp_handler.triage_mcp_server"],
    env={
        "FHIR_SERVER_URL": fhir_server_url.rstrip("/"),
        "TRIAGE_MODE": "healthcare",
        "FHIR_INTEGRATION": "true"
    }
)