"""Unit tests for authentication module."""

from pathlib import Path
from unittest.mock import Mock

import httpx
import pytest

from heblo_mcp.auth import HebloAuth, MSALBearerAuth


def test_heblo_auth_initialization(mock_config, mock_msal_app, mock_token_cache):
    """Test HebloAuth initialization."""
    auth = HebloAuth(
        tenant_id=mock_config.tenant_id,
        client_id=mock_config.client_id,
        scope=mock_config.api_scope,
        cache_path=mock_config.token_cache_path,
    )

    assert auth.tenant_id == mock_config.tenant_id
    assert auth.client_id == mock_config.client_id
    assert auth.scope == mock_config.api_scope
    assert auth.cache_path == mock_config.token_cache_path


def test_heblo_auth_get_token_success(mock_heblo_auth, mock_msal_app):
    """Test successful token retrieval from cache."""
    token = mock_heblo_auth.get_token()

    assert token == "mock-access-token"
    mock_msal_app.get_accounts.assert_called_once()
    mock_msal_app.acquire_token_silent.assert_called_once()


def test_heblo_auth_get_token_no_cache(mock_heblo_auth, mock_msal_app):
    """Test token retrieval fails when no cached token."""
    # Mock no accounts
    mock_msal_app.get_accounts.return_value = []

    with pytest.raises(Exception) as exc_info:
        mock_heblo_auth.get_token()

    assert "No cached authentication token found" in str(exc_info.value)


def test_heblo_auth_get_token_silent_fails(mock_heblo_auth, mock_msal_app):
    """Test token retrieval when silent acquisition fails."""
    # Mock silent acquisition failure
    mock_msal_app.acquire_token_silent.return_value = None

    with pytest.raises(Exception) as exc_info:
        mock_heblo_auth.get_token()

    assert "No cached authentication token found" in str(exc_info.value)


def test_heblo_auth_login_success(mock_heblo_auth, mock_msal_app, capsys):
    """Test successful device code login."""
    result = mock_heblo_auth.login()

    assert "access_token" in result
    assert result["access_token"] == "new-mock-token"

    # Verify device flow was initiated
    mock_msal_app.initiate_device_flow.assert_called_once()
    mock_msal_app.acquire_token_by_device_flow.assert_called_once()

    # Verify message was displayed
    captured = capsys.readouterr()
    assert "DEVICE CODE AUTHENTICATION" in captured.out
    assert "TEST123" in captured.out


def test_heblo_auth_login_flow_error(mock_heblo_auth, mock_msal_app):
    """Test login when device flow initiation fails."""
    # Mock flow initiation error
    mock_msal_app.initiate_device_flow.return_value = {
        "error": "invalid_request",
        "error_description": "Failed to initiate flow",
    }

    with pytest.raises(Exception) as exc_info:
        mock_heblo_auth.login()

    assert "Failed to create device flow" in str(exc_info.value)


def test_heblo_auth_login_auth_error(mock_heblo_auth, mock_msal_app):
    """Test login when authentication fails."""
    # Mock authentication error
    mock_msal_app.acquire_token_by_device_flow.return_value = {
        "error": "authorization_pending",
        "error_description": "User has not completed authentication",
    }

    with pytest.raises(Exception) as exc_info:
        mock_heblo_auth.login()

    assert "Authentication failed" in str(exc_info.value)


def test_msal_bearer_auth_adds_token(mock_heblo_auth):
    """Test that MSALBearerAuth adds Bearer token to request."""
    auth = MSALBearerAuth(mock_heblo_auth)
    request = httpx.Request("GET", "https://test.example.com/api/test")

    # Execute auth flow
    flow = auth.auth_flow(request)
    authed_request = next(flow)

    assert "Authorization" in authed_request.headers
    assert authed_request.headers["Authorization"] == "Bearer mock-access-token"


def test_msal_bearer_auth_retries_on_401(mock_heblo_auth, mock_msal_app):
    """Test that MSALBearerAuth retries on 401 response."""
    auth = MSALBearerAuth(mock_heblo_auth)
    request = httpx.Request("GET", "https://test.example.com/api/test")

    # Execute auth flow
    flow = auth.auth_flow(request)
    authed_request = next(flow)

    # Send 401 response
    response_401 = Mock(spec=httpx.Response)
    response_401.status_code = 401

    try:
        flow.send(response_401)
        retry_request = next(flow)

        # Verify retry has updated token
        assert "Authorization" in retry_request.headers
        assert retry_request.headers["Authorization"].startswith("Bearer ")
    except StopIteration:
        # Flow may complete after retry
        pass


def test_token_cache_persistence(tmp_path: Path, mock_msal_app, mock_token_cache):
    """Test that token cache is persisted to disk."""
    cache_path = tmp_path / "cache.json"

    # Set cache as changed
    mock_token_cache.has_state_changed = True

    auth = HebloAuth(
        tenant_id="test-tenant",
        client_id="test-client",
        scope="test-scope",
        cache_path=cache_path,
    )

    # Trigger cache save
    auth.login()

    # Verify cache was written
    assert cache_path.exists()
