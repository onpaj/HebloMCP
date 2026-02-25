# Add ManufactureOrder and ManufactureBatch Endpoints Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expose ManufactureOrder and ManufactureBatch API endpoints as MCP tools

**Architecture:** Add two RouteMap entries to include ManufactureOrder and ManufactureBatch tags, allowing FastMCP to auto-discover and expose 14+ manufacturing endpoints as MCP tools.

**Tech Stack:** FastMCP, Python 3.12+, pytest

---

## Task 1: Update Route Tests for New Tags

**Files:**
- Modify: `tests/unit/test_routes.py:85`

**Step 1: Write failing test for new route count**

Update the route count assertion to expect 9 route maps (8 included tags + 1 exclude):

```python
def test_get_route_maps():
    """Test that route maps are correctly configured."""
    route_maps = get_route_maps()

    assert isinstance(route_maps, list)
    assert len(route_maps) == 9  # 8 included tag groups + 1 exclude rule

    # Check that all required tags are included
    required_tags = {
        "Analytics",
        "Catalog",
        "Invoices",
        "IssuedInvoices",
        "BankStatements",
        "Dashboard",
        "ManufactureOrder",
        "ManufactureBatch",
    }

    included_tags = set()
    for route_map in route_maps:
        if hasattr(route_map, "tags") and route_map.tags:
            included_tags.update(route_map.tags)

    assert required_tags.issubset(included_tags)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_routes.py::test_get_route_maps -v`

Expected output:
```
FAILED tests/unit/test_routes.py::test_get_route_maps - AssertionError: assert 7 == 9
```

**Step 3: Commit the failing test**

```bash
git add tests/unit/test_routes.py
git commit -m "test: add failing test for manufacture tags in routes"
```

---

## Task 2: Add ManufactureOrder and ManufactureBatch Tags to Routes

**Files:**
- Modify: `src/heblo_mcp/routes.py:141-164`

**Step 1: Add new RouteMap entries**

Add ManufactureOrder and ManufactureBatch after Dashboard and before the exclude rule:

```python
def get_route_maps() -> list[RouteMap]:
    """Get route filtering rules for FastMCP.

    Includes only curated endpoints from 8 tag groups:
    - Analytics (5 endpoints)
    - Catalog (15 endpoints)
    - Invoices (6 endpoints)
    - IssuedInvoices (3 endpoints)
    - BankStatements (3 endpoints)
    - Dashboard (6 endpoints)
    - ManufactureOrder (10 endpoints)
    - ManufactureBatch (4 endpoints)

    Total: 52+ tools exposed via MCP.
    """
    return [
        # Include specific tag groups as TOOL
        RouteMap(tags={"Analytics"}, mcp_type=MCPType.TOOL),
        RouteMap(tags={"Catalog"}, mcp_type=MCPType.TOOL),
        RouteMap(tags={"Invoices"}, mcp_type=MCPType.TOOL),
        RouteMap(tags={"IssuedInvoices"}, mcp_type=MCPType.TOOL),
        RouteMap(tags={"BankStatements"}, mcp_type=MCPType.TOOL),
        RouteMap(tags={"Dashboard"}, mcp_type=MCPType.TOOL),
        RouteMap(tags={"ManufactureOrder"}, mcp_type=MCPType.TOOL),
        RouteMap(tags={"ManufactureBatch"}, mcp_type=MCPType.TOOL),
        # Exclude everything else (catch-all pattern)
        RouteMap(pattern=".*", mcp_type=MCPType.EXCLUDE),
    ]
```

**Step 2: Run test to verify it passes**

Run: `pytest tests/unit/test_routes.py::test_get_route_maps -v`

Expected output:
```
PASSED tests/unit/test_routes.py::test_get_route_maps
```

**Step 3: Run all route tests**

Run: `pytest tests/unit/test_routes.py -v`

Expected: All tests pass

**Step 4: Commit the implementation**

```bash
git add src/heblo_mcp/routes.py
git commit -m "feat: add ManufactureOrder and ManufactureBatch endpoints

Expose 14+ manufacturing endpoints as MCP tools:
- ManufactureOrder: 10 endpoints for order management
- ManufactureBatch: 4 endpoints for batch calculations

Total tools increased from 38 to 52+."
```

---

## Task 3: Manual Testing

**Step 1: Start FastMCP dev server**

Run: `fastmcp dev src/heblo_mcp/server.py`

Expected: Server starts without errors

**Step 2: Verify new tools appear**

In the FastMCP inspector, check that manufacture tools are listed:
- Look for tools starting with `manufacture_order_*`
- Look for tools starting with `manufacture_batch_*`
- Verify ~52+ total tools are available

**Step 3: Test a simple endpoint (optional)**

If authenticated, try calling:
- Tool: `manufacture_order_list` (GET /api/ManufactureOrder)
- Verify it returns data or appropriate auth/validation errors

---

## Task 4: Update Documentation

**Files:**
- Modify: `README.md:8` (tool count)
- Modify: `README.md:135-173` (add manufacture sections)

**Step 1: Update tool count in header**

Change line 8 from:
```markdown
- 🛠️ **38 Curated Tools** - Analytics, Catalog, Invoices, IssuedInvoices, BankStatements, Dashboard
```

To:
```markdown
- 🛠️ **52+ Curated Tools** - Analytics, Catalog, Invoices, IssuedInvoices, BankStatements, Dashboard, ManufactureOrder, ManufactureBatch
```

**Step 2: Add manufacture tools section**

After the Dashboard section (around line 173), add:

```markdown
### ManufactureOrder (10 tools)
- `manufacture_order_list` - List manufacture orders with filters
- `manufacture_order_create` - Create new manufacture order
- `manufacture_order_detail` - Get detailed information about a specific order
- `manufacture_order_update` - Update existing manufacture order
- `manufacture_order_status_update` - Update order status
- `manufacture_order_confirm_semi_product` - Confirm semi-product in order
- `manufacture_order_confirm_products` - Confirm products in order
- `manufacture_order_calendar` - Get calendar view of orders
- `manufacture_order_duplicate` - Duplicate an existing order
- `manufacture_order_responsible_persons` - Get list of responsible persons

### ManufactureBatch (4 tools)
- `manufacture_batch_template` - Get batch template for a product
- `manufacture_batch_calculate_by_size` - Calculate batch quantities by size
- `manufacture_batch_calculate_by_ingredient` - Calculate batch quantities by ingredient
- `manufacture_batch_calculate_batch_plan` - Calculate complete batch plan
```

**Step 3: Commit documentation updates**

```bash
git add README.md
git commit -m "docs: add ManufactureOrder and ManufactureBatch to README"
```

---

## Task 5: Final Verification

**Step 1: Run all tests**

Run: `pytest tests/ -v`

Expected: All tests pass

**Step 2: Verify git status is clean**

Run: `git status`

Expected: Clean working tree (all changes committed)

**Step 3: Review commit history**

Run: `git log --oneline -5`

Expected: See 4 commits (test, implementation, docs, design doc)

---

## Completion

Implementation complete! The MCP server now exposes 52+ tools including manufacturing operations for orders and batch calculations.

**Next Steps (Future):**
1. Add TOOL_METADATA entries with helpful hints for key endpoints
2. Document common manufacturing workflows
3. Add usage examples for typical operations
