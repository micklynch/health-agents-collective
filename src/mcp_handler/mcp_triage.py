"""
MCP server configuration for Triage agent.

This module provides the MCP server configuration for the healthcare triage system.
"""

from pydantic_ai.mcp import MCPServerStdio

# Triage MCP server - this would connect to a triage service
server = MCPServerStdio(
    command="python",
    args=["-m", "triage_mcp_server"],
    env={
        "TRIAGE_MODE": "healthcare",
        "FHIR_INTEGRATION": "true"
    }
)