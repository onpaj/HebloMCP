# OAuth Authentication for Heblo MCP Server

**Date**: 2026-02-26
**Status**: Approved
**Author**: Claude Code (Brainstorming Session)

## Overview

Add per-user OAuth authentication for Heblo MCP server when deployed in SSE (cloud) mode, while maintaining backward compatibility with stdio (local) mode. Users will authenticate with their Microsoft accounts in Claude Code, and the server will validate their tokens and use them to call the Heblo API.

## Problem Statement

The current HebloMCP server works well for local use (stdio mode) with device code authentication, but when deployed to Azure Web App via SSE transport, there is no authentication protecting the MCP server endpoint. Anyone with the URL can access it.

**Requirements:**
- Per-user authentication (each user authenticates with their own MS account)
- User tokens used for Heblo API calls (user-level auditing)
- OAuth device code flow initiated by Claude Code client
- Client-side token storage (stateless server)
- Backward compatibility with existing stdio mode
- No breaking changes to existing deployments

## Approach: SSE Auth Headers

Use HTTP Bearer authentication for SSE connections. Claude Code initiates device code flow directly with Azure AD, obtains tokens, and passes them via `Authorization` header. Server validates JWT tokens and uses them for Heblo API calls.

**Why this approach:**
- Stateless - no server-side session management
- Standard HTTP authentication pattern
- Works with existing SSE infrastructure
- Simple JWT validation (signature + claims)
- Keeps stdio and SSE modes cleanly separated

**Alternatives considered:**
- MCP Protocol OAuth (not mature enough yet)
- Dual-mode with auth service (too complex, requires state)

## Architecture

### Two Authentication Modes

**Stdio Mode (Local) - Unchanged:**
- User runs `heblo-mcp login`
- Device code flow with Azure AD
- Token cached to `~/.config/heblo-mcp/token_cache.json`
- Server reads from cache for API calls

**SSE Mode (Cloud) - New OAuth:**
- Client initiates device code flow with Azure AD
- Client stores token in its config
- Client sends `Authorization: Bearer <token>` header
- Server validates JWT on each request
- Server uses validated token for Heblo API calls

### Transport Detection

Server auto-detects mode:
- **Stdio**: Use existing `HebloAuth` with local cache
- **SSE**: Use new `TokenValidator` for bearer tokens

### Configuration

New environment variables:
- `HEBLO_TRANSPORT` - "stdio" or "sse" (auto-detected if not set)
- `HEBLO_SSE_AUTH_ENABLED` - Enable/disable SSE auth (default: true for SSE)
- `HEBLO_JWKS_CACHE_TTL` - Cache duration for Azure AD public keys (default: 3600)

Existing variables (unchanged):
- `HEBLO_TENANT_ID`
- `HEBLO_CLIENT_ID`
- `HEBLO_API_SCOPE`

## Components

### New Components

#### 1. `token_validator.py` - JWT Token Validation

Validates Azure AD JWT tokens:
- Verify signature using Microsoft's public keys (JWKS)
- Check expiration and claims (audience, issuer, scope)
- Cache public keys with TTL
- Return validated user identity (email, tenant, object ID)

**Key Methods:**
```python
class TokenValidator:
    def __init__(tenant_id: str, audience: str, jwks_cache_ttl: int)
    async def validate_token(token: str) -> UserContext
    async def _fetch_jwks() -> dict
```

#### 2. `sse_auth.py` - SSE Authentication Middleware

ASGI middleware for SSE auth:
- Extract Bearer token from headers
- Call `TokenValidator` to validate
- Attach user context to request state
- Handle auth errors (401 responses)

**Key Methods:**
```python
class SSEAuthMiddleware:
    def __init__(app, token_validator: TokenValidator)
    async def __call__(scope, receive, send)
    def _extract_token(headers) -> str | None
```

#### 3. `auth_mode.py` - Transport Mode Detection

Factory for auth strategy:
- Detect stdio vs SSE mode
- Return appropriate auth strategy

**Key Methods:**
```python
def detect_transport_mode(config: HebloMCPConfig) -> str
def get_auth_strategy(transport: str, config: HebloMCPConfig) -> AuthStrategy
```

### Modified Components

#### 1. `server.py` - Server Creation

Changes:
- Add conditional middleware based on transport
- Stdio: Use existing `HebloAuth` (no changes)
- SSE: Add `SSEAuthMiddleware` to app
- Pass validated token to httpx client

#### 2. `config.py` - Configuration

Add fields:
- `transport: str` - Transport mode
- `sse_auth_enabled: bool` - Enable SSE auth
- `jwks_cache_ttl: int` - Public key cache TTL

#### 3. `auth.py` - Existing Auth

Minor changes:
- Extract reusable token validation helpers
- No breaking changes to `HebloAuth`
- Keep device code flow unchanged

### Dependencies

New packages:
- `PyJWT[crypto]` - JWT parsing and validation
- `cryptography` - RSA signature verification
- `cachetools` - JWKS caching (optional)

## Data Flow

### Stdio Mode (Unchanged)

```
1. User: heblo-mcp login
2. HebloAuth → Azure AD device code flow
3. User authenticates in browser
4. Token cached to ~/.config/heblo-mcp/token_cache.json
5. Claude Code starts server via stdio
6. Server reads token from cache
7. All API calls use cached token
```

### SSE Mode - Initial Setup

```
1. User configures Claude Code with MCP server URL
2. Claude Code detects OAuth requirement
3. Claude Code → Azure AD device code flow
   - tenant_id, client_id from config
   - scope: api://8b34be89-cef4-445a-929a-bc1a21dce0cb/access_as_user
4. User authenticates in browser
5. Claude Code stores access + refresh tokens (encrypted)
```

### SSE Mode - Each Request

```
1. Claude Code establishes SSE connection
   Header: Authorization: Bearer <user_access_token>
2. SSEAuthMiddleware extracts token
3. TokenValidator validates:
   - Fetch Azure AD public keys (JWKS) if not cached
   - Verify JWT signature with RSA public key
   - Check expiration (exp claim)
   - Verify audience (aud) = Heblo client ID
   - Verify issuer (iss) = Azure AD tenant
4. Valid → Attach user context to request
5. Invalid → Return 401 Unauthorized
6. Tool call → httpx uses user token for Heblo API
   Authorization: Bearer <user_token>
7. Return MCP response
```

### Token Refresh (Client-side)

```
1. Claude Code receives 401 response
2. Uses refresh token → Azure AD for new access token
3. Updates stored token
4. Retries request
```

## Error Handling

### Authentication Errors

| Error | When | Response | Message | Client Action |
|-------|------|----------|---------|---------------|
| Missing Token | No Authorization header | 401 | "Authentication required. Please provide Bearer token." | Initiate device code flow |
| Invalid Format | Not a valid JWT | 401 | "Invalid token format. Expected JWT Bearer token." | Clear cache, re-auth |
| Expired Token | exp claim in past | 401 | "Token expired. Please refresh your authentication." | Use refresh token |
| Invalid Signature | Signature doesn't match | 401 | "Invalid token signature." | Clear cache, re-auth |
| Wrong Audience/Issuer | aud/iss mismatch | 403 | "Token not valid for this service." | Check Azure AD config |

### JWKS Fetching Errors

**Can't fetch public keys:**
- Fallback: Use cached keys (up to 24 hours old)
- No cache: 503 Service Unavailable
- Message: "Unable to validate tokens. Please try again later."

**Key rotation:**
- Cache keys with TTL (1 hour default)
- On signature failure: Refresh JWKS and retry once

### Heblo API Errors

**401 from Heblo API:**
- Response: 403 Forbidden (token valid but insufficient permissions)
- Message: "Your account doesn't have access to Heblo API. Contact your administrator."

**Token expires mid-request:**
- Response: 401 Unauthorized
- Message: "Token expired during request. Please retry."

### Graceful Degradation

- Health endpoint (`/health`) bypasses auth
- Stdio mode works if SSE auth fails to initialize
- Don't break existing deployments

### Logging

**Log (audit trail):**
- Auth attempts (success/failure)
- Token validation failures (type)
- User identity (email, tenant ID)
- JWKS refresh events

**Never log:**
- Actual token values
- Full error details to client

## Testing Strategy

### Unit Tests

**`test_token_validator.py`:**
- ✓ Validate well-formed JWT with correct signature
- ✗ Reject expired token
- ✗ Reject wrong audience
- ✗ Reject wrong issuer
- ✗ Reject invalid signature
- Handle JWKS fetch failures
- Cache JWKS with TTL
- Refresh on key rotation

**`test_sse_auth.py`:**
- ✓ Extract Bearer token from header
- ✗ Reject missing Authorization header
- ✗ Reject malformed header
- ✓ Attach user context to request
- ✗ Return 401 on validation failure
- ✓ Bypass auth for health endpoint

**`test_auth_mode.py`:**
- Detect stdio mode from config
- Detect SSE mode from config
- Auto-detect when not configured
- Return correct auth strategy

**`test_server_creation.py`:**
- Create stdio server without middleware
- Create SSE server with auth middleware
- Config-based mode selection

### Integration Tests

**`test_sse_auth_integration.py`:**
- SSE connection with valid token → success
- SSE with expired token → 401
- SSE without token → 401
- Tool call → Heblo API receives user token
- Health endpoint accessible without auth

**`test_backward_compatibility.py`:**
- Stdio mode unchanged
- Token cache still works
- `heblo-mcp login` unchanged
- No breaking changes

### Manual Testing

**Claude Code Integration:**
1. Configure SSE endpoint
2. Initiate device code flow
3. Complete auth in browser
4. Verify tool calls work
5. Test token expiration/refresh
6. Verify 401 handling

**Local Development:**
1. Test stdio with existing flow
2. Test SSE with mock tokens
3. Use `fastmcp dev` with middleware
4. Test invalid/expired tokens

### Test Fixtures

- Valid JWT (mock signature)
- Expired token
- Wrong audience token
- Wrong issuer token
- Malformed token
- Mock JWKS endpoint

### Coverage Goals

- Token validation: 100% (critical security)
- Auth middleware: 95%
- Mode detection: 100%
- Overall auth module: 95%+

## Security Considerations

**Benefits:**
- Stateless validation (no session state to compromise)
- Per-user tokens (audit trail at Heblo API level)
- Token isolation (users can't access others' data)
- Standard JWT validation (well-tested libraries)

**Risks & Mitigations:**
- Token theft → Short token expiration (1 hour typical)
- Replay attacks → HTTPS required, validate exp claim
- JWKS endpoint compromise → Cache with TTL, validate issuer
- Token in logs → Never log token values

## Implementation Plan

Implementation details will be created in the next phase using the `writing-plans` skill.

## Success Criteria

- ✓ SSE mode requires valid Azure AD token
- ✓ Invalid tokens receive 401 Unauthorized
- ✓ Heblo API calls use user's token
- ✓ Stdio mode continues working unchanged
- ✓ No breaking changes to existing deployments
- ✓ 95%+ test coverage for auth code
- ✓ Integration test with Claude Code passes
- ✓ Health endpoint accessible without auth

## Future Enhancements

- Support for MCP Protocol OAuth when spec matures
- Token refresh on server side (if needed)
- Rate limiting per user
- Admin API for token revocation
- Support for API keys as alternative auth method
