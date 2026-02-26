"""SSE authentication middleware for HebloMCP."""

import json
from collections.abc import Callable

from heblo_mcp.token_validator import TokenValidationError, TokenValidator


def _extract_bearer_token(headers: list[tuple[bytes, bytes]]) -> str | None:
    """Extract Bearer token from Authorization header.

    Args:
        headers: List of (name, value) header tuples

    Returns:
        Token string if found, None otherwise
    """
    for name, value in headers:
        if name.lower() == b"authorization":
            auth_value = value.decode("utf-8")
            if auth_value.startswith("Bearer "):
                return auth_value[7:]  # Remove "Bearer " prefix
    return None


class SSEAuthMiddleware:
    """ASGI middleware for SSE authentication.

    Validates Bearer tokens from Authorization header and attaches
    user context to request scope.
    """

    def __init__(self, app: Callable, token_validator: TokenValidator, bypass_health: bool = True):
        """Initialize middleware.

        Args:
            app: ASGI application
            token_validator: Token validator instance
            bypass_health: If True, bypass auth for health endpoint (/)
        """
        self.app = app
        self.token_validator = token_validator
        self.bypass_health = bypass_health

    async def __call__(self, scope, receive, send):
        """ASGI middleware callable.

        Args:
            scope: ASGI scope dict
            receive: ASGI receive callable
            send: ASGI send callable
        """
        # Only process HTTP requests
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Bypass health endpoint if configured
        if self.bypass_health and scope.get("path") == "/":
            await self.app(scope, receive, send)
            return

        # Bypass OAuth endpoints (they handle their own auth)
        oauth_paths = ["/authorize", "/callback", "/token"]
        if scope.get("path") in oauth_paths:
            await self.app(scope, receive, send)
            return

        # Extract token
        headers = scope.get("headers", [])
        token = _extract_bearer_token(headers)

        if not token:
            # No token - send 401
            await self._send_401(send, "Authentication required. Please provide Bearer token.")
            return

        try:
            # Validate token
            user_ctx = await self.token_validator.validate_token(token)

            # Attach user context to scope
            scope["user"] = user_ctx

            # Call next middleware/app
            await self.app(scope, receive, send)

        except TokenValidationError as e:
            # Invalid token - send 401
            await self._send_401(send, str(e))

    async def _send_401(self, send: Callable, message: str):
        """Send 401 Unauthorized response.

        Args:
            send: ASGI send callable
            message: Error message
        """
        body = json.dumps({"error": message}).encode("utf-8")

        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("utf-8")),
                ],
            }
        )

        await send(
            {
                "type": "http.response.body",
                "body": body,
            }
        )
