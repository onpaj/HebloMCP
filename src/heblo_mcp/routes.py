"""Route filtering and metadata for HebloMCP server."""

from fastmcp.server.providers.openapi.routing import MCPType, RouteMap

# Mapping of (method, path) to {operationId, summary}
# This metadata is injected into the OpenAPI spec since Heblo API lacks these fields
TOOL_METADATA = {
    # Analytics (5 endpoints)
    ("GET", "/api/Analytics/product-margin-summary"): {
        "operationId": "analytics_product_margin_summary",
        "summary": "Get product margin summary with profit calculations",
    },
    ("GET", "/api/Analytics/margin-analysis"): {
        "operationId": "analytics_margin_analysis",
        "summary": "Analyze profit margins across products and time periods",
    },
    ("GET", "/api/Analytics/margin-report"): {
        "operationId": "analytics_margin_report",
        "summary": "Generate detailed margin report with breakdowns",
    },
    ("GET", "/api/Analytics/invoice-import-statistics"): {
        "operationId": "analytics_invoice_import_stats",
        "summary": "Get statistics on invoice import operations",
    },
    ("GET", "/api/Analytics/bank-statement-import-statistics"): {
        "operationId": "analytics_bank_statement_import_stats",
        "summary": "Get statistics on bank statement import operations",
    },
    # Catalog (15 endpoints)
    ("GET", "/api/Catalog"): {
        "operationId": "catalog_list",
        "summary": "List all catalog products with filters and pagination",
    },
    ("GET", "/api/Catalog/{productCode}"): {
        "operationId": "catalog_detail",
        "summary": "Get detailed information about a specific product",
    },
    ("GET", "/api/Catalog/{productCode}/composition"): {
        "operationId": "catalog_composition",
        "summary": "Get product composition and material breakdown",
    },
    ("GET", "/api/Catalog/materials-for-purchase"): {
        "operationId": "catalog_materials_for_purchase",
        "summary": "List materials that need to be purchased",
    },
    ("GET", "/api/Catalog/autocomplete"): {
        "operationId": "catalog_autocomplete",
        "summary": "Search catalog with autocomplete suggestions",
    },
    ("GET", "/api/Catalog/{productCode}/manufacture-difficulty"): {
        "operationId": "catalog_manufacture_difficulty_get",
        "summary": "Get manufacturing difficulty rating for a product",
    },
    ("POST", "/api/Catalog/manufacture-difficulty"): {
        "operationId": "catalog_manufacture_difficulty_create",
        "summary": "Create manufacturing difficulty rating",
    },
    ("PUT", "/api/Catalog/manufacture-difficulty/{id}"): {
        "operationId": "catalog_manufacture_difficulty_update",
        "summary": "Update manufacturing difficulty rating",
    },
    ("DELETE", "/api/Catalog/manufacture-difficulty/{id}"): {
        "operationId": "catalog_manufacture_difficulty_delete",
        "summary": "Delete manufacturing difficulty rating",
    },
    ("GET", "/api/Catalog/{productCode}/usage"): {
        "operationId": "catalog_product_usage",
        "summary": "Get product usage history and statistics",
    },
    ("GET", "/api/Catalog/warehouse-statistics"): {
        "operationId": "catalog_warehouse_statistics",
        "summary": "Get warehouse inventory statistics",
    },
    ("POST", "/api/Catalog/recalculate-product-weight"): {
        "operationId": "catalog_recalculate_all_weights",
        "summary": "Recalculate weights for all products",
    },
    ("POST", "/api/Catalog/recalculate-product-weight/{productCode}"): {
        "operationId": "catalog_recalculate_product_weight",
        "summary": "Recalculate weight for a specific product",
    },
    ("POST", "/api/Catalog/stock-taking/enqueue"): {
        "operationId": "catalog_stock_taking_enqueue",
        "summary": "Enqueue stock-taking job for processing",
    },
    ("GET", "/api/Catalog/stock-taking/job-status/{jobId}"): {
        "operationId": "catalog_stock_taking_job_status",
        "summary": "Check status of stock-taking job",
    },
    # Invoices (6 endpoints)
    ("GET", "/api/invoices"): {
        "operationId": "invoices_list",
        "summary": "List all invoices with filters and pagination",
    },
    ("GET", "/api/invoices/{id}"): {
        "operationId": "invoices_detail",
        "summary": "Get detailed information about a specific invoice",
    },
    ("GET", "/api/invoices/stats"): {
        "operationId": "invoices_statistics",
        "summary": "Get invoice statistics and summaries",
    },
    ("POST", "/api/invoices/import/enqueue-async"): {
        "operationId": "invoices_import_enqueue",
        "summary": "Enqueue invoice import job for async processing",
    },
    ("GET", "/api/invoices/import/job-status/{jobId}"): {
        "operationId": "invoices_import_job_status",
        "summary": "Check status of invoice import job",
    },
    ("GET", "/api/invoices/import/running-jobs"): {
        "operationId": "invoices_import_running_jobs",
        "summary": "List all currently running invoice import jobs",
    },
    # IssuedInvoices (3 endpoints)
    ("GET", "/api/IssuedInvoices"): {
        "operationId": "issued_invoices_list",
        "summary": "List all issued invoices with filters",
    },
    ("GET", "/api/IssuedInvoices/{id}"): {
        "operationId": "issued_invoices_detail",
        "summary": "Get detailed information about a specific issued invoice",
    },
    ("GET", "/api/IssuedInvoices/sync-stats"): {
        "operationId": "issued_invoices_sync_stats",
        "summary": "Get synchronization statistics for issued invoices",
    },
    # BankStatements (3 endpoints)
    ("POST", "/api/bank-statements/import"): {
        "operationId": "bank_statements_import",
        "summary": "Import bank statements from file or data",
    },
    ("GET", "/api/bank-statements"): {
        "operationId": "bank_statements_list",
        "summary": "List all bank statements with filters",
    },
    ("GET", "/api/bank-statements/{id}"): {
        "operationId": "bank_statements_detail",
        "summary": "Get detailed information about a specific bank statement",
    },
    # Dashboard (6 endpoints)
    ("GET", "/api/Dashboard/tiles"): {
        "operationId": "dashboard_tiles",
        "summary": "Get all available dashboard tiles",
    },
    ("GET", "/api/Dashboard/settings"): {
        "operationId": "dashboard_settings_get",
        "summary": "Get current dashboard settings and configuration",
    },
    ("POST", "/api/Dashboard/settings"): {
        "operationId": "dashboard_settings_update",
        "summary": "Update dashboard settings and configuration",
    },
    ("GET", "/api/Dashboard/data"): {
        "operationId": "dashboard_data",
        "summary": "Get dashboard data for all enabled tiles",
    },
    ("POST", "/api/Dashboard/tiles/{tileId}/enable"): {
        "operationId": "dashboard_tile_enable",
        "summary": "Enable a specific dashboard tile",
    },
    ("POST", "/api/Dashboard/tiles/{tileId}/disable"): {
        "operationId": "dashboard_tile_disable",
        "summary": "Disable a specific dashboard tile",
    },
}


def get_route_maps() -> list[RouteMap]:
    """Get route filtering rules for FastMCP.

    Includes only curated endpoints from 6 tag groups:
    - Analytics (5 endpoints)
    - Catalog (15 endpoints)
    - Invoices (6 endpoints)
    - IssuedInvoices (3 endpoints)
    - BankStatements (3 endpoints)
    - Dashboard (6 endpoints)

    Total: 38 tools exposed via MCP.
    """
    return [
        # Include specific tag groups as TOOL
        RouteMap(tags={"Analytics"}, mcp_type=MCPType.TOOL),
        RouteMap(tags={"Catalog"}, mcp_type=MCPType.TOOL),
        RouteMap(tags={"Invoices"}, mcp_type=MCPType.TOOL),
        RouteMap(tags={"IssuedInvoices"}, mcp_type=MCPType.TOOL),
        RouteMap(tags={"BankStatements"}, mcp_type=MCPType.TOOL),
        RouteMap(tags={"Dashboard"}, mcp_type=MCPType.TOOL),
        # Exclude everything else (catch-all pattern)
        RouteMap(pattern=".*", mcp_type=MCPType.EXCLUDE),
    ]
