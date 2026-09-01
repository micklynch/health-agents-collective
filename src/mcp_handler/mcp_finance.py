"""
MCP server configuration for Finance agent.

This module provides the MCP server configuration for the healthcare
finance / revenue cycle system.
"""

import sys
from pydantic_ai.mcp import MCPServerStdio

from src.core.config import settings

# Finance MCP server
server = MCPServerStdio(
    command=sys.executable,
    args=["-m", "src.mcp_handler.finance_mcp_server"],
    env={
        "FINANCE_CLEARINGHOUSE_URL": settings.finance_clearinghouse_url or "",
        "FINANCE_EDI_SENDER_ID": settings.finance_edi_sender_id,
        "FINANCE_EDI_RECEIVER_ID": settings.finance_edi_receiver_id,
        "FINANCE_MODE": "us-revenue-cycle",
    }
)
