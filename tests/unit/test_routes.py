"""Unit tests for routes module."""


from heblo_mcp.routes import TOOL_METADATA, get_route_maps


def test_tool_metadata_structure():
    """Test that TOOL_METADATA has correct structure."""
    assert isinstance(TOOL_METADATA, dict)
    assert len(TOOL_METADATA) >= 31  # Should have at least 31 tools

    # Check each entry has required fields
    for key, metadata in TOOL_METADATA.items():
        # Key should be (method, path) tuple
        assert isinstance(key, tuple)
        assert len(key) == 2
        method, path = key
        assert method in {"GET", "POST", "PUT", "DELETE"}
        assert path.startswith("/api/")

        # Metadata should have operationId and summary
        assert "operationId" in metadata
        assert "summary" in metadata
        assert isinstance(metadata["operationId"], str)
        assert isinstance(metadata["summary"], str)


def test_tool_metadata_hints():
    """Test that tool metadata contains helpful hints."""
    # Catalog list should have ProductTypes hint
    catalog_list = TOOL_METADATA[("GET", "/api/Catalog")]
    assert "HINT" in catalog_list["summary"]
    assert "ProductTypes" in catalog_list["summary"]
    assert "Product" in catalog_list["summary"]
    assert "SemiProduct" in catalog_list["summary"]

    # Catalog composition should have composition-specific hints
    catalog_comp = TOOL_METADATA[("GET", "/api/Catalog/{productCode}/composition")]
    assert "HINT" in catalog_comp["summary"]
    assert "Product" in catalog_comp["summary"]
    assert "SemiProduct" in catalog_comp["summary"]
    assert "'M'" in catalog_comp["summary"]  # Mention codes ending with M

    # Autocomplete should have filter hints
    autocomplete = TOOL_METADATA[("GET", "/api/Catalog/autocomplete")]
    assert "HINT" in autocomplete["summary"]
    assert "productTypes" in autocomplete["summary"]


def test_tool_metadata_product_type_guidance():
    """Test that tools with product codes have proper type guidance."""
    tools_with_product_codes = [
        ("GET", "/api/Catalog/{productCode}"),
        ("GET", "/api/Catalog/{productCode}/composition"),
        ("GET", "/api/Catalog/{productCode}/manufacture-difficulty"),
        ("GET", "/api/Catalog/{productCode}/usage"),
        ("POST", "/api/Catalog/recalculate-product-weight/{productCode}"),
    ]

    for method, path in tools_with_product_codes:
        metadata = TOOL_METADATA[(method, path)]
        summary = metadata["summary"]

        # Should mention product types or code patterns
        assert any(
            keyword in summary for keyword in ["Product", "SemiProduct", "HINT", "type"]
        ), f"Missing product type guidance in {path}"


def test_tool_metadata_materials_guidance():
    """Test that material-related tools have proper guidance."""
    materials_tool = TOOL_METADATA[("GET", "/api/Catalog/materials-for-purchase")]

    assert "HINT" in materials_tool["summary"]
    assert "Material" in materials_tool["summary"] or "Goods" in materials_tool["summary"]


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


def test_tool_metadata_operation_ids_unique():
    """Test that all operation IDs are unique."""
    operation_ids = [metadata["operationId"] for metadata in TOOL_METADATA.values()]

    assert len(operation_ids) == len(set(operation_ids)), "Duplicate operation IDs found"


def test_tool_metadata_coverage_by_category():
    """Test that we have tools in each expected category."""
    analytics_count = sum(
        1 for (method, path) in TOOL_METADATA.keys() if path.startswith("/api/Analytics")
    )
    catalog_count = sum(
        1 for (method, path) in TOOL_METADATA.keys() if path.startswith("/api/Catalog")
    )
    invoices_count = sum(
        1 for (method, path) in TOOL_METADATA.keys() if path.startswith("/api/invoices")
    )
    issued_invoices_count = sum(
        1 for (method, path) in TOOL_METADATA.keys() if path.startswith("/api/IssuedInvoices")
    )
    bank_statements_count = sum(
        1 for (method, path) in TOOL_METADATA.keys() if path.startswith("/api/bank-statements")
    )
    dashboard_count = sum(
        1 for (method, path) in TOOL_METADATA.keys() if path.startswith("/api/Dashboard")
    )

    # Verify we have tools in each category
    assert analytics_count >= 3, f"Expected at least 3 analytics tools, got {analytics_count}"
    assert catalog_count >= 10, f"Expected at least 10 catalog tools, got {catalog_count}"
    assert invoices_count >= 3, f"Expected at least 3 invoice tools, got {invoices_count}"
    assert (
        issued_invoices_count >= 2
    ), f"Expected at least 2 issued invoice tools, got {issued_invoices_count}"
    assert (
        bank_statements_count >= 2
    ), f"Expected at least 2 bank statement tools, got {bank_statements_count}"
    assert dashboard_count >= 3, f"Expected at least 3 dashboard tools, got {dashboard_count}"
