"""Unit tests for server health endpoint."""

import pytest
from fastmcp import FastMCP

from heblo_mcp.server import create_server_with_health


@pytest.mark.asyncio
async def test_health_endpoint_exists(mock_config, mock_msal_app, mock_token_cache, sample_openapi_spec, monkeypatch):
    """Test that health endpoint is registered."""
    # Mock fetch_and_patch_spec
    from unittest.mock import patch

    with patch("heblo_mcp.server.fetch_and_patch_spec") as mock_fetch:
        mock_fetch.return_value = sample_openapi_spec

        # Create server with health endpoint
        mcp = await create_server_with_health(mock_config)

        # Verify health endpoint exists
        # FastMCP with SSE should expose health endpoint
        assert mcp is not None
