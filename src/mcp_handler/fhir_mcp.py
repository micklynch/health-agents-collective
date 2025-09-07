import requests
from src.core.config import settings
from pydantic_ai.mcp import MCPServerStdio

FHIR_SERVER_URL = settings.fhir_base_url.strip()
if not FHIR_SERVER_URL:
    raise ValueError("FHIR base URL is not set in configuration. Please set it in your .env.local file as HAPI_MCP_SERVER_HOST or update src/core/config.py defaults.")

# Create MCP server process definition - runs this Python MCP server file
mcp_server = MCPServerStdio(
    command="uv",
    args=[
        "run",
        "python",
        "src/mcp_handler/fhir_mcp_main.py"
    ],
    env={"FHIR_SERVER_URL": FHIR_SERVER_URL},
)

# Note:
# The actual MCP tool methods will be implemented in `fhir_mcp_main.py`
# which will be started as a subprocess by MCPServerStdio above.

# This module should only export `mcp_server` for the Pydantic AI Agent integration.
