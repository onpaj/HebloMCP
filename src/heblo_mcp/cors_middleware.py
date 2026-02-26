"""CORS middleware for SSE transport."""

from collections.abc import Callable


class CORSMiddleware:
    """ASGI middleware for handling CORS preflight requests.

    Allows MCP clients to make cross-origin requests to the SSE endpoint.
    """

    def __init__(
        self,
        app: Callable,
        allow_origins: list[str] | None = None,
        allow_methods: list[str] | None = None,
        allow_headers: list[str] | None = None,
    ):
        """Initialize CORS middleware.

        Args:
            app: ASGI application
            allow_origins: Allowed origins (default: ["*"])
            allow_methods: Allowed methods (default: ["GET", "POST", "OPTIONS"])
            allow_headers: Allowed headers (default: ["*"])
        """
        self.app = app
        self.allow_origins = allow_origins or ["*"]
        self.allow_methods = allow_methods or ["GET", "POST", "OPTIONS"]
        self.allow_headers = allow_headers or ["*"]

    async def __call__(self, scope, receive, send):
        """ASGI middleware callable."""
        # Only process HTTP requests
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Handle OPTIONS preflight requests
        if scope["method"] == "OPTIONS":
            await self._send_preflight_response(send)
            return

        # For other requests, add CORS headers
        async def send_with_cors(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(self._get_cors_headers())
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_cors)

    def _get_cors_headers(self) -> list[tuple[bytes, bytes]]:
        """Get CORS headers."""
        return [
            (b"access-control-allow-origin", b"*"),
            (b"access-control-allow-methods", ", ".join(self.allow_methods).encode()),
            (b"access-control-allow-headers", b"*"),
            (b"access-control-max-age", b"86400"),
        ]

    async def _send_preflight_response(self, send: Callable):
        """Send CORS preflight response."""
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": self._get_cors_headers() + [(b"content-length", b"0")],
        })
        await send({
            "type": "http.response.body",
            "body": b"",
        })
