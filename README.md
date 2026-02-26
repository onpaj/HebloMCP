# HebloMCP

**MCP server for Heblo application** - Exposes Heblo API endpoints (analytics, catalog, invoices, bank statements, dashboards) as MCP tools for AI assistant integration.

## Features

- 🔐 **Azure AD Authentication** - Secure device code flow with token caching
- 🛠️ **52+ Curated Tools** - Analytics, Catalog, Invoices, IssuedInvoices, BankStatements, Dashboard, ManufactureOrder, ManufactureBatch
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

HebloMCP exposes 52+ tools across 8 categories:

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

### Run Server (stdio mode - local)

```bash
docker run -i \
  -v heblo-mcp-cache:/home/heblo/.config/heblo-mcp \
  -e HEBLO_TENANT_ID=your-tenant-id \
  -e HEBLO_CLIENT_ID=your-client-id \
  heblo-mcp
```

### Run Server (SSE mode - cloud/remote)

```bash
docker run -p 8000:8000 \
  -v heblo-mcp-cache:/home/heblo/.config/heblo-mcp \
  -e HEBLO_TENANT_ID=your-tenant-id \
  -e HEBLO_CLIENT_ID=your-client-id \
  heblo-mcp serve-sse
```

## Cloud Deployment

### Azure Web App Deployment

HebloMCP can be deployed to Azure Web App for remote access via SSE transport.

**Prerequisites:**
- Azure subscription
- DockerHub account
- GitHub repository

**Setup:**
See [Azure Setup Guide](docs/AZURE_SETUP.md) for complete instructions.

**Quick Start:**
1. Create Azure Service Principal
2. Configure GitHub Secrets
3. Push to `main` branch
4. GitHub Actions automatically deploys to Azure

**Access:**
- Root endpoint (SSE): `https://heblo-mcp.azurewebsites.net/`
- SSE endpoint: `https://heblo-mcp.azurewebsites.net`

**Monitoring:**
```bash
az webapp log tail --resource-group rgHeblo --name heblo-mcp
```

### Deployment Pipeline Configuration

The GitHub Actions workflow (`.github/workflows/deploy.yml`) requires specific secrets to be configured.

#### GitHub Secrets Configuration

Navigate to your repository: **Settings → Secrets and variables → Actions → New repository secret**

**Required Secrets:**

| Secret Name | Description | How to Get |
|------------|-------------|------------|
| `DOCKERHUB_USERNAME` | Your DockerHub username | Your DockerHub account username |
| `DOCKERHUB_TOKEN` | DockerHub access token | Create at [hub.docker.com/settings/security](https://hub.docker.com/settings/security) |
| `AZURE_CLIENT_ID` | Service Principal App ID | From `az ad sp create-for-rbac` output: `clientId` |
| `AZURE_CLIENT_SECRET` | Service Principal secret | From `az ad sp create-for-rbac` output: `clientSecret` |
| `AZURE_TENANT_ID` | Azure tenant ID | From `az ad sp create-for-rbac` output: `tenantId` |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID | From `az ad sp create-for-rbac` output: `subscriptionId` |
| `AZURE_WEBAPP_NAME` | Azure Web App name | Example: `heblo-mcp` |
| `AZURE_RESOURCE_GROUP` | Azure resource group | Example: `rgHeblo` |

**Create Azure Service Principal:**
```bash
az ad sp create-for-rbac \
  --name "sp-heblo-mcp-deploy" \
  --role Contributor \
  --scopes /subscriptions/$(az account show --query id -o tsv)/resourceGroups/rgHeblo \
  --sdk-auth
```

Save the entire JSON output - you'll need values from it for the GitHub Secrets above.

#### Azure App Settings (Runtime Configuration)

These are configured in Azure Portal or via Azure CLI for the running application:

**Required App Settings:**

| Setting Name | Description | Example Value |
|-------------|-------------|---------------|
| `HEBLO_TENANT_ID` | Your Heblo tenant ID | From Azure AD app registration |
| `HEBLO_CLIENT_ID` | Your Heblo client ID | From Azure AD app registration |
| `HEBLO_TRANSPORT` | Transport mode for cloud | `sse` |
| `WEBSITES_PORT` | Port for Azure Web App | `8000` |

**Configure via Azure CLI:**
```bash
az webapp config appsettings set \
  --resource-group rgHeblo \
  --name heblo-mcp \
  --settings \
    HEBLO_TENANT_ID="your-tenant-id" \
    HEBLO_CLIENT_ID="your-client-id" \
    HEBLO_TRANSPORT="sse" \
    WEBSITES_PORT="8000"
```

#### Deployment Workflow

Once secrets are configured, the deployment is automatic:

1. **Push to main** triggers the workflow
2. **Tests run** - All 51 tests must pass
3. **Docker build** - Multi-stage build creates optimized image
4. **Push to DockerHub** - Image tagged with `latest`, `sha-<commit>`, and version
5. **Deploy to Azure** - Azure pulls the new image and deploys
6. **Health check** - Workflow verifies deployment succeeded

**Monitor deployment:**
- GitHub Actions tab shows workflow progress
- Azure Portal shows deployment status
- Use deployment checklist: [docs/DEPLOYMENT_CHECKLIST.md](docs/DEPLOYMENT_CHECKLIST.md)

For detailed deployment steps, see:
- [Azure Setup Guide](docs/AZURE_SETUP.md)
- [Deployment Checklist](docs/DEPLOYMENT_CHECKLIST.md)

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
