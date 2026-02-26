"""Tests for JWT token validation."""

import pytest
from unittest.mock import AsyncMock, patch
from heblo_mcp.token_validator import TokenValidator, TokenValidationError
from tests.fixtures.jwt_fixtures import (
    create_test_jwt,
    create_test_rsa_keypair,
    create_test_jwks,
)


@pytest.fixture
def rsa_keys():
    """Create RSA key pair for testing."""
    return create_test_rsa_keypair()


@pytest.fixture
def mock_jwks(rsa_keys):
    """Create mock JWKS."""
    _, public_key = rsa_keys
    return create_test_jwks(public_key)


@pytest.fixture
async def validator(mock_jwks):
    """Create a TokenValidator with mocked JWKS fetching."""
    validator = TokenValidator(
        tenant_id="test-tenant",
        audience="test-client",
        jwks_cache_ttl=3600
    )

    # Mock the JWKS fetch
    with patch.object(validator, '_fetch_jwks', new=AsyncMock(return_value=mock_jwks)):
        yield validator


@pytest.mark.asyncio
async def test_validate_valid_token(validator, rsa_keys):
    """Test validating a valid JWT token."""
    private_key, _ = rsa_keys
    token = create_test_jwt(
        tenant_id="test-tenant",
        client_id="test-client",
        email="user@example.com",
        object_id="obj-123",
        private_key=private_key
    )

    user_ctx = await validator.validate_token(token)

    assert user_ctx.email == "user@example.com"
    assert user_ctx.tenant_id == "test-tenant"
    assert user_ctx.object_id == "obj-123"
    assert user_ctx.token == token


@pytest.mark.asyncio
async def test_validate_expired_token(validator, rsa_keys):
    """Test that expired tokens are rejected."""
    private_key, _ = rsa_keys
    token = create_test_jwt(
        tenant_id="test-tenant",
        client_id="test-client",
        expired=True,
        private_key=private_key
    )

    with pytest.raises(TokenValidationError, match="expired"):
        await validator.validate_token(token)


@pytest.mark.asyncio
async def test_validate_wrong_audience(validator, rsa_keys):
    """Test that tokens with wrong audience are rejected."""
    private_key, _ = rsa_keys
    token = create_test_jwt(
        tenant_id="test-tenant",
        client_id="test-client",
        wrong_audience=True,
        private_key=private_key
    )

    with pytest.raises(TokenValidationError, match="audience"):
        await validator.validate_token(token)


@pytest.mark.asyncio
async def test_validate_wrong_issuer(validator, rsa_keys):
    """Test that tokens with wrong issuer are rejected."""
    private_key, _ = rsa_keys
    token = create_test_jwt(
        tenant_id="test-tenant",
        client_id="test-client",
        wrong_issuer=True,
        private_key=private_key
    )

    with pytest.raises(TokenValidationError, match="issuer"):
        await validator.validate_token(token)


@pytest.mark.asyncio
async def test_validate_malformed_token(validator):
    """Test that malformed tokens are rejected."""
    with pytest.raises(TokenValidationError, match="Invalid token format"):
        await validator.validate_token("not-a-jwt")


@pytest.mark.asyncio
async def test_jwks_caching(validator, mock_jwks):
    """Test that JWKS is cached and not fetched multiple times."""
    # This will trigger JWKS fetch
    await validator._get_jwks()

    # Mock to track calls
    with patch.object(validator, '_fetch_jwks', new=AsyncMock(return_value=mock_jwks)) as mock_fetch:
        # Should use cache
        await validator._get_jwks()
        mock_fetch.assert_not_called()
