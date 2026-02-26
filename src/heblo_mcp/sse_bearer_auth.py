"""Bearer auth for SSE mode that uses user context from request."""

from collections.abc import Generator

import httpx


class SSEBearerAuth(httpx.Auth):
    """httpx Auth handler for SSE mode.

    Extracts user token from request context (set by SSEAuthMiddleware)
    and adds it to the Authorization header for Heblo API calls.
    """

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        """Implement httpx auth flow.

        Args:
            request: The outgoing HTTP request

        Yields:
            Request with Authorization header if user context available
        """
        # Try to get user context from request extensions
        # This is set by SSEAuthMiddleware
        user_ctx = request.extensions.get("user_context")

        if user_ctx and hasattr(user_ctx, "token"):
            # Add Bearer token to request
            request.headers["Authorization"] = f"Bearer {user_ctx.token}"

        # Send request
        yield request
