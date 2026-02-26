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
- [ ] Root endpoint returns 200: `curl https://heblo-mcp.azurewebsites.net/`
- [ ] Expected response: FastMCP SSE endpoint information

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

# Test root endpoint
curl -v https://heblo-mcp.azurewebsites.net/
```
