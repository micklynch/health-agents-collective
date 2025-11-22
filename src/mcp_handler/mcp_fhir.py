"""
MCP server configuration for FHIR integration.

This module provides the MCP server configuration for connecting to FHIR servers.
"""

import os
import sys
from pydantic_ai.mcp import MCPServerStdio

from src.core.config import settings

# Pull the FHIR endpoint from configuration
fhir_server_url = settings.fhir_base_url

# Create MCP server for FHIR using the real launcher module.
server = MCPServerStdio(
    command=sys.executable,
    args=["-m", "src.mcp_handler.fhir_mcp_main"],
    env={
        "FHIR_SERVER_URL": fhir_server_url.rstrip("/"),
        "FHIR_VERSION": os.getenv("FHIR_VERSION", "R4"),
    },
)