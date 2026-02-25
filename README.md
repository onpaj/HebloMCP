# HebloMCP

**MCP server for Heblo application** - Exposes Heblo API endpoints (analytics, catalog, invoices, bank statements, dashboards) as MCP tools for AI assistant integration.

## Features

- 🔐 **Azure AD Authentication** - Secure device code flow with token caching
- 🛠️ **38 Curated Tools** - Analytics, Catalog, Invoices, IssuedInvoices, BankStatements, Dashboard
- 🚀 **FastMCP Integration** - Built on FastMCP's OpenAPI support
- 📦 **Easy Setup** - One-time login, automatic token renewal
- 🐳 **Docker Support** - Production-ready container image

## Prerequisites

Before using HebloMCP, you need to register an Azure AD application with the Heblo API. Follow these steps:

### Azure AD App Registration Setup

1. **Navigate to Azure Portal**
   - Go to [Azure Portal](https://portal.azure.com)
   - Select **Azure Active Directory** > **App Registrations**

2. **Create New Registration**
   - Click **New registration**
   - **Name**: `Heblo MCP` (or any name you prefer)
   - **Supported account types**: Single tenant (your organization only)
   - **Redirect URI**: Leave blank
   - Click **Register**

3. **Enable Public Client Flows**
   - Go to **Authentication** tab
   - Scroll to **Advanced settings** > **Allow public client flows**
   - Toggle **Enable the following mobile and desktop flows** to **Yes**
   - Click **Save**

4. **Add API Permissions**
   - Go to **API permissions** tab
   - Click **Add a permission** > **My APIs**
   - Select **Heblo API** (Client ID: `8b34be89-cef4-445a-929a-bc1a21dce0cb`)
   - Select **Delegated permissions**
   - Check **access_as_user**
   - Click **Add permissions**

5. **Grant Admin Consent**
   - Click **Grant admin consent for [Your Organization]**
   - Confirm by clicking **Yes**

6. **Note Your IDs**
   - Copy **Application (client) ID** from the Overview page
   - Copy **Directory (tenant) ID** from the Overview page
   - You'll need these for the `.env` file

## Installation

### Option 1: Install from Source

```bash
# Clone the repository
git clone https://github.com/yourusername/heblo-mcp.git
cd heblo-mcp

# Create virtual environment (Python 3.12+ required)
python3.12 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in editable mode
pip install -e .
```

### Option 2: Install from PyPI (when published)

```bash
pip install heblo-mcp
```

## Configuration

Create a `.env` file in your project directory or set environment variables:

```bash
# Required
HEBLO_TENANT_ID=your-tenant-id-here
HEBLO_CLIENT_ID=your-client-id-here

# Optional (defaults shown)
HEBLO_API_SCOPE=api://8b34be89-cef4-445a-929a-bc1a21dce0cb/access_as_user
HEBLO_API_BASE_URL=https://heblo.anela.cz
HEBLO_OPENAPI_SPEC_URL=https://heblo.stg.anela.cz/swagger/v1/swagger.json
HEBLO_TOKEN_CACHE_PATH=~/.config/heblo-mcp/token_cache.json
```

## Usage

### 1. Authenticate

Run the login command once to authenticate with Azure AD:

```bash
heblo-mcp login
```

This will:
- Display a device code and URL
- Open your browser to authenticate
- Cache your token to `~/.config/heblo-mcp/token_cache.json`
- Automatically renew tokens on subsequent runs

### 2. Configure Claude Desktop

Add HebloMCP to your Claude Desktop configuration:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "heblo": {
      "command": "heblo-mcp",
      "env": {
        "HEBLO_TENANT_ID": "your-tenant-id",
        "HEBLO_CLIENT_ID": "your-client-id"
      }
    }
  }
}
```

### 3. Use with Other MCP Hosts

HebloMCP works with any MCP-compatible host. Configure according to your host's documentation.

## Available Tools

HebloMCP exposes 38 tools across 6 categories:

### Analytics (5 tools)
- `analytics_product_margin_summary` - Get product margin summary with profit calculations
- `analytics_margin_analysis` - Analyze profit margins across products and time periods
- `analytics_margin_report` - Generate detailed margin report with breakdowns
- `analytics_invoice_import_stats` - Get statistics on invoice import operations
- `analytics_bank_statement_import_stats` - Get statistics on bank statement import operations

### Catalog (15 tools)
- `catalog_list` - List all catalog products with filters and pagination
- `catalog_detail` - Get detailed information about a specific product
- `catalog_composition` - Get product composition and material breakdown
- `catalog_materials_for_purchase` - List materials that need to be purchased
- `catalog_autocomplete` - Search catalog with autocomplete suggestions
- And 10 more catalog management tools...

### Invoices (6 tools)
- `invoices_list` - List all invoices with filters and pagination
- `invoices_detail` - Get detailed information about a specific invoice
- `invoices_statistics` - Get invoice statistics and summaries
- And 3 more invoice management tools...

### IssuedInvoices (3 tools)
- `issued_invoices_list` - List all issued invoices with filters
- `issued_invoices_detail` - Get detailed information about a specific issued invoice
- `issued_invoices_sync_stats` - Get synchronization statistics for issued invoices

### BankStatements (3 tools)
- `bank_statements_import` - Import bank statements from file or data
- `bank_statements_list` - List all bank statements with filters
- `bank_statements_detail` - Get detailed information about a specific bank statement

### Dashboard (6 tools)
- `dashboard_tiles` - Get all available dashboard tiles
- `dashboard_settings_get` - Get current dashboard settings and configuration
- `dashboard_data` - Get dashboard data for all enabled tiles
- And 3 more dashboard management tools...

## Docker Usage

### Build Image

```bash
docker build -t heblo-mcp .
```

### Run Login

```bash
docker run -it --rm \
  -v heblo-mcp-cache:/home/heblo/.config/heblo-mcp \
  -e HEBLO_TENANT_ID=your-tenant-id \
  -e HEBLO_CLIENT_ID=your-client-id \
  heblo-mcp login
```

### Run Server

```bash
docker run -i \
  -v heblo-mcp-cache:/home/heblo/.config/heblo-mcp \
  -e HEBLO_TENANT_ID=your-tenant-id \
  -e HEBLO_CLIENT_ID=your-client-id \
  heblo-mcp
```

## Development

### Run Tests

```bash
pytest
```

### Code Formatting

```bash
black src/
ruff check src/
```

### Test with FastMCP Inspector

```bash
fastmcp dev src/heblo_mcp/server.py
```

## Troubleshooting

### "No cached authentication token found"

Run `heblo-mcp login` to authenticate first.

### "Authentication failed"

- Verify your `HEBLO_TENANT_ID` and `HEBLO_CLIENT_ID` are correct
- Ensure the Azure AD app has the `access_as_user` permission
- Check that admin consent was granted

### "Module not found" errors

Ensure you're using Python 3.12+ and have installed all dependencies:

```bash
pip install -e ".[dev]"
```

### Token expired

HebloMCP automatically renews tokens. If you see 401 errors, try:

```bash
rm ~/.config/heblo-mcp/token_cache.json
heblo-mcp login
```

## Architecture

HebloMCP is built on:

- **FastMCP** - MCP server framework with OpenAPI support
- **MSAL** - Microsoft Authentication Library for device code flow
- **httpx** - Modern HTTP client with authentication support
- **Pydantic** - Configuration management and validation

Key components:

- `config.py` - Environment-based configuration with defaults
- `auth.py` - MSAL device code flow and token caching
- `routes.py` - Route filtering and metadata (38 endpoints)
- `spec.py` - OpenAPI spec fetching and patching
- `server.py` - FastMCP server assembly

## Contributing

Contributions are welcome! Please open an issue or pull request.

## License

MIT License - See LICENSE file for details

## Support

For issues and questions:
- GitHub Issues: https://github.com/yourusername/heblo-mcp/issues
- Heblo Support: Contact your Heblo administrator

---

**Built with ❤️ for the Heblo team**
