"""HebloMCP server creation and configuration."""

import httpx
from fastmcp import FastMCP

from heblo_mcp.auth import HebloAuth, MSALBearerAuth
from heblo_mcp.config import HebloMCPConfig
from heblo_mcp.routes import get_route_maps
from heblo_mcp.spec import fetch_and_patch_spec


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

    # Set up authentication
    auth = HebloAuth(
        tenant_id=config.tenant_id,
        client_id=config.client_id,
        scope=config.api_scope,
        cache_path=config.token_cache_path,
    )

    # Create httpx auth wrapper
    bearer_auth = MSALBearerAuth(auth)

    # Create HTTP client with authentication
    client = httpx.AsyncClient(
        base_url=config.api_base_url,
        auth=bearer_auth,
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

    # Add health endpoint
    @mcp.tool()
    def health() -> dict:
        """Health check endpoint for Azure Web App.

        Returns:
            Health status information
        """
        return {
            "status": "healthy",
            "version": "0.1.0",
            "transport": "sse"
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
