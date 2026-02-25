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

    Also fixes validation issues:
    - Makes IssuedInvoiceErrorType enum nullable (API returns null on success)

    Args:
        spec: OpenAPI specification dict (modified in-place)
    """
    if "paths" not in spec:
        return

    # Fix schema validation issues
    fix_schema_validation(spec)

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


def fix_schema_validation(spec: dict) -> None:
    """Fix schema validation issues in the Heblo OpenAPI spec.

    Issues fixed:
    - ErrorCodes enum: Make nullable (API returns null on success, but enum has 87 error values)
    - IssuedInvoiceErrorType enum: Make nullable (API returns null when no error)
    - DateOnly schema: Change from object to string (API returns "2026-08-31", not {year, month, day})

    Args:
        spec: OpenAPI specification dict (modified in-place)
    """
    schemas = spec.get("components", {}).get("schemas", {})

    # Fix ErrorCodes enum - THE BIG ONE (87 error codes)
    # This is used by ALL response schemas (105+ schemas have errorCode field)
    # When API succeeds, errorCode is null, but validation expects one of 87 values
    if "ErrorCodes" in schemas:
        error_codes_schema = schemas["ErrorCodes"]
        # Add null as a valid enum value
        if "enum" in error_codes_schema:
            if None not in error_codes_schema["enum"] and "null" not in error_codes_schema["enum"]:
                error_codes_schema["enum"].append(None)
        # Mark as nullable
        error_codes_schema["nullable"] = True

    # Fix IssuedInvoiceErrorType enum - add nullable
    if "IssuedInvoiceErrorType" in schemas:
        error_type_schema = schemas["IssuedInvoiceErrorType"]
        # Add null as a valid enum value
        if "enum" in error_type_schema:
            if None not in error_type_schema["enum"] and "null" not in error_type_schema["enum"]:
                error_type_schema["enum"].append(None)
        # Mark as nullable
        error_type_schema["nullable"] = True

    # Fix DateOnly schema - API returns string "2026-08-31" not object {year, month, day}
    if "DateOnly" in schemas:
        # Replace the object schema with a string schema
        schemas["DateOnly"] = {
            "type": "string",
            "format": "date",
            "description": "Date in ISO 8601 format (YYYY-MM-DD)",
        }
