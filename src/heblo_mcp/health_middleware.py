"""Health check middleware for SSE transport."""

import json
from collections.abc import Callable


class HealthCheckMiddleware:
    """ASGI middleware that provides a simple HTTP health check endpoint.

    Responds to GET requests at the root path (/) with a JSON health status.
    This allows monitoring tools and deployment pipelines to verify the service
    is running without needing to interact with the MCP protocol.
    """

    def __init__(self, app: Callable, version: str = "unknown", transport: str = "auto"):
        """Initialize health check middleware.

        Args:
            app: ASGI application to wrap
            version: Application version to include in response
            transport: Transport mode (sse, stdio, auto)
        """
        self.app = app
        self.version = version
        self.transport = transport

    async def __call__(self, scope, receive, send):
        """ASGI middleware callable."""
        # Only intercept HTTP GET requests to root path
        if (
            scope["type"] == "http"
            and scope["method"] == "GET"
            and scope["path"] == "/"
        ):
            await self._send_health_response(send)
            return

        # Pass through all other requests
        await self.app(scope, receive, send)

    async def _send_health_response(self, send: Callable):
        """Send HTTP health check response."""
        body = json.dumps({
            "status": "healthy",
            "version": self.version,
            "transport": self.transport,
        }).encode()

        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        })
        await send({
            "type": "http.response.body",
            "body": body,
        })
