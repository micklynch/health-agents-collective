"""
MCP server configuration for FHIR integration.

This module provides the MCP server configuration for connecting to FHIR servers.
"""

import os
import sys
from pydantic_ai.mcp import MCPServerStdio

# Pull the FHIR endpoint from configuration, honoring either the legacy
# FHIR_SERVER_URL or the newer FHIR_BASE_URL used in .env.
fhir_server_url = (
    os.getenv("FHIR_SERVER_URL")
    or os.getenv("FHIR_BASE_URL")
    or "https://r4.smarthealthit.org"
)

# Create MCP server for FHIR using the real launcher module.
server = MCPServerStdio(
    command=sys.executable,
    args=["-m", "src.mcp_handler.fhir_mcp_main"],
    env={
        "FHIR_SERVER_URL": fhir_server_url.rstrip("/"),
        "FHIR_VERSION": os.getenv("FHIR_VERSION", "R4"),
    },
)