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
