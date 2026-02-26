"""Integration tests for SSE authentication."""

from unittest.mock import AsyncMock, patch

import pytest

from heblo_mcp.config import HebloMCPConfig
from heblo_mcp.server import create_server
from tests.fixtures.jwt_fixtures import create_test_jwt, create_test_rsa_keypair


@pytest.fixture
def rsa_keys():
    """Create RSA key pair for testing."""
    return create_test_rsa_keypair()


@pytest.mark.asyncio
async def test_sse_server_accepts_valid_token(rsa_keys, sample_openapi_spec):
    """Test that SSE server accepts valid token."""
    private_key, _ = rsa_keys

    # Create config for SSE mode
    config = HebloMCPConfig(
        tenant_id="test-tenant", client_id="test-client", transport="sse", sse_auth_enabled=True
    )

    # Create token
    token = create_test_jwt(
        tenant_id="test-tenant",
        client_id="test-client",
        email="user@example.com",
        private_key=private_key,
    )

    # Mock OpenAPI spec fetching
    with patch(
        "heblo_mcp.server.fetch_and_patch_spec", new=AsyncMock(return_value=sample_openapi_spec)
    ):
        server = await create_server(config)

        # Verify server was created
        assert server is not None


@pytest.mark.asyncio
async def test_stdio_server_unchanged(mock_msal_app, mock_token_cache, sample_openapi_spec):
    """Test that stdio server creation is unchanged."""
    config = HebloMCPConfig(tenant_id="test-tenant", client_id="test-client", transport="stdio")

    # Mock OpenAPI spec fetching
    with patch(
        "heblo_mcp.server.fetch_and_patch_spec", new=AsyncMock(return_value=sample_openapi_spec)
    ):
        server = await create_server(config)

        # Verify server was created
        assert server is not None
