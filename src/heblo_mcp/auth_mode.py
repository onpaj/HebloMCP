"""Transport mode detection for HebloMCP server."""

from heblo_mcp.config import HebloMCPConfig


def detect_transport_mode(config: HebloMCPConfig) -> str:
    """Detect the transport mode from configuration.

    Args:
        config: HebloMCP configuration

    Returns:
        "stdio" or "sse"
    """
    if config.transport in ("stdio", "sse"):
        return config.transport

    # Auto mode: default to stdio for safety
    # In production, you might detect from environment or process info
    return "stdio"
