"""HebloMCP server creation and configuration."""

import httpx
from fastmcp import FastMCP

from heblo_mcp import __version__
from heblo_mcp.auth import HebloAuth, MSALBearerAuth
from heblo_mcp.auth_mode import detect_transport_mode
from heblo_mcp.config import HebloMCPConfig
from heblo_mcp.routes import get_route_maps
from heblo_mcp.spec import fetch_and_patch_spec
from heblo_mcp.sse_auth import SSEAuthMiddleware
from heblo_mcp.sse_bearer_auth import SSEBearerAuth
from heblo_mcp.token_validator import TokenValidator


async def create_server(config: HebloMCPConfig | None = None) -> FastMCP:
    """Create and configure the HebloMCP FastMCP server.

    Args:
        config: Configuration object (defaults to loading from environment)

    Returns:
        Configured FastMCP server instance
    """
    # Load configuration
    if config is None:
        config = HebloMCPConfig()

    # Detect transport mode
    transport = detect_transport_mode(config)

    # Set up authentication based on transport mode
    if transport == "stdio":
        # Stdio mode: Use existing local auth with token cache
        auth = HebloAuth(
            tenant_id=config.tenant_id,
            client_id=config.client_id,
            scope=config.api_scope,
            cache_path=config.token_cache_path,
        )
        bearer_auth = MSALBearerAuth(auth)

        # Create HTTP client with authentication
        client = httpx.AsyncClient(
            base_url=config.api_base_url,
            auth=bearer_auth,
            timeout=60.0,
        )
    else:
        # SSE mode: Auth handled by middleware, client uses token from request context
        sse_auth = SSEBearerAuth()

        client = httpx.AsyncClient(
            base_url=config.api_base_url,
            auth=sse_auth,
            timeout=60.0,
        )

    # Fetch and patch OpenAPI spec
    spec = await fetch_and_patch_spec(config.openapi_spec_url)

    # Create FastMCP server from OpenAPI spec
    mcp = FastMCP.from_openapi(
        openapi_spec=spec,
        client=client,
        name="Heblo MCP",
        route_maps=get_route_maps(),
    )

    # Add SSE authentication middleware if in SSE mode
    if transport == "sse" and config.sse_auth_enabled:
        token_validator = TokenValidator(
            tenant_id=config.tenant_id,
            audience=config.client_id,
            jwks_cache_ttl=config.jwks_cache_ttl,
        )

        # Wrap the FastMCP app with auth middleware
        # Note: This requires access to the underlying ASGI app
        # FastMCP may need to expose this or we may need to wrap differently
        if hasattr(mcp, 'app'):
            mcp.app = SSEAuthMiddleware(
                mcp.app,
                token_validator,
                bypass_health=True
            )

    return mcp


# Create the default server instance for FastMCP CLI
mcp = None  # Will be initialized when needed


async def create_server_with_health(config: HebloMCPConfig | None = None) -> FastMCP:
    """Create server with health endpoint for SSE mode.

    Args:
        config: Configuration object (defaults to loading from environment)

    Returns:
        Configured FastMCP server instance with health endpoint
    """
    # Create base server
    mcp = await create_server(config)

    # Load config if not provided (for health endpoint)
    if config is None:
        config = HebloMCPConfig()

    # Add health endpoint
    @mcp.tool()
    def health() -> dict:
        """Health check endpoint for Azure Web App.

        Returns:
            Health status information
        """
        return {
            "status": "healthy",
            "version": __version__,
            "transport": config.transport if config else "auto"
        }

    return mcp


async def get_mcp_server() -> FastMCP:
    """Get or create the MCP server instance.

    This is used by the FastMCP CLI and __main__.py entry point.
    """
    global mcp
    if mcp is None:
        mcp = await create_server()
    return mcp
