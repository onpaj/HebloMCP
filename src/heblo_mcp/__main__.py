"""CLI entry point for HebloMCP server."""

import argparse
import sys

from heblo_mcp.auth import HebloAuth
from heblo_mcp.config import HebloMCPConfig


def login_command():
    """Execute the login command to authenticate with Azure AD."""
    try:
        # Load configuration
        config = HebloMCPConfig()

        # Create auth handler
        auth = HebloAuth(
            tenant_id=config.tenant_id,
            client_id=config.client_id,
            scope=config.api_scope,
            cache_path=config.token_cache_path,
        )

        # Perform device code authentication
        result = auth.login()

        # Show success message
        print("\n✅ Authentication successful!")
        print(f"Token cached to: {config.token_cache_path}")
        print("\nYou can now use HebloMCP with Claude Desktop or other MCP hosts.")

        return 0

    except Exception as e:
        print(f"\n❌ Authentication failed: {e}", file=sys.stderr)
        return 1


def start_server():
    """Start the MCP server in stdio mode."""
    # Import FastMCP runtime here to avoid loading during login
    from fastmcp import FastMCP

    from heblo_mcp.server import get_mcp_server

    # FastMCP will handle the async setup and stdio transport
    # We just need to provide the server factory
    import asyncio

    async def run():
        mcp = await get_mcp_server()
        # Run the MCP server with stdio transport
        await mcp.run_stdio_async()

    asyncio.run(run())


def start_server_sse():
    """Start the MCP server in SSE mode for cloud deployment."""
    # Import FastMCP runtime here to avoid loading during login
    import asyncio
    import os

    from heblo_mcp.server import create_server_with_health

    async def run():
        # Create server with health endpoint
        mcp = await create_server_with_health()

        # Run the MCP server with SSE transport on port 8000
        # FastMCP's run() method will automatically use SSE when not in stdio mode
        await mcp.run(
            transport="sse",
            host="0.0.0.0",
            port=int(os.getenv("PORT", "8000"))
        )

    asyncio.run(run())


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="heblo-mcp",
        description="HebloMCP - MCP server for Heblo application",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Login subcommand
    subparsers.add_parser(
        "login",
        help="Authenticate with Azure AD using device code flow",
    )

    # Serve-SSE subcommand
    subparsers.add_parser(
        "serve-sse",
        help="Start MCP server in SSE mode for cloud deployment",
    )

    args = parser.parse_args()

    # Execute command
    if args.command == "login":
        sys.exit(login_command())
    elif args.command == "serve-sse":
        start_server_sse()
    elif args.command is None:
        # Default: start MCP server in stdio mode
        start_server()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
