# Claude Desktop OAuth Configuration Guide

This guide explains how to configure OAuth authentication for Claude Desktop to connect to your deployed HebloMCP server.

## Architecture

Claude Desktop uses OAuth 2.0 Authorization Code Flow with PKCE. Your MCP server acts as an OAuth proxy between Claude Desktop and Azure AD:

```
Claude Desktop → MCP Server → Azure AD (Entra ID)
       ↓              ↓              ↓
   1. /authorize → 2. Redirect → 3. User Login
       ↓              ↓              ↓
   7. Token ←── 6. /token ←── 5. Exchange Code
```

## Prerequisites

- Azure AD App Registration (already created)
- Access to Azure Portal
- MCP server deployed at `https://mcp.heblo.anela.cz`

## Step 1: Generate Client Secret

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to: **Entra ID → App Registrations**
3. Find your app: `baca6321-c6ca-4893-9174-d8054e5cca6b`
4. Go to: **Certificates & secrets**
5. Click: **New client secret**
   - Description: `Claude Desktop MCP OAuth`
   - Expires: 12-24 months (recommended)
6. Click: **Add**
7. **CRITICAL:** Copy the secret value immediately (shown only once!)

## Step 2: Add Redirect URI

1. In your app registration, go to: **Authentication**
2. Under **Platform configurations**, click: **Add a platform**
3. Select: **Web**
4. Add redirect URI: `https://mcp.heblo.anela.cz/callback`
5. Click: **Configure**
6. Scroll down and ensure **Allow public client flows** is set to **Yes**

## Step 3: Verify API Permissions

1. In your app registration, go to: **API permissions**
2. Verify the following permission exists:
   - **API:** `api://8b34be89-f86f-422f-af40-7dbcd30cb66a`
   - **Permission:** `access_as_user` (Delegated)
   - **Type:** Delegated
3. If missing, click **Add a permission** → **APIs my organization uses** → Find your API
4. If "Admin consent required" is shown, click **Grant admin consent**

## Step 4: Configure Environment Variables

Add the client secret to your `.env` file:

```bash
# Existing configuration
HEBLO_TENANT_ID=31fd4df1-b9c0-4abd-a4b0-0e1aceaabe9a
HEBLO_CLIENT_ID=baca6321-c6ca-4893-9174-d8054e5cca6b
HEBLO_API_SCOPE=api://8b34be89-f86f-422f-af40-7dbcd30cb66a/access_as_user

# Add this (use the secret you copied):
HEBLO_CLIENT_SECRET=<paste-your-client-secret-here>
```

For deployed server (Azure Web App), add the secret to Application Settings:
1. Go to your Azure Web App
2. Navigate to: **Configuration → Application settings**
3. Click: **New application setting**
   - Name: `HEBLO_CLIENT_SECRET`
   - Value: `<your-client-secret>`
4. Click: **OK** → **Save**

## Step 5: Deploy OAuth Endpoints

The OAuth proxy endpoints are now implemented in your codebase:
- `/authorize` - Initiates OAuth flow
- `/callback` - Handles Azure AD callback
- `/token` - Exchanges authorization code for token

Deploy the updated code:

```bash
# Test locally first
python -m heblo_mcp serve-sse

# Or deploy to Azure
git add .
git commit -m "feat: add OAuth proxy for Claude Desktop authentication"
git push origin master  # Triggers GitHub Actions deployment
```

## Step 6: Configure Claude Desktop

In Claude Desktop, add your MCP server:

1. Open Claude Desktop settings
2. Go to **MCP Servers** (or similar)
3. Add server with OAuth configuration:

```json
{
  "heblo-mcp": {
    "url": "https://mcp.heblo.anela.cz",
    "auth": {
      "type": "oauth2",
      "client_id": "baca6321-c6ca-4893-9174-d8054e5cca6b"
    }
  }
}
```

**Note:** Claude Desktop will handle the OAuth flow automatically. You don't need to provide the client secret in Claude Desktop.

## Step 7: Test the Connection

1. Restart Claude Desktop
2. Click to connect to the HebloMCP server
3. You should be redirected to Azure AD login page
4. Sign in with your organizational account
5. Grant consent if prompted
6. You'll be redirected back to Claude Desktop
7. The MCP server should now be connected

## Troubleshooting

### Error: "Invalid redirect_uri"
- Verify `https://mcp.heblo.anela.cz/callback` is added to your app's redirect URIs
- Ensure the URI matches exactly (no trailing slash)

### Error: "Client secret not configured"
- Check that `HEBLO_CLIENT_SECRET` is set in your environment
- For Azure Web App, verify the Application Setting is saved and restarted

### Error: "Invalid audience"
- Verify the API scope in `.env` matches your API app registration
- Check that the API permission is granted in Azure AD

### Error: "Token validation failed"
- Ensure the token validator is using the correct tenant ID and client ID
- Verify JWKS endpoint is accessible from your server

### Connection timeout
- Check that your server is running and accessible
- Verify firewall rules allow HTTPS traffic
- Test the health endpoint: `curl https://mcp.heblo.anela.cz/`

## Security Considerations

1. **Client Secret Storage:**
   - Never commit client secrets to git
   - Use Azure Key Vault for production secrets
   - Rotate secrets periodically (before expiration)

2. **Session Storage:**
   - Current implementation uses in-memory storage
   - For multi-instance deployments, use Redis or database
   - Sessions expire after 10 minutes (configurable)

3. **Token Security:**
   - Tokens are validated using Azure AD's public keys (JWKS)
   - Tokens expire after 1 hour (Azure AD default)
   - No tokens are stored on disk

## Architecture Details

### OAuth Flow Sequence

1. **Authorization Request:**
   - Claude Desktop → `GET /authorize?client_id=...&redirect_uri=https://claude.ai/...&code_challenge=...`
   - Server stores PKCE challenge and redirects to Azure AD
   - Azure AD → User authentication page

2. **Authorization Grant:**
   - User authenticates and consents
   - Azure AD → `GET /callback?code=<azure_code>&state=...`

3. **Token Exchange:**
   - Server exchanges Azure code for access token (using client secret)
   - Server generates proxy code
   - Server → Redirects to Claude Desktop: `https://claude.ai/...?code=<proxy_code>`

4. **Token Retrieval:**
   - Claude Desktop → `POST /token` with proxy code and PKCE verifier
   - Server validates PKCE
   - Server → Returns Azure AD access token

5. **MCP Connection:**
   - Claude Desktop → `GET /sse` with Bearer token
   - Middleware validates JWT token
   - MCP connection established

### Security Features

- **PKCE (Proof Key for Code Exchange):** Prevents authorization code interception
- **State Parameter:** Prevents CSRF attacks
- **JWT Validation:** Verifies token signature, expiration, audience, issuer
- **Code Expiration:** Proxy codes expire after 5 minutes
- **Single-Use Codes:** Each proxy code can only be exchanged once

## Additional Resources

- [Azure AD OAuth 2.0 Documentation](https://docs.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-auth-code-flow)
- [PKCE Specification (RFC 7636)](https://tools.ietf.org/html/rfc7636)
- [MCP Protocol Specification](https://modelcontextprotocol.io)
