# Design: Add ManufactureOrder and ManufactureBatch Endpoints

**Date:** 2026-02-25
**Status:** Approved

## Overview

Add manufacturing operations support to HebloMCP by exposing ManufactureOrder and ManufactureBatch endpoints from the Heblo API as MCP tools.

## Motivation

Users need to create, list, and manage manufacturing orders and batch calculations through the MCP interface. These endpoints already exist in the Heblo API OpenAPI spec but are not currently exposed by the MCP server.

## Architecture

Add two new tag groups to the MCP server's route filtering:
- **ManufactureOrder** - 10 endpoints for managing manufacturing orders
- **ManufactureBatch** - 4 endpoints for batch template and calculation operations

This increases total exposed tools from 38 to 52+ across 8 tag groups (previously 6).

### Approach

**Simple Tag Inclusion** - Add ManufactureOrder and ManufactureBatch tags to RouteMap, letting FastMCP auto-generate tool names and descriptions from the OpenAPI spec. Custom hints can be added later to TOOL_METADATA as usage patterns emerge.

## Components

### Files Modified

**`src/heblo_mcp/routes.py`:**
- Add two RouteMap entries for new tags
- Update docstring to reflect new counts (52+ tools, 8 tag groups)

No new files needed. Existing authentication, spec fetching, and server setup remain unchanged.

## Endpoints Added

### ManufactureOrder (10 endpoints)

- `GET /api/ManufactureOrder` - List manufacture orders
- `POST /api/ManufactureOrder` - Create manufacture order
- `GET /api/ManufactureOrder/{id}` - Get specific order
- `PUT /api/ManufactureOrder/{id}` - Update order
- `PATCH /api/ManufactureOrder/{id}/status` - Update order status
- `POST /api/ManufactureOrder/{id}/confirm-semi-product` - Confirm semi-product
- `POST /api/ManufactureOrder/{id}/confirm-products` - Confirm products
- `GET /api/ManufactureOrder/calendar` - Get calendar view
- `POST /api/ManufactureOrder/{id}/duplicate` - Duplicate order
- `GET /api/ManufactureOrder/responsible-persons` - Get responsible persons
- `POST /api/ManufactureOrder/{id}/resolve-manual-action` - Resolve manual action
- `PATCH /api/ManufactureOrder/{id}/schedule` - Update schedule

### ManufactureBatch (4 endpoints)

- `GET /api/manufacture-batch/template/{productCode}` - Get batch template
- `POST /api/manufacture-batch/calculate-by-size` - Calculate batch by size
- `POST /api/manufacture-batch/calculate-by-ingredient` - Calculate batch by ingredient
- `POST /api/manufacture-batch/calculate-batch-plan` - Calculate batch plan

## Data Flow

1. MCP server starts → fetches OpenAPI spec from staging URL
2. `get_route_maps()` returns routing rules including new ManufactureOrder/ManufactureBatch tags
3. FastMCP filters spec paths by tags, exposing only matched endpoints as tools
4. AI calls manufacture tools → authenticated requests to Heblo API → responses returned via MCP

## Error Handling

Leverages existing error handling infrastructure:
- Azure AD auth errors (401) handled by `auth.py`
- API errors returned directly from Heblo API through FastMCP
- No manufacture-specific error handling needed initially
- Custom hints can be added to TOOL_METADATA later if patterns emerge

## Testing

- **Manual testing**: Use `fastmcp dev src/heblo_mcp/server.py` to verify new tools appear and are callable
- **Integration test**: Call a simple endpoint like `GET /api/ManufactureOrder` to confirm routing works
- No new automated tests needed (follows existing pattern of tag-based routing)

## Future Enhancements

1. Add TOOL_METADATA entries with helpful hints for key endpoints (e.g., common filters, state values)
2. Document manufacturing workflows in README
3. Add usage examples for common operations

## Implementation Plan

See implementation plan document (created via writing-plans skill).
