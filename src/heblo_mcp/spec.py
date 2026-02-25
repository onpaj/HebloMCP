"""OpenAPI specification fetching and patching for HebloMCP."""

import httpx

from heblo_mcp.routes import TOOL_METADATA


async def fetch_and_patch_spec(url: str) -> dict:
    """Fetch OpenAPI spec from URL and inject metadata.

    Args:
        url: URL to fetch the OpenAPI spec from (usually staging)

    Returns:
        Patched OpenAPI spec with operationId and summary fields injected
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        spec = response.json()

    inject_metadata(spec)
    return spec


def inject_metadata(spec: dict) -> None:
    """Inject operationId and summary from TOOL_METADATA into OpenAPI spec.

    The Heblo API spec lacks operationId and summary fields, which are required
    for FastMCP to generate clean tool names and descriptions. This function
    patches the spec in-place by injecting metadata from TOOL_METADATA.

    Args:
        spec: OpenAPI specification dict (modified in-place)
    """
    if "paths" not in spec:
        return

    for path, path_item in spec["paths"].items():
        for method, operation in path_item.items():
            # Skip non-operation keys like 'parameters', 'summary', etc.
            if method.upper() not in {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}:
                continue

            if not isinstance(operation, dict):
                continue

            # Look up metadata for this (method, path) combination
            metadata_key = (method.upper(), path)
            if metadata_key in TOOL_METADATA:
                metadata = TOOL_METADATA[metadata_key]

                # Inject operationId if missing
                if "operationId" not in operation:
                    operation["operationId"] = metadata["operationId"]

                # Inject summary if missing
                if "summary" not in operation:
                    operation["summary"] = metadata["summary"]
