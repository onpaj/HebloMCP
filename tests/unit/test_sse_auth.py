"""Tests for SSE authentication middleware."""

import pytest
from unittest.mock import AsyncMock, Mock
from heblo_mcp.sse_auth import SSEAuthMiddleware
from heblo_mcp.token_validator import TokenValidator, TokenValidationError
from heblo_mcp.user_context import UserContext


class MockSend:
    """Mock send callable for ASGI."""

    def __init__(self):
        self.events = []

    async def __call__(self, event):
        self.events.append(event)


class MockReceive:
    """Mock receive callable for ASGI."""

    def __init__(self, events=None):
        self.events = events or []
        self.index = 0

    async def __call__(self):
        if self.index < len(self.events):
            event = self.events[self.index]
            self.index += 1
            return event
        return {"type": "http.disconnect"}


@pytest.fixture
def mock_validator():
    """Create a mock token validator."""
    validator = Mock(spec=TokenValidator)
    validator.validate_token = AsyncMock()
    return validator


@pytest.fixture
def mock_app():
    """Create a mock ASGI app."""
    app = AsyncMock()
    return app


@pytest.mark.asyncio
async def test_extract_bearer_token_success():
    """Test extracting Bearer token from Authorization header."""
    from heblo_mcp.sse_auth import _extract_bearer_token

    headers = [(b"authorization", b"Bearer test-token-123")]
    token = _extract_bearer_token(headers)
    assert token == "test-token-123"


@pytest.mark.asyncio
async def test_extract_bearer_token_no_header():
    """Test that missing Authorization header returns None."""
    from heblo_mcp.sse_auth import _extract_bearer_token

    headers = []
    token = _extract_bearer_token(headers)
    assert token is None


@pytest.mark.asyncio
async def test_extract_bearer_token_wrong_scheme():
    """Test that non-Bearer auth returns None."""
    from heblo_mcp.sse_auth import _extract_bearer_token

    headers = [(b"authorization", b"Basic dXNlcjpwYXNz")]
    token = _extract_bearer_token(headers)
    assert token is None


@pytest.mark.asyncio
async def test_middleware_with_valid_token(mock_validator, mock_app):
    """Test middleware with valid token."""
    # Setup
    user_ctx = UserContext(
        email="user@example.com",
        tenant_id="test-tenant",
        object_id="obj-123",
        token="valid-token"
    )
    mock_validator.validate_token.return_value = user_ctx

    middleware = SSEAuthMiddleware(mock_app, mock_validator, bypass_health=True)

    scope = {
        "type": "http",
        "path": "/some-endpoint",
        "headers": [(b"authorization", b"Bearer valid-token")],
    }

    receive = MockReceive()
    send = MockSend()

    # Execute
    await middleware(scope, receive, send)

    # Verify
    mock_validator.validate_token.assert_called_once_with("valid-token")
    assert "user" in scope
    assert scope["user"] == user_ctx
    mock_app.assert_called_once()


@pytest.mark.asyncio
async def test_middleware_missing_token(mock_validator, mock_app):
    """Test middleware rejects missing token."""
    middleware = SSEAuthMiddleware(mock_app, mock_validator, bypass_health=True)

    scope = {
        "type": "http",
        "path": "/some-endpoint",
        "headers": [],
    }

    receive = MockReceive()
    send = MockSend()

    # Execute
    await middleware(scope, receive, send)

    # Verify - should send 401
    assert len(send.events) > 0
    start_event = send.events[0]
    assert start_event["type"] == "http.response.start"
    assert start_event["status"] == 401


@pytest.mark.asyncio
async def test_middleware_invalid_token(mock_validator, mock_app):
    """Test middleware rejects invalid token."""
    mock_validator.validate_token.side_effect = TokenValidationError("Invalid token")

    middleware = SSEAuthMiddleware(mock_app, mock_validator, bypass_health=True)

    scope = {
        "type": "http",
        "path": "/some-endpoint",
        "headers": [(b"authorization", b"Bearer invalid-token")],
    }

    receive = MockReceive()
    send = MockSend()

    # Execute
    await middleware(scope, receive, send)

    # Verify - should send 401
    assert len(send.events) > 0
    start_event = send.events[0]
    assert start_event["type"] == "http.response.start"
    assert start_event["status"] == 401


@pytest.mark.asyncio
async def test_middleware_bypasses_health_endpoint(mock_validator, mock_app):
    """Test middleware bypasses health endpoint."""
    middleware = SSEAuthMiddleware(mock_app, mock_validator, bypass_health=True)

    scope = {
        "type": "http",
        "path": "/",
        "headers": [],
    }

    receive = MockReceive()
    send = MockSend()

    # Execute
    await middleware(scope, receive, send)

    # Verify - should call app without validation
    mock_validator.validate_token.assert_not_called()
    mock_app.assert_called_once()
