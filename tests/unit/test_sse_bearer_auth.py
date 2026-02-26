"""Tests for SSE bearer auth that uses request context."""

import httpx
import pytest
from unittest.mock import Mock
from heblo_mcp.sse_bearer_auth import SSEBearerAuth
from heblo_mcp.user_context import UserContext


def test_sse_bearer_auth_adds_token():
    """Test that SSE bearer auth adds token from user context."""
    user_ctx = UserContext(
        email="user@example.com",
        tenant_id="test-tenant",
        object_id="obj-123",
        token="user-token-123"
    )

    auth = SSEBearerAuth()
    request = httpx.Request("GET", "https://api.example.com/test")

    # Simulate ASGI scope attached to request
    # In real usage, this would come from middleware
    request.extensions = {"user_context": user_ctx}

    # Apply auth
    flow = auth.auth_flow(request)
    authed_request = next(flow)

    # Verify Authorization header was added
    assert "Authorization" in authed_request.headers
    assert authed_request.headers["Authorization"] == "Bearer user-token-123"


def test_sse_bearer_auth_no_context():
    """Test that SSE bearer auth handles missing user context."""
    auth = SSEBearerAuth()
    request = httpx.Request("GET", "https://api.example.com/test")

    # No user context in extensions
    request.extensions = {}

    # Apply auth - should not add header
    flow = auth.auth_flow(request)
    authed_request = next(flow)

    # No Authorization header should be added
    assert "Authorization" not in authed_request.headers
