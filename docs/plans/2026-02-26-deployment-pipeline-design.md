# Deployment Pipeline Design

**Date:** 2026-02-26
**Status:** Approved
**Approach:** Dual-Mode Server (stdio + SSE)

## Overview

Deploy HebloMCP as a remotely accessible HTTP/SSE service on Azure Web App using GitHub Actions CI/CD and DockerHub as the container registry. The solution maintains backward compatibility with local stdio usage while enabling cloud deployment.

## Requirements

- **Environment:** Production only
- **Deployment Trigger:** Automatic on push to main branch
- **Container Registry:** DockerHub
- **Cloud Platform:** Azure Web App for Containers
- **Authentication:** Azure Service Principal
- **Secrets:** Azure Web App Configuration

## Architecture

### Dual-Mode Transport

The server supports two transport modes:

1. **stdio mode** (default) - Local usage with Claude Desktop
2. **SSE mode** - Remote HTTPS access for cloud deployment

Transport mode is controlled via:
- CLI flag: `heblo-mcp serve-sse`
- Environment variable: `HEBLO_TRANSPORT=sse`

### Infrastructure

**Existing Azure Resources:**
- Resource Group: `rgHeblo` (Germany West)
- App Service Plan: `spHeblo`

**New Azure Resources:**
- Web App: `heblo_mcp`
- Service Principal: `sp-heblo-mcp-deploy` (Contributor role on `rgHeblo`)

**Azure Web App Configuration:**
- Container Source: DockerHub
- Port: 8000
- Always On: Enabled
- App Settings:
  - `HEBLO_TENANT_ID` - Heblo tenant ID
  - `HEBLO_CLIENT_ID` - Heblo client ID
  - `HEBLO_TRANSPORT` - `sse`
  - `WEBSITES_PORT` - `8000`

## Code Changes

### 1. SSE Transport Support

**File: `src/heblo_mcp/server.py`**
- Add SSE transport mode using FastMCP's built-in support
- Auto-detect transport based on environment
- Expose on port 8000 in SSE mode
- Add `/health` endpoint for Azure health checks

**File: `src/heblo_mcp/__main__.py`**
- Add `serve-sse` command
- Keep existing `login` and default stdio behavior

**File: `Dockerfile`**
- Update `CMD` to run in SSE mode: `["serve-sse"]`
- Expose port 8000
- Add health check configuration

### 2. Health Check Endpoint

Add `/health` endpoint that returns:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "transport": "sse"
}
```

## CI/CD Pipeline

### Workflow: `.github/workflows/deploy.yml`

**Trigger:**
- Push to `main` branch
- Paths: `src/**`, `Dockerfile`, `pyproject.toml`

**Pipeline Stages:**

1. **Build & Test**
   - Checkout code
   - Setup Python 3.12
   - Install dependencies
   - Run pytest

2. **Build Docker Image**
   - Build multi-stage Dockerfile
   - Tag with:
     - `latest`
     - `sha-{commit-sha}` (for rollback capability)

3. **Push to DockerHub**
   - Login using `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`
   - Push both tags

4. **Deploy to Azure Web App**
   - Login using Service Principal credentials
   - Update Web App to pull new image
   - Wait for health check
   - Verify deployment success

**Estimated Time:** 3-5 minutes per deployment

### GitHub Secrets

Required secrets in repository settings:

**DockerHub:**
- `DOCKERHUB_USERNAME` - DockerHub username
- `DOCKERHUB_TOKEN` - Access token from hub.docker.com/settings/security

**Azure Service Principal:**
- `AZURE_CLIENT_ID` - Service principal application ID
- `AZURE_CLIENT_SECRET` - Service principal secret
- `AZURE_TENANT_ID` - Azure tenant ID
- `AZURE_SUBSCRIPTION_ID` - Azure subscription ID

**Azure Configuration:**
- `AZURE_WEBAPP_NAME` - `heblo_mcp`
- `AZURE_RESOURCE_GROUP` - `rgHeblo`

## Deployment Flow

```
Developer pushes to main
         ↓
GitHub Actions triggered
         ↓
Run pytest
  ├─ Pass → Continue
  └─ Fail → Stop & notify
         ↓
Build Docker image
  - yourusername/heblo-mcp:latest
  - yourusername/heblo-mcp:sha-abc1234
         ↓
Push to DockerHub
         ↓
Deploy to Azure Web App
  - Pull image from DockerHub
  - Start new container
  - Health check on /health
  - Stop old container
         ↓
Deployment complete
  - Service: https://heblo-mcp.azurewebsites.net
```

### Zero-Downtime Deployment

- Azure performs rolling deployment
- New container starts before old one stops
- Health checks ensure readiness
- Automatic rollback on health check failure

## Testing & Validation

### Pre-Deployment (CI Pipeline)
- Pytest suite runs automatically
- Pipeline fails if tests don't pass

### Post-Deployment Validation

**Health Check:**
- Endpoint: `https://heblo-mcp.azurewebsites.net/health`
- Expected: HTTP 200 OK

**MCP Connection Test:**
1. Connect MCP client to SSE endpoint
2. Verify device code authentication
3. Test sample tool call (e.g., `catalog_list`)

**Azure Monitoring:**
- Container logs: Azure Portal → Log Stream
- Deployment history: Deployment Center
- Optional: Application Insights for metrics

### First Deployment Checklist
- [ ] Health endpoint returns 200
- [ ] Container logs show successful startup
- [ ] Device code authentication works
- [ ] Tool calls return expected data
- [ ] No errors in Azure logs

## Error Handling & Rollback

### Failure Scenarios

**1. Tests Fail in CI**
- Pipeline stops immediately
- No deployment occurs
- Developer notified via GitHub
- Fix: Address test failures, push again

**2. Docker Build Fails**
- Pipeline stops at build stage
- Fix: Check Dockerfile, dependencies

**3. Azure Deployment Fails**
- Old container continues running (no downtime)
- Fix: Check Azure logs, verify App Settings

**4. Health Check Fails**
- Azure marks deployment as failed
- Automatic rollback to previous version
- Fix: Investigate health endpoint issues

### Rollback Procedures

**Method 1: Via Azure Portal**
1. Go to Deployment Center
2. Select previous deployment
3. Click redeploy

**Method 2: Via Git Revert**
1. Revert problematic commit
2. Push to main
3. Automatic redeploy triggered

**Method 3: Via DockerHub Tag**
1. Azure Portal → Container Settings
2. Change image tag to previous SHA
3. Restart container

### Monitoring & Alerts

- Azure logs deployment success/failure automatically
- Container logs available in real-time
- Optional: Email alerts for deployment failures

## Security Considerations

- Service Principal has Contributor role scoped to `rgHeblo` only
- DockerHub token used instead of password
- Runtime secrets stored in Azure App Settings, not in image
- Token cache persists in Azure-managed storage
- HTTPS enforced by Azure Web App

## Future Enhancements

- Add staging environment for pre-production testing
- Implement blue-green deployment strategy
- Add Application Insights for detailed telemetry
- Set up automated integration tests post-deployment
- Add Slack/Teams notifications for deployment status

## Success Metrics

- Deployment time: < 5 minutes
- Zero-downtime deployments
- Automatic rollback on failure
- Health check pass rate: 100%
- Service availability: 99.9%+

## Next Steps

1. Implement SSE transport in code
2. Create Azure Service Principal
3. Configure GitHub Secrets
4. Create GitHub Actions workflow
5. Create Azure Web App
6. Test deployment pipeline
7. Validate end-to-end functionality
