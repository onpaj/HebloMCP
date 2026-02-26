# Deployment Pipeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deploy HebloMCP to Azure Web App with automated CI/CD via GitHub Actions and DockerHub

**Architecture:** Dual-mode server (stdio + SSE), GitHub Actions pipeline, DockerHub registry, Azure Web App deployment

**Tech Stack:** FastMCP (SSE transport), GitHub Actions, DockerHub, Azure Web App for Containers, Azure Service Principal

---

## Part 1: SSE Transport Support

### Task 1: Add Health Endpoint

**Files:**
- Modify: `src/heblo_mcp/server.py`
- Test: `tests/unit/test_server_health.py`

**Step 1: Write failing test for health endpoint**

Create `tests/unit/test_server_health.py`:

```python
"""Unit tests for server health endpoint."""

import pytest
from fastmcp import FastMCP

from heblo_mcp.server import create_server_with_health


@pytest.mark.asyncio
async def test_health_endpoint_exists(mock_config, mock_msal_app, mock_token_cache, sample_openapi_spec, monkeypatch):
    """Test that health endpoint is registered."""
    # Mock fetch_and_patch_spec
    from unittest.mock import patch

    with patch("heblo_mcp.server.fetch_and_patch_spec") as mock_fetch:
        mock_fetch.return_value = sample_openapi_spec

        # Create server with health endpoint
        mcp = await create_server_with_health(mock_config)

        # Verify health endpoint exists
        # FastMCP with SSE should expose health endpoint
        assert mcp is not None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_server_health.py -v`

Expected: FAIL - `ImportError: cannot import name 'create_server_with_health'`

**Step 3: Add health endpoint to server**

In `src/heblo_mcp/server.py`, add after imports:

```python
from fastmcp.resources import Health
```

Add new function before `create_server`:

```python
async def create_server_with_health(config: HebloMCPConfig | None = None) -> FastMCP:
    """Create server with health endpoint for SSE mode.

    Args:
        config: Configuration object (defaults to loading from environment)

    Returns:
        Configured FastMCP server instance with health endpoint
    """
    # Create base server
    mcp = await create_server(config)

    # Add health endpoint
    @mcp.tool()
    def health() -> dict:
        """Health check endpoint for Azure Web App.

        Returns:
            Health status information
        """
        return {
            "status": "healthy",
            "version": "0.1.0",
            "transport": "sse"
        }

    return mcp
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_server_health.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/heblo_mcp/server.py tests/unit/test_server_health.py
git commit -m "feat: add health endpoint for SSE mode"
```

---

### Task 2: Add SSE Transport Command

**Files:**
- Modify: `src/heblo_mcp/__main__.py`
- Test: `tests/unit/test_cli_serve_sse.py`

**Step 1: Write failing test for serve-sse command**

Create `tests/unit/test_cli_serve_sse.py`:

```python
"""Unit tests for CLI serve-sse command."""

import pytest
from unittest.mock import AsyncMock, Mock, patch


def test_serve_sse_command_exists():
    """Test that serve-sse command is registered."""
    from heblo_mcp.__main__ import main
    import sys

    # Test that serve-sse is recognized
    with patch.object(sys, 'argv', ['heblo-mcp', 'serve-sse']):
        with patch('heblo_mcp.__main__.start_server_sse') as mock_serve:
            with pytest.raises(SystemExit) as exc_info:
                main()

            # Should call serve-sse function
            assert exc_info.value.code == 0 or mock_serve.called


@pytest.mark.asyncio
async def test_start_server_sse_runs():
    """Test that SSE server starts correctly."""
    from heblo_mcp.__main__ import start_server_sse

    with patch('heblo_mcp.__main__.get_mcp_server') as mock_get_server:
        mock_mcp = AsyncMock()
        mock_mcp.run.return_value = None
        mock_get_server.return_value = mock_mcp

        with patch('asyncio.run') as mock_asyncio_run:
            mock_asyncio_run.return_value = None

            # This should not raise
            start_server_sse()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_cli_serve_sse.py -v`

Expected: FAIL - `ImportError: cannot import name 'start_server_sse'`

**Step 3: Add serve-sse command**

In `src/heblo_mcp/__main__.py`, add after `start_server()` function:

```python
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
```

**Step 4: Update main() to handle serve-sse command**

In `src/heblo_mcp/__main__.py`, update the `main()` function:

Add after login subparser:

```python
    # Serve-SSE subcommand
    subparsers.add_parser(
        "serve-sse",
        help="Start MCP server in SSE mode for cloud deployment",
    )
```

Update the command handling section:

```python
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
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/unit/test_cli_serve_sse.py -v`

Expected: PASS (may need to adjust test based on actual behavior)

**Step 6: Commit**

```bash
git add src/heblo_mcp/__main__.py tests/unit/test_cli_serve_sse.py
git commit -m "feat: add serve-sse command for SSE transport"
```

---

### Task 3: Update Dockerfile for SSE Mode

**Files:**
- Modify: `Dockerfile`

**Step 1: Read current Dockerfile**

Check current CMD and EXPOSE directives.

**Step 2: Update Dockerfile**

In `Dockerfile`, update the runtime stage:

After line 42 (before VOLUME), add:

```dockerfile
# Expose port for SSE transport
EXPOSE 8000
```

Update CMD (line 52):

```dockerfile
# Default command - run in SSE mode for cloud deployment
CMD ["serve-sse"]
```

Add health check before LABEL section:

```dockerfile
# Health check for Azure Web App
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=5.0)" || exit 1
```

**Step 3: Test Docker build**

Run: `docker build -t heblo-mcp:test .`

Expected: Build succeeds

**Step 4: Test Docker run locally**

Run:
```bash
docker run --rm -p 8000:8000 \
  -e HEBLO_TENANT_ID=test \
  -e HEBLO_CLIENT_ID=test \
  heblo-mcp:test
```

Expected: Server starts and listens on port 8000 (will fail auth, but should start)

**Step 5: Commit**

```bash
git add Dockerfile
git commit -m "feat: configure Dockerfile for SSE mode deployment"
```

---

## Part 2: GitHub Actions CI/CD Pipeline

### Task 4: Create GitHub Actions Workflow

**Files:**
- Create: `.github/workflows/deploy.yml`

**Step 1: Create workflow directory**

Run: `mkdir -p .github/workflows`

**Step 2: Create deploy.yml**

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Azure

on:
  push:
    branches:
      - main
    paths:
      - 'src/**'
      - 'Dockerfile'
      - 'pyproject.toml'
      - '.github/workflows/deploy.yml'

env:
  DOCKERHUB_IMAGE: ${{ secrets.DOCKERHUB_USERNAME }}/heblo-mcp

jobs:
  build-test-deploy:
    runs-on: ubuntu-latest

    steps:
      # Checkout code
      - name: Checkout repository
        uses: actions/checkout@v4

      # Set up Python
      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      # Install dependencies
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      # Run tests
      - name: Run tests
        run: |
          pytest -v

      # Set up Docker Buildx
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      # Login to DockerHub
      - name: Login to DockerHub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}

      # Extract commit SHA for tagging
      - name: Extract metadata
        id: meta
        run: |
          echo "sha_short=$(git rev-parse --short HEAD)" >> $GITHUB_OUTPUT
          echo "version=0.1.0" >> $GITHUB_OUTPUT

      # Build and push Docker image
      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            ${{ env.DOCKERHUB_IMAGE }}:latest
            ${{ env.DOCKERHUB_IMAGE }}:sha-${{ steps.meta.outputs.sha_short }}
            ${{ env.DOCKERHUB_IMAGE }}:${{ steps.meta.outputs.version }}
          cache-from: type=registry,ref=${{ env.DOCKERHUB_IMAGE }}:latest
          cache-to: type=inline

      # Login to Azure
      - name: Login to Azure
        uses: azure/login@v2
        with:
          creds: |
            {
              "clientId": "${{ secrets.AZURE_CLIENT_ID }}",
              "clientSecret": "${{ secrets.AZURE_CLIENT_SECRET }}",
              "subscriptionId": "${{ secrets.AZURE_SUBSCRIPTION_ID }}",
              "tenantId": "${{ secrets.AZURE_TENANT_ID }}"
            }

      # Deploy to Azure Web App
      - name: Deploy to Azure Web App
        uses: azure/webapps-deploy@v3
        with:
          app-name: ${{ secrets.AZURE_WEBAPP_NAME }}
          images: ${{ env.DOCKERHUB_IMAGE }}:sha-${{ steps.meta.outputs.sha_short }}

      # Verify deployment
      - name: Verify deployment
        run: |
          echo "Waiting for deployment to complete..."
          sleep 30

          # Check health endpoint
          curl -f https://${{ secrets.AZURE_WEBAPP_NAME }}.azurewebsites.net/health || exit 1

          echo "✅ Deployment successful!"
```

**Step 3: Validate YAML syntax**

Run: `yamllint .github/workflows/deploy.yml` (install yamllint if needed)

Or use online validator: https://www.yamllint.com/

Expected: Valid YAML

**Step 4: Commit**

```bash
git add .github/workflows/deploy.yml
git commit -m "ci: add GitHub Actions deployment workflow"
```

---

## Part 3: Azure Infrastructure Setup

### Task 5: Document Azure Setup Steps

**Files:**
- Create: `docs/AZURE_SETUP.md`

**Step 1: Create Azure setup documentation**

Create `docs/AZURE_SETUP.md`:

```markdown
# Azure Infrastructure Setup Guide

This guide walks through setting up Azure infrastructure for HebloMCP deployment.

## Prerequisites

- Azure subscription with active account
- Azure CLI installed: `brew install azure-cli` (macOS) or see [Azure CLI docs](https://learn.microsoft.com/cli/azure/install-azure-cli)
- DockerHub account

## Step 1: Login to Azure

```bash
az login
```

Select your subscription:

```bash
az account set --subscription "Your Subscription Name"
```

Verify:

```bash
az account show
```

## Step 2: Create Azure Service Principal

Create a service principal with Contributor role on the resource group:

```bash
az ad sp create-for-rbac \
  --name "sp-heblo-mcp-deploy" \
  --role Contributor \
  --scopes /subscriptions/$(az account show --query id -o tsv)/resourceGroups/rgHeblo \
  --sdk-auth
```

**IMPORTANT:** Save the entire JSON output. You'll need it for GitHub Secrets.

Example output:
```json
{
  "clientId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "clientSecret": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "subscriptionId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "tenantId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  ...
}
```

## Step 3: Create Azure Web App

Create the Web App for Containers:

```bash
az webapp create \
  --resource-group rgHeblo \
  --plan spHeblo \
  --name heblo-mcp \
  --deployment-container-image-name nginx:latest
```

Note: We use nginx:latest as a placeholder. GitHub Actions will deploy the actual image.

Configure the Web App for custom port:

```bash
az webapp config appsettings set \
  --resource-group rgHeblo \
  --name heblo-mcp \
  --settings WEBSITES_PORT=8000
```

Enable Always On (keeps container running):

```bash
az webapp config set \
  --resource-group rgHeblo \
  --name heblo-mcp \
  --always-on true
```

## Step 4: Configure Application Settings

Set runtime environment variables:

```bash
az webapp config appsettings set \
  --resource-group rgHeblo \
  --name heblo-mcp \
  --settings \
    HEBLO_TENANT_ID="your-heblo-tenant-id" \
    HEBLO_CLIENT_ID="your-heblo-client-id" \
    HEBLO_TRANSPORT="sse" \
    WEBSITES_PORT="8000"
```

Replace `your-heblo-tenant-id` and `your-heblo-client-id` with actual values.

## Step 5: Configure GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions → New repository secret

Add the following secrets:

**DockerHub:**
- `DOCKERHUB_USERNAME`: Your DockerHub username
- `DOCKERHUB_TOKEN`: Create at https://hub.docker.com/settings/security

**Azure Service Principal** (from Step 2 output):
- `AZURE_CLIENT_ID`: The `clientId` from JSON
- `AZURE_CLIENT_SECRET`: The `clientSecret` from JSON
- `AZURE_TENANT_ID`: The `tenantId` from JSON
- `AZURE_SUBSCRIPTION_ID`: The `subscriptionId` from JSON

**Azure Configuration:**
- `AZURE_WEBAPP_NAME`: `heblo-mcp`
- `AZURE_RESOURCE_GROUP`: `rgHeblo`

## Step 6: Verify Setup

Check Web App status:

```bash
az webapp show \
  --resource-group rgHeblo \
  --name heblo-mcp \
  --query "{name:name, state:state, defaultHostName:defaultHostName}"
```

Expected output:
```json
{
  "defaultHostName": "heblo-mcp.azurewebsites.net",
  "name": "heblo-mcp",
  "state": "Running"
}
```

## Next Steps

1. Push code to `main` branch
2. GitHub Actions will automatically build and deploy
3. Access health endpoint: https://heblo-mcp.azurewebsites.net/health
4. Connect MCP client to: https://heblo-mcp.azurewebsites.net

## Troubleshooting

**Check deployment logs:**
```bash
az webapp log tail --resource-group rgHeblo --name heblo-mcp
```

**Check container logs:**
Go to Azure Portal → App Services → heblo-mcp → Log stream

**Restart the app:**
```bash
az webapp restart --resource-group rgHeblo --name heblo-mcp
```

**Manually update container image:**
```bash
az webapp config container set \
  --resource-group rgHeblo \
  --name heblo-mcp \
  --docker-custom-image-name yourusername/heblo-mcp:latest
```
```

**Step 2: Commit**

```bash
git add docs/AZURE_SETUP.md
git commit -m "docs: add Azure infrastructure setup guide"
```

---

## Part 4: Testing & Validation

### Task 6: Create Deployment Testing Checklist

**Files:**
- Create: `docs/DEPLOYMENT_CHECKLIST.md`

**Step 1: Create checklist document**

Create `docs/DEPLOYMENT_CHECKLIST.md`:

```markdown
# Deployment Validation Checklist

Use this checklist after first deployment and for troubleshooting.

## Pre-Deployment

- [ ] All tests pass locally: `pytest -v`
- [ ] Docker builds locally: `docker build -t heblo-mcp:test .`
- [ ] Docker runs locally: `docker run -p 8000:8000 -e HEBLO_TENANT_ID=test -e HEBLO_CLIENT_ID=test heblo-mcp:test`
- [ ] GitHub Secrets configured (see AZURE_SETUP.md)
- [ ] Azure Web App created and running

## GitHub Actions Pipeline

- [ ] Workflow runs without errors
- [ ] Tests pass in CI
- [ ] Docker image pushed to DockerHub
- [ ] Azure deployment completes
- [ ] Health check passes in workflow

## Azure Web App

- [ ] App shows "Running" status in portal
- [ ] Container logs show startup success
- [ ] Health endpoint returns 200: `curl https://heblo-mcp.azurewebsites.net/health`
- [ ] Expected response:
  ```json
  {
    "status": "healthy",
    "version": "0.1.0",
    "transport": "sse"
  }
  ```

## MCP Client Connection

- [ ] Can connect to SSE endpoint
- [ ] Device code authentication works
- [ ] Sample tool call succeeds (e.g., catalog_list)
- [ ] No authentication errors in logs

## Rollback Test

- [ ] Can rollback via Azure Portal → Deployment Center
- [ ] Can rollback by reverting git commit and pushing
- [ ] Previous version works after rollback

## Monitoring

- [ ] Azure logs accessible via `az webapp log tail`
- [ ] Container logs visible in portal
- [ ] No error patterns in logs

## Performance

- [ ] Deployment completes in < 5 minutes
- [ ] Health check responds in < 2 seconds
- [ ] Tool calls respond in reasonable time

## Troubleshooting Commands

```bash
# Check app status
az webapp show --resource-group rgHeblo --name heblo-mcp

# View logs
az webapp log tail --resource-group rgHeblo --name heblo-mcp

# Restart app
az webapp restart --resource-group rgHeblo --name heblo-mcp

# Check deployment history
az webapp deployment list --resource-group rgHeblo --name heblo-mcp

# Test health endpoint
curl -v https://heblo-mcp.azurewebsites.net/health
```
```

**Step 2: Commit**

```bash
git add docs/DEPLOYMENT_CHECKLIST.md
git commit -m "docs: add deployment validation checklist"
```

---

## Part 5: Update Documentation

### Task 7: Update README with Deployment Info

**Files:**
- Modify: `README.md`

**Step 1: Read current README**

Note the Docker Usage section location (around line 192).

**Step 2: Add deployment section**

In `README.md`, add new section after "Docker Usage" section:

```markdown
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
- Health check: `https://heblo-mcp.azurewebsites.net/health`
- SSE endpoint: `https://heblo-mcp.azurewebsites.net`

**Monitoring:**
```bash
az webapp log tail --resource-group rgHeblo --name heblo-mcp
```

For detailed deployment steps, see:
- [Azure Setup Guide](docs/AZURE_SETUP.md)
- [Deployment Checklist](docs/DEPLOYMENT_CHECKLIST.md)
```

**Step 3: Update Docker section**

In the "Docker Usage" section, update the "Run Server" example to mention both modes:

```markdown
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
```

**Step 4: Commit**

```bash
git add README.md
git commit -m "docs: add cloud deployment information to README"
```

---

## Part 6: Final Integration

### Task 8: Run Full Test Suite

**Step 1: Run all tests**

Run: `pytest -v`

Expected: All tests pass

**Step 2: Fix any failing tests**

If tests fail, fix them before proceeding.

**Step 3: Build Docker image**

Run: `docker build -t heblo-mcp:final-test .`

Expected: Build succeeds

**Step 4: Test Docker image locally**

Run:
```bash
docker run -d -p 8000:8000 \
  --name heblo-mcp-test \
  -e HEBLO_TENANT_ID=test \
  -e HEBLO_CLIENT_ID=test \
  heblo-mcp:final-test
```

Wait 5 seconds, then:

```bash
curl http://localhost:8000/health
```

Expected: Returns health status JSON

Cleanup:
```bash
docker stop heblo-mcp-test
docker rm heblo-mcp-test
```

**Step 5: Commit any fixes**

```bash
git add .
git commit -m "fix: resolve integration test issues"
```

---

### Task 9: Prepare for First Deployment

**Step 1: Verify all changes are committed**

Run: `git status`

Expected: Working tree clean

**Step 2: Review all commits**

Run: `git log --oneline -10`

Expected: See all deployment-related commits

**Step 3: Push to main branch**

Run: `git push origin main`

Expected: Push succeeds, GitHub Actions triggered

**Step 4: Monitor GitHub Actions**

1. Go to GitHub repository → Actions tab
2. Watch the "Deploy to Azure" workflow run
3. Verify each step completes successfully

**Step 5: Verify deployment**

Run:
```bash
curl https://heblo-mcp.azurewebsites.net/health
```

Expected: Returns health status JSON

**Step 6: Check Azure logs**

Run:
```bash
az webapp log tail --resource-group rgHeblo --name heblo-mcp
```

Expected: No errors, successful startup

---

## Success Criteria

- ✅ All tests pass locally and in CI
- ✅ Docker image builds successfully
- ✅ GitHub Actions workflow completes without errors
- ✅ Azure Web App shows "Running" status
- ✅ Health endpoint returns 200 OK
- ✅ Container logs show successful startup
- ✅ Deployment time < 5 minutes
- ✅ Documentation complete and accurate

## Rollback Plan

If deployment fails:

1. **Immediate rollback:**
   ```bash
   az webapp config container set \
     --resource-group rgHeblo \
     --name heblo-mcp \
     --docker-custom-image-name yourusername/heblo-mcp:previous-tag
   ```

2. **Fix and redeploy:**
   ```bash
   git revert HEAD
   git push origin main
   ```

3. **Check logs for issues:**
   ```bash
   az webapp log tail --resource-group rgHeblo --name heblo-mcp
   ```

## Next Steps After Deployment

1. Test MCP client connection with SSE endpoint
2. Verify device code authentication flow
3. Test sample tool calls (catalog_list, etc.)
4. Set up monitoring alerts (optional)
5. Configure custom domain (optional)
6. Add Application Insights (optional)
