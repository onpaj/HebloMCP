"""Unit tests for server health endpoint."""

import json

import pytest

from heblo_mcp import __version__
from heblo_mcp.server import create_server_with_health


@pytest.mark.asyncio
async def test_health_endpoint_exists(mock_config, mock_msal_app, mock_token_cache, sample_openapi_spec, monkeypatch):
    """Test that health endpoint is registered and returns correct response."""
    # Mock fetch_and_patch_spec
    from unittest.mock import patch

    with patch("heblo_mcp.server.fetch_and_patch_spec") as mock_fetch:
        mock_fetch.return_value = sample_openapi_spec

        # Create server with health endpoint
        mcp = await create_server_with_health(mock_config)

        # Verify server was created
        assert mcp is not None

        # List all tools to verify health is registered
        tools = await mcp.list_tools()
        tool_names = [tool.name for tool in tools]
        assert "health" in tool_names, "Health tool should be registered"

        # Call the health tool
        result = await mcp.call_tool("health", {})

        # Verify the response structure and values
        assert result is not None, "Result should not be None"
        assert hasattr(result, 'content'), "Result should have content attribute"
        assert len(result.content) == 1, "Result content should contain one item"

        # Parse the response from content
        response_text = result.content[0].text
        response_data = json.loads(response_text)

        # Verify expected fields and values
        assert response_data["status"] == "healthy", "Status should be 'healthy'"
        assert response_data["version"] == __version__, f"Version should be '{__version__}'"
        assert response_data["transport"] == "sse", "Transport should be 'sse'"
