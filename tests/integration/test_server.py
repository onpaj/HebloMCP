"""Integration tests for MCP server creation and operation."""

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from heblo_mcp.server import create_server


@pytest.mark.asyncio
async def test_create_server_success(mock_config, mock_msal_app, mock_token_cache, sample_openapi_spec):
    """Test successful MCP server creation."""
    # Mock fetch_and_patch_spec
    with patch("heblo_mcp.server.fetch_and_patch_spec") as mock_fetch:
        mock_fetch.return_value = sample_openapi_spec

        # Create server
        mcp = await create_server(mock_config)

        # Verify server was created
        assert mcp is not None
        assert hasattr(mcp, "name")

        # Verify spec was fetched
        mock_fetch.assert_called_once_with(mock_config.openapi_spec_url)


@pytest.mark.asyncio
async def test_create_server_with_default_config(mock_msal_app, mock_token_cache, sample_openapi_spec, monkeypatch):
    """Test server creation with default config loading."""
    # Set required env vars
    monkeypatch.setenv("HEBLO_TENANT_ID", "test-tenant")
    monkeypatch.setenv("HEBLO_CLIENT_ID", "test-client")

    with patch("heblo_mcp.server.fetch_and_patch_spec") as mock_fetch:
        mock_fetch.return_value = sample_openapi_spec

        # Create server without explicit config
        mcp = await create_server()

        assert mcp is not None


@pytest.mark.asyncio
async def test_server_http_client_configuration(mock_config, mock_msal_app, mock_token_cache, sample_openapi_spec):
    """Test that HTTP client is correctly configured."""
    with patch("heblo_mcp.server.fetch_and_patch_spec") as mock_fetch:
        mock_fetch.return_value = sample_openapi_spec

        with patch("heblo_mcp.server.httpx.AsyncClient") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            await create_server(mock_config)

            # Verify client was created with correct params
            mock_client_class.assert_called_once()
            call_kwargs = mock_client_class.call_args.kwargs

            assert call_kwargs["base_url"] == mock_config.api_base_url
            assert call_kwargs["timeout"] == 60.0
            assert "auth" in call_kwargs
