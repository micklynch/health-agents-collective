"""
MCP server configuration for FHIR integration.

This module provides the MCP server configuration for connecting to FHIR servers.
"""

import os
from pydantic_ai.mcp import MCPServerStdio

# Get FHIR server URL from environment variable
fhir_server_url = os.getenv("FHIR_SERVER_URL", "http://192.168.68.211:8080/fhir")

# Create MCP server for FHIR
server = MCPServerStdio(
    command="python",
    args=["-m", "fhir_mcp_server"],
    env={
        "FHIR_SERVER_URL": fhir_server_url,
        "FHIR_VERSION": "R4"
    }
)