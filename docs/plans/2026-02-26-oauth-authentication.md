# OAuth Authentication for SSE Mode Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add per-user OAuth authentication for Heblo MCP server when deployed in SSE mode, validating Azure AD JWT tokens while maintaining backward compatibility with stdio mode.

**Architecture:** Client (Claude Code) authenticates with Azure AD and sends Bearer token in Authorization header. Server validates JWT signature using Azure AD public keys (JWKS), checks claims, and uses validated token for Heblo API calls. Stdio mode unchanged.

**Tech Stack:** PyJWT for JWT validation, httpx for JWKS fetching, ASGI middleware for request interception, pytest for testing.

---

## Task 1: Add JWT Dependencies

**Files:**
- Modify: `pyproject.toml:15-20`

**Step 1: Add PyJWT and cryptography to dependencies**

Update the dependencies section in pyproject.toml:

```toml
dependencies = [
    "fastmcp>=3.0",
    "httpx>=0.27.0",
    "msal>=1.31.0",
    "pydantic-settings>=2.6.0",
    "PyJWT[crypto]>=2.9.0",
    "cryptography>=43.0.0",
]
```

**Step 2: Install new dependencies**

Run: `pip install -e .`
Expected: PyJWT and cryptography installed successfully

**Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "feat: add PyJWT and cryptography dependencies for OAuth"
```

---

## Task 2: Update Configuration

**Files:**
- Modify: `src/heblo_mcp/config.py:8-38`
- Test: `tests/unit/test_config.py`

**Step 1: Write failing test for new config fields**

Add to `tests/unit/test_config.py`:

```python
def test_config_has_transport_field():
    """Test that config has transport field with default auto."""
    config = HebloMCPConfig(
        tenant_id="test-tenant",
        client_id="test-client"
    )
    assert hasattr(config, "transport")
    assert config.transport == "auto"


def test_config_has_sse_auth_enabled_field():
    """Test that config has sse_auth_enabled field."""
    config = HebloMCPConfig(
        tenant_id="test-tenant",
        client_id="test-client"
    )
    assert hasattr(config, "sse_auth_enabled")
    assert config.sse_auth_enabled is True


def test_config_has_jwks_cache_ttl_field():
    """Test that config has jwks_cache_ttl field with default 3600."""
    config = HebloMCPConfig(
        tenant_id="test-tenant",
        client_id="test-client"
    )
    assert hasattr(config, "jwks_cache_ttl")
    assert config.jwks_cache_ttl == 3600
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_config.py::test_config_has_transport_field -v`
Expected: FAIL with "AttributeError: 'HebloMCPConfig' object has no attribute 'transport'"

**Step 3: Add new fields to HebloMCPConfig**

Update `src/heblo_mcp/config.py`:

```python
class HebloMCPConfig(BaseSettings):
    """HebloMCP configuration loaded from environment variables.

    All settings can be overridden via environment variables prefixed with HEBLO_.
    Example: HEBLO_CLIENT_ID, HEBLO_TENANT_ID, etc.
    """

    model_config = SettingsConfigDict(
        env_prefix="HEBLO_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Azure AD Authentication
    tenant_id: str
    client_id: str
    api_scope: str = "api://8b34be89-cef4-445a-929a-bc1a21dce0cb/access_as_user"

    # API Configuration
    api_base_url: str = "https://heblo.anela.cz"
    openapi_spec_url: str = "https://heblo.stg.anela.cz/swagger/v1/swagger.json"

    # Token Cache
    token_cache_path: Path = Path.home() / ".config" / "heblo-mcp" / "token_cache.json"

    # Transport and Authentication
    transport: str = "auto"  # "stdio", "sse", or "auto" to detect
    sse_auth_enabled: bool = True  # Enable SSE authentication validation
    jwks_cache_ttl: int = 3600  # JWKS cache time-to-live in seconds

    def __init__(self, **kwargs):
        """Initialize config and ensure token cache directory exists."""
        super().__init__(**kwargs)
        self.token_cache_path.parent.mkdir(parents=True, exist_ok=True)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_config.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/heblo_mcp/config.py tests/unit/test_config.py
git commit -m "feat: add transport and SSE auth config fields"
```

---

## Task 3: Create Transport Mode Detection

**Files:**
- Create: `src/heblo_mcp/auth_mode.py`
- Create: `tests/unit/test_auth_mode.py`

**Step 1: Write failing test for transport detection**

Create `tests/unit/test_auth_mode.py`:

```python
"""Tests for transport mode detection."""

import pytest
from heblo_mcp.auth_mode import detect_transport_mode
from heblo_mcp.config import HebloMCPConfig


def test_detect_stdio_mode_explicit():
    """Test detection of explicit stdio mode."""
    config = HebloMCPConfig(
        tenant_id="test",
        client_id="test",
        transport="stdio"
    )
    assert detect_transport_mode(config) == "stdio"


def test_detect_sse_mode_explicit():
    """Test detection of explicit sse mode."""
    config = HebloMCPConfig(
        tenant_id="test",
        client_id="test",
        transport="sse"
    )
    assert detect_transport_mode(config) == "sse"


def test_detect_auto_mode_defaults_to_stdio():
    """Test that auto mode defaults to stdio for safety."""
    config = HebloMCPConfig(
        tenant_id="test",
        client_id="test",
        transport="auto"
    )
    # For now, auto defaults to stdio (safest option)
    assert detect_transport_mode(config) == "stdio"
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_auth_mode.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'heblo_mcp.auth_mode'"

**Step 3: Create minimal implementation**

Create `src/heblo_mcp/auth_mode.py`:

```python
"""Transport mode detection for HebloMCP server."""

from heblo_mcp.config import HebloMCPConfig


def detect_transport_mode(config: HebloMCPConfig) -> str:
    """Detect the transport mode from configuration.

    Args:
        config: HebloMCP configuration

    Returns:
        "stdio" or "sse"
    """
    if config.transport in ("stdio", "sse"):
        return config.transport

    # Auto mode: default to stdio for safety
    # In production, you might detect from environment or process info
    return "stdio"
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_auth_mode.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/heblo_mcp/auth_mode.py tests/unit/test_auth_mode.py
git commit -m "feat: add transport mode detection"
```

---

## Task 4: Create User Context Model

**Files:**
- Create: `src/heblo_mcp/user_context.py`
- Create: `tests/unit/test_user_context.py`

**Step 1: Write failing test for UserContext**

Create `tests/unit/test_user_context.py`:

```python
"""Tests for user context model."""

from heblo_mcp.user_context import UserContext


def test_user_context_creation():
    """Test creating a user context."""
    ctx = UserContext(
        email="user@example.com",
        tenant_id="tenant-123",
        object_id="obj-456",
        token="fake-token"
    )
    assert ctx.email == "user@example.com"
    assert ctx.tenant_id == "tenant-123"
    assert ctx.object_id == "obj-456"
    assert ctx.token == "fake-token"


def test_user_context_repr_hides_token():
    """Test that repr doesn't expose token."""
    ctx = UserContext(
        email="user@example.com",
        tenant_id="tenant-123",
        object_id="obj-456",
        token="secret-token"
    )
    repr_str = repr(ctx)
    assert "secret-token" not in repr_str
    assert "user@example.com" in repr_str
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_user_context.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Create UserContext model**

Create `src/heblo_mcp/user_context.py`:

```python
"""User context model for authenticated requests."""

from dataclasses import dataclass


@dataclass
class UserContext:
    """Represents an authenticated user's context.

    Attributes:
        email: User's email address
        tenant_id: Azure AD tenant ID
        object_id: User's object ID in Azure AD
        token: Access token for API calls
    """

    email: str
    tenant_id: str
    object_id: str
    token: str

    def __repr__(self) -> str:
        """String representation without exposing token."""
        return f"UserContext(email={self.email!r}, tenant_id={self.tenant_id!r}, object_id={self.object_id!r})"
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_user_context.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/heblo_mcp/user_context.py tests/unit/test_user_context.py
git commit -m "feat: add UserContext model for authenticated users"
```

---

## Task 5: Create JWT Token Validator

**Files:**
- Create: `src/heblo_mcp/token_validator.py`
- Create: `tests/unit/test_token_validator.py`
- Create: `tests/fixtures/jwt_fixtures.py`

**Step 1: Create JWT test fixtures**

Create `tests/fixtures/__init__.py`:

```python
"""Test fixtures for HebloMCP tests."""
```

Create `tests/fixtures/jwt_fixtures.py`:

```python
"""JWT token fixtures for testing."""

import time
from typing import Dict

import jwt


def create_test_jwt(
    tenant_id: str = "test-tenant",
    client_id: str = "test-client",
    email: str = "user@example.com",
    object_id: str = "obj-123",
    expired: bool = False,
    wrong_audience: bool = False,
    wrong_issuer: bool = False,
    private_key: str | None = None,
) -> str:
    """Create a test JWT token.

    Args:
        tenant_id: Azure AD tenant ID
        client_id: Application client ID
        email: User email
        object_id: User object ID
        expired: If True, create an expired token
        wrong_audience: If True, use wrong audience
        wrong_issuer: If True, use wrong issuer
        private_key: RSA private key (PEM format). If None, uses HS256 with "secret"

    Returns:
        JWT token string
    """
    now = int(time.time())
    exp = now - 3600 if expired else now + 3600

    payload = {
        "aud": "wrong-client" if wrong_audience else client_id,
        "iss": f"https://login.microsoftonline.com/wrong-tenant/v2.0" if wrong_issuer else f"https://login.microsoftonline.com/{tenant_id}/v2.0",
        "exp": exp,
        "iat": now,
        "nbf": now,
        "preferred_username": email,
        "oid": object_id,
        "sub": object_id,
        "tid": tenant_id,
        "scp": "access_as_user",
    }

    if private_key:
        return jwt.encode(payload, private_key, algorithm="RS256")
    else:
        # For simple tests, use HS256 with shared secret
        return jwt.encode(payload, "test-secret", algorithm="HS256")


def create_test_rsa_keypair() -> tuple[str, str]:
    """Create a test RSA key pair.

    Returns:
        Tuple of (private_key_pem, public_key_pem)
    """
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    return private_pem, public_pem


def create_test_jwks(public_key_pem: str, kid: str = "test-key-1") -> Dict:
    """Create a test JWKS (JSON Web Key Set) from a public key.

    Args:
        public_key_pem: Public key in PEM format
        kid: Key ID

    Returns:
        JWKS dictionary
    """
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
    import base64

    # Load public key
    public_key = serialization.load_pem_public_key(
        public_key_pem.encode("utf-8"),
        backend=default_backend()
    )

    # Extract public numbers
    numbers = public_key.public_numbers()

    # Convert to base64url
    def int_to_base64url(n):
        return base64.urlsafe_b64encode(
            n.to_bytes((n.bit_length() + 7) // 8, byteorder='big')
        ).rstrip(b'=').decode('utf-8')

    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "kid": kid,
                "n": int_to_base64url(numbers.n),
                "e": int_to_base64url(numbers.e),
            }
        ]
    }
```

**Step 2: Write failing tests for TokenValidator**

Create `tests/unit/test_token_validator.py`:

```python
"""Tests for JWT token validation."""

import pytest
from unittest.mock import AsyncMock, patch
from heblo_mcp.token_validator import TokenValidator, TokenValidationError
from tests.fixtures.jwt_fixtures import (
    create_test_jwt,
    create_test_rsa_keypair,
    create_test_jwks,
)


@pytest.fixture
def rsa_keys():
    """Create RSA key pair for testing."""
    return create_test_rsa_keypair()


@pytest.fixture
def mock_jwks(rsa_keys):
    """Create mock JWKS."""
    _, public_key = rsa_keys
    return create_test_jwks(public_key)


@pytest.fixture
async def validator(mock_jwks):
    """Create a TokenValidator with mocked JWKS fetching."""
    validator = TokenValidator(
        tenant_id="test-tenant",
        audience="test-client",
        jwks_cache_ttl=3600
    )

    # Mock the JWKS fetch
    with patch.object(validator, '_fetch_jwks', new=AsyncMock(return_value=mock_jwks)):
        yield validator


@pytest.mark.asyncio
async def test_validate_valid_token(validator, rsa_keys):
    """Test validating a valid JWT token."""
    private_key, _ = rsa_keys
    token = create_test_jwt(
        tenant_id="test-tenant",
        client_id="test-client",
        email="user@example.com",
        object_id="obj-123",
        private_key=private_key
    )

    user_ctx = await validator.validate_token(token)

    assert user_ctx.email == "user@example.com"
    assert user_ctx.tenant_id == "test-tenant"
    assert user_ctx.object_id == "obj-123"
    assert user_ctx.token == token


@pytest.mark.asyncio
async def test_validate_expired_token(validator, rsa_keys):
    """Test that expired tokens are rejected."""
    private_key, _ = rsa_keys
    token = create_test_jwt(
        tenant_id="test-tenant",
        client_id="test-client",
        expired=True,
        private_key=private_key
    )

    with pytest.raises(TokenValidationError, match="expired"):
        await validator.validate_token(token)


@pytest.mark.asyncio
async def test_validate_wrong_audience(validator, rsa_keys):
    """Test that tokens with wrong audience are rejected."""
    private_key, _ = rsa_keys
    token = create_test_jwt(
        tenant_id="test-tenant",
        client_id="test-client",
        wrong_audience=True,
        private_key=private_key
    )

    with pytest.raises(TokenValidationError, match="audience"):
        await validator.validate_token(token)


@pytest.mark.asyncio
async def test_validate_wrong_issuer(validator, rsa_keys):
    """Test that tokens with wrong issuer are rejected."""
    private_key, _ = rsa_keys
    token = create_test_jwt(
        tenant_id="test-tenant",
        client_id="test-client",
        wrong_issuer=True,
        private_key=private_key
    )

    with pytest.raises(TokenValidationError, match="issuer"):
        await validator.validate_token(token)


@pytest.mark.asyncio
async def test_validate_malformed_token(validator):
    """Test that malformed tokens are rejected."""
    with pytest.raises(TokenValidationError, match="Invalid token format"):
        await validator.validate_token("not-a-jwt")


@pytest.mark.asyncio
async def test_jwks_caching(validator, mock_jwks):
    """Test that JWKS is cached and not fetched multiple times."""
    # This will trigger JWKS fetch
    await validator._get_jwks()

    # Mock to track calls
    with patch.object(validator, '_fetch_jwks', new=AsyncMock(return_value=mock_jwks)) as mock_fetch:
        # Should use cache
        await validator._get_jwks()
        mock_fetch.assert_not_called()
```

**Step 3: Run tests to verify they fail**

Run: `pytest tests/unit/test_token_validator.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 4: Create TokenValidator implementation**

Create `src/heblo_mcp/token_validator.py`:

```python
"""JWT token validation for Azure AD tokens."""

import time
from typing import Dict, Optional

import httpx
import jwt
from jwt import PyJWKClient

from heblo_mcp.user_context import UserContext


class TokenValidationError(Exception):
    """Raised when token validation fails."""
    pass


class TokenValidator:
    """Validates Azure AD JWT tokens.

    Validates JWT signature using Microsoft's public keys (JWKS),
    checks expiration and claims, and returns user context.
    """

    def __init__(self, tenant_id: str, audience: str, jwks_cache_ttl: int = 3600):
        """Initialize token validator.

        Args:
            tenant_id: Azure AD tenant ID
            audience: Expected audience (client ID)
            jwks_cache_ttl: Cache TTL for JWKS in seconds
        """
        self.tenant_id = tenant_id
        self.audience = audience
        self.jwks_cache_ttl = jwks_cache_ttl

        # JWKS URL for Azure AD
        self.jwks_url = f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"

        # Cache for JWKS
        self._jwks_cache: Optional[Dict] = None
        self._jwks_cache_time: float = 0

        # PyJWKClient for fetching and caching keys
        self._jwk_client: Optional[PyJWKClient] = None

    async def validate_token(self, token: str) -> UserContext:
        """Validate JWT token and return user context.

        Args:
            token: JWT token string

        Returns:
            UserContext with user information

        Raises:
            TokenValidationError: If token validation fails
        """
        try:
            # Get signing key from JWKS
            jwks = await self._get_jwks()

            # Create JWK client if not exists
            if self._jwk_client is None:
                self._jwk_client = PyJWKClient(self.jwks_url, cache_keys=True, lifespan=self.jwks_cache_ttl)

            # Get signing key
            signing_key = self._jwk_client.get_signing_key_from_jwt(token)

            # Validate and decode token
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=f"https://login.microsoftonline.com/{self.tenant_id}/v2.0",
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_aud": True,
                    "verify_iss": True,
                }
            )

            # Extract user information
            email = payload.get("preferred_username", payload.get("email", ""))
            object_id = payload.get("oid", "")
            tenant_id = payload.get("tid", "")

            return UserContext(
                email=email,
                tenant_id=tenant_id,
                object_id=object_id,
                token=token
            )

        except jwt.ExpiredSignatureError:
            raise TokenValidationError("Token expired. Please refresh your authentication.")
        except jwt.InvalidAudienceError:
            raise TokenValidationError("Token not valid for this service. Invalid audience.")
        except jwt.InvalidIssuerError:
            raise TokenValidationError("Token not valid for this service. Invalid issuer.")
        except jwt.InvalidSignatureError:
            raise TokenValidationError("Invalid token signature.")
        except jwt.DecodeError:
            raise TokenValidationError("Invalid token format. Expected JWT Bearer token.")
        except Exception as e:
            raise TokenValidationError(f"Token validation failed: {str(e)}")

    async def _get_jwks(self) -> Dict:
        """Get JWKS, using cache if available.

        Returns:
            JWKS dictionary
        """
        now = time.time()

        # Check cache
        if self._jwks_cache and (now - self._jwks_cache_time) < self.jwks_cache_ttl:
            return self._jwks_cache

        # Fetch new JWKS
        jwks = await self._fetch_jwks()
        self._jwks_cache = jwks
        self._jwks_cache_time = now

        return jwks

    async def _fetch_jwks(self) -> Dict:
        """Fetch JWKS from Azure AD.

        Returns:
            JWKS dictionary

        Raises:
            TokenValidationError: If JWKS fetch fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.jwks_url, timeout=10.0)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            # If we have cached JWKS (even if old), use it
            if self._jwks_cache:
                return self._jwks_cache
            raise TokenValidationError(f"Unable to fetch JWKS: {str(e)}")
```

**Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/test_token_validator.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add src/heblo_mcp/token_validator.py tests/unit/test_token_validator.py tests/fixtures/
git commit -m "feat: add JWT token validator with Azure AD JWKS"
```

---

## Task 6: Create SSE Authentication Middleware

**Files:**
- Create: `src/heblo_mcp/sse_auth.py`
- Create: `tests/unit/test_sse_auth.py`

**Step 1: Write failing tests for SSE auth middleware**

Create `tests/unit/test_sse_auth.py`:

```python
"""Tests for SSE authentication middleware."""

import pytest
from unittest.mock import AsyncMock, Mock
from heblo_mcp.sse_auth import SSEAuthMiddleware
from heblo_mcp.token_validator import TokenValidator, TokenValidationError
from heblo_mcp.user_context import UserContext


class MockSend:
    """Mock send callable for ASGI."""

    def __init__(self):
        self.events = []

    async def __call__(self, event):
        self.events.append(event)


class MockReceive:
    """Mock receive callable for ASGI."""

    def __init__(self, events=None):
        self.events = events or []
        self.index = 0

    async def __call__(self):
        if self.index < len(self.events):
            event = self.events[self.index]
            self.index += 1
            return event
        return {"type": "http.disconnect"}


@pytest.fixture
def mock_validator():
    """Create a mock token validator."""
    validator = Mock(spec=TokenValidator)
    validator.validate_token = AsyncMock()
    return validator


@pytest.fixture
def mock_app():
    """Create a mock ASGI app."""
    app = AsyncMock()
    return app


@pytest.mark.asyncio
async def test_extract_bearer_token_success():
    """Test extracting Bearer token from Authorization header."""
    from heblo_mcp.sse_auth import _extract_bearer_token

    headers = [(b"authorization", b"Bearer test-token-123")]
    token = _extract_bearer_token(headers)
    assert token == "test-token-123"


@pytest.mark.asyncio
async def test_extract_bearer_token_no_header():
    """Test that missing Authorization header returns None."""
    from heblo_mcp.sse_auth import _extract_bearer_token

    headers = []
    token = _extract_bearer_token(headers)
    assert token is None


@pytest.mark.asyncio
async def test_extract_bearer_token_wrong_scheme():
    """Test that non-Bearer auth returns None."""
    from heblo_mcp.sse_auth import _extract_bearer_token

    headers = [(b"authorization", b"Basic dXNlcjpwYXNz")]
    token = _extract_bearer_token(headers)
    assert token is None


@pytest.mark.asyncio
async def test_middleware_with_valid_token(mock_validator, mock_app):
    """Test middleware with valid token."""
    # Setup
    user_ctx = UserContext(
        email="user@example.com",
        tenant_id="test-tenant",
        object_id="obj-123",
        token="valid-token"
    )
    mock_validator.validate_token.return_value = user_ctx

    middleware = SSEAuthMiddleware(mock_app, mock_validator, bypass_health=True)

    scope = {
        "type": "http",
        "path": "/some-endpoint",
        "headers": [(b"authorization", b"Bearer valid-token")],
    }

    receive = MockReceive()
    send = MockSend()

    # Execute
    await middleware(scope, receive, send)

    # Verify
    mock_validator.validate_token.assert_called_once_with("valid-token")
    assert "user" in scope
    assert scope["user"] == user_ctx
    mock_app.assert_called_once()


@pytest.mark.asyncio
async def test_middleware_missing_token(mock_validator, mock_app):
    """Test middleware rejects missing token."""
    middleware = SSEAuthMiddleware(mock_app, mock_validator, bypass_health=True)

    scope = {
        "type": "http",
        "path": "/some-endpoint",
        "headers": [],
    }

    receive = MockReceive()
    send = MockSend()

    # Execute
    await middleware(scope, receive, send)

    # Verify - should send 401
    assert len(send.events) > 0
    start_event = send.events[0]
    assert start_event["type"] == "http.response.start"
    assert start_event["status"] == 401


@pytest.mark.asyncio
async def test_middleware_invalid_token(mock_validator, mock_app):
    """Test middleware rejects invalid token."""
    mock_validator.validate_token.side_effect = TokenValidationError("Invalid token")

    middleware = SSEAuthMiddleware(mock_app, mock_validator, bypass_health=True)

    scope = {
        "type": "http",
        "path": "/some-endpoint",
        "headers": [(b"authorization", b"Bearer invalid-token")],
    }

    receive = MockReceive()
    send = MockSend()

    # Execute
    await middleware(scope, receive, send)

    # Verify - should send 401
    assert len(send.events) > 0
    start_event = send.events[0]
    assert start_event["type"] == "http.response.start"
    assert start_event["status"] == 401


@pytest.mark.asyncio
async def test_middleware_bypasses_health_endpoint(mock_validator, mock_app):
    """Test middleware bypasses health endpoint."""
    middleware = SSEAuthMiddleware(mock_app, mock_validator, bypass_health=True)

    scope = {
        "type": "http",
        "path": "/",
        "headers": [],
    }

    receive = MockReceive()
    send = MockSend()

    # Execute
    await middleware(scope, receive, send)

    # Verify - should call app without validation
    mock_validator.validate_token.assert_not_called()
    mock_app.assert_called_once()
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_sse_auth.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Create SSE auth middleware implementation**

Create `src/heblo_mcp/sse_auth.py`:

```python
"""SSE authentication middleware for HebloMCP."""

import json
from typing import Callable, Optional

from heblo_mcp.token_validator import TokenValidator, TokenValidationError
from heblo_mcp.user_context import UserContext


def _extract_bearer_token(headers: list[tuple[bytes, bytes]]) -> Optional[str]:
    """Extract Bearer token from Authorization header.

    Args:
        headers: List of (name, value) header tuples

    Returns:
        Token string if found, None otherwise
    """
    for name, value in headers:
        if name.lower() == b"authorization":
            auth_value = value.decode("utf-8")
            if auth_value.startswith("Bearer "):
                return auth_value[7:]  # Remove "Bearer " prefix
    return None


class SSEAuthMiddleware:
    """ASGI middleware for SSE authentication.

    Validates Bearer tokens from Authorization header and attaches
    user context to request scope.
    """

    def __init__(
        self,
        app: Callable,
        token_validator: TokenValidator,
        bypass_health: bool = True
    ):
        """Initialize middleware.

        Args:
            app: ASGI application
            token_validator: Token validator instance
            bypass_health: If True, bypass auth for health endpoint (/)
        """
        self.app = app
        self.token_validator = token_validator
        self.bypass_health = bypass_health

    async def __call__(self, scope, receive, send):
        """ASGI middleware callable.

        Args:
            scope: ASGI scope dict
            receive: ASGI receive callable
            send: ASGI send callable
        """
        # Only process HTTP requests
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Bypass health endpoint if configured
        if self.bypass_health and scope.get("path") == "/":
            await self.app(scope, receive, send)
            return

        # Extract token
        headers = scope.get("headers", [])
        token = _extract_bearer_token(headers)

        if not token:
            # No token - send 401
            await self._send_401(
                send,
                "Authentication required. Please provide Bearer token."
            )
            return

        try:
            # Validate token
            user_ctx = await self.token_validator.validate_token(token)

            # Attach user context to scope
            scope["user"] = user_ctx

            # Call next middleware/app
            await self.app(scope, receive, send)

        except TokenValidationError as e:
            # Invalid token - send 401
            await self._send_401(send, str(e))

    async def _send_401(self, send: Callable, message: str):
        """Send 401 Unauthorized response.

        Args:
            send: ASGI send callable
            message: Error message
        """
        body = json.dumps({"error": message}).encode("utf-8")

        await send({
            "type": "http.response.start",
            "status": 401,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("utf-8")),
            ],
        })

        await send({
            "type": "http.response.body",
            "body": body,
        })
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_sse_auth.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/heblo_mcp/sse_auth.py tests/unit/test_sse_auth.py
git commit -m "feat: add SSE authentication middleware"
```

---

## Task 7: Update Server Creation for SSE Auth

**Files:**
- Modify: `src/heblo_mcp/server.py:13-88`
- Test: `tests/integration/test_server.py`

**Step 1: Write failing test for SSE server with auth**

Add to `tests/integration/test_server.py`:

```python
@pytest.mark.asyncio
async def test_create_sse_server_with_auth():
    """Test creating SSE server with authentication middleware."""
    config = HebloMCPConfig(
        tenant_id="test-tenant",
        client_id="test-client",
        transport="sse",
        sse_auth_enabled=True
    )

    server = await create_server(config)

    # Server should be created successfully
    assert server is not None
    # Note: Can't easily test middleware is attached without actually making requests


@pytest.mark.asyncio
async def test_create_stdio_server_without_auth():
    """Test creating stdio server without SSE auth middleware."""
    config = HebloMCPConfig(
        tenant_id="test-tenant",
        client_id="test-client",
        transport="stdio",
    )

    server = await create_server(config)

    # Server should be created successfully
    assert server is not None
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/integration/test_server.py::test_create_sse_server_with_auth -v`
Expected: Test may pass but doesn't verify auth middleware (we'll verify manually)

**Step 3: Update server.py to add conditional middleware**

Modify `src/heblo_mcp/server.py`:

```python
"""HebloMCP server creation and configuration."""

import httpx
from fastmcp import FastMCP

from heblo_mcp import __version__
from heblo_mcp.auth import HebloAuth, MSALBearerAuth
from heblo_mcp.auth_mode import detect_transport_mode
from heblo_mcp.config import HebloMCPConfig
from heblo_mcp.routes import get_route_maps
from heblo_mcp.spec import fetch_and_patch_spec
from heblo_mcp.sse_auth import SSEAuthMiddleware
from heblo_mcp.token_validator import TokenValidator


async def create_server(config: HebloMCPConfig | None = None) -> FastMCP:
    """Create and configure the HebloMCP FastMCP server.

    Args:
        config: Configuration object (defaults to loading from environment)

    Returns:
        Configured FastMCP server instance
    """
    # Load configuration
    if config is None:
        config = HebloMCPConfig()

    # Detect transport mode
    transport = detect_transport_mode(config)

    # Set up authentication based on transport mode
    if transport == "stdio":
        # Stdio mode: Use existing local auth with token cache
        auth = HebloAuth(
            tenant_id=config.tenant_id,
            client_id=config.client_id,
            scope=config.api_scope,
            cache_path=config.token_cache_path,
        )
        bearer_auth = MSALBearerAuth(auth)

        # Create HTTP client with authentication
        client = httpx.AsyncClient(
            base_url=config.api_base_url,
            auth=bearer_auth,
            timeout=60.0,
        )
    else:
        # SSE mode: Auth handled by middleware, client uses token from request context
        # For now, create client without auth (will be added per-request)
        client = httpx.AsyncClient(
            base_url=config.api_base_url,
            timeout=60.0,
        )

    # Fetch and patch OpenAPI spec
    spec = await fetch_and_patch_spec(config.openapi_spec_url)

    # Create FastMCP server from OpenAPI spec
    mcp = FastMCP.from_openapi(
        openapi_spec=spec,
        client=client,
        name="Heblo MCP",
        route_maps=get_route_maps(),
    )

    # Add SSE authentication middleware if in SSE mode
    if transport == "sse" and config.sse_auth_enabled:
        token_validator = TokenValidator(
            tenant_id=config.tenant_id,
            audience=config.client_id,
            jwks_cache_ttl=config.jwks_cache_ttl,
        )

        # Wrap the FastMCP app with auth middleware
        # Note: This requires access to the underlying ASGI app
        # FastMCP may need to expose this or we may need to wrap differently
        if hasattr(mcp, 'app'):
            mcp.app = SSEAuthMiddleware(
                mcp.app,
                token_validator,
                bypass_health=True
            )

    return mcp


# Create the default server instance for FastMCP CLI
mcp = None  # Will be initialized when needed


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
            "version": __version__,
            "transport": config.transport if config else "auto"
        }

    return mcp


async def get_mcp_server() -> FastMCP:
    """Get or create the MCP server instance.

    This is used by the FastMCP CLI and __main__.py entry point.
    """
    global mcp
    if mcp is None:
        mcp = await create_server()
    return mcp
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/integration/test_server.py -v`
Expected: Tests PASS

**Step 5: Commit**

```bash
git add src/heblo_mcp/server.py tests/integration/test_server.py
git commit -m "feat: add conditional SSE auth middleware to server"
```

---

## Task 8: Add Per-Request Token Injection for SSE Mode

**Files:**
- Create: `src/heblo_mcp/sse_bearer_auth.py`
- Modify: `src/heblo_mcp/server.py:38-48`
- Create: `tests/unit/test_sse_bearer_auth.py`

**Step 1: Write failing test for SSE bearer auth**

Create `tests/unit/test_sse_bearer_auth.py`:

```python
"""Tests for SSE bearer auth that uses request context."""

import httpx
import pytest
from unittest.mock import Mock
from heblo_mcp.sse_bearer_auth import SSEBearerAuth
from heblo_mcp.user_context import UserContext


def test_sse_bearer_auth_adds_token():
    """Test that SSE bearer auth adds token from user context."""
    user_ctx = UserContext(
        email="user@example.com",
        tenant_id="test-tenant",
        object_id="obj-123",
        token="user-token-123"
    )

    auth = SSEBearerAuth()
    request = httpx.Request("GET", "https://api.example.com/test")

    # Simulate ASGI scope attached to request
    # In real usage, this would come from middleware
    request.extensions = {"user_context": user_ctx}

    # Apply auth
    flow = auth.auth_flow(request)
    authed_request = next(flow)

    # Verify Authorization header was added
    assert "Authorization" in authed_request.headers
    assert authed_request.headers["Authorization"] == "Bearer user-token-123"


def test_sse_bearer_auth_no_context():
    """Test that SSE bearer auth handles missing user context."""
    auth = SSEBearerAuth()
    request = httpx.Request("GET", "https://api.example.com/test")

    # No user context in extensions
    request.extensions = {}

    # Apply auth - should not add header
    flow = auth.auth_flow(request)
    authed_request = next(flow)

    # No Authorization header should be added
    assert "Authorization" not in authed_request.headers
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_sse_bearer_auth.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Create SSE bearer auth implementation**

Create `src/heblo_mcp/sse_bearer_auth.py`:

```python
"""Bearer auth for SSE mode that uses user context from request."""

from typing import Generator

import httpx


class SSEBearerAuth(httpx.Auth):
    """httpx Auth handler for SSE mode.

    Extracts user token from request context (set by SSEAuthMiddleware)
    and adds it to the Authorization header for Heblo API calls.
    """

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        """Implement httpx auth flow.

        Args:
            request: The outgoing HTTP request

        Yields:
            Request with Authorization header if user context available
        """
        # Try to get user context from request extensions
        # This is set by SSEAuthMiddleware
        user_ctx = request.extensions.get("user_context")

        if user_ctx and hasattr(user_ctx, "token"):
            # Add Bearer token to request
            request.headers["Authorization"] = f"Bearer {user_ctx.token}"

        # Send request
        yield request
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_sse_bearer_auth.py -v`
Expected: All tests PASS

**Step 5: Update server.py to use SSEBearerAuth**

Modify `src/heblo_mcp/server.py` to import and use SSEBearerAuth:

```python
from heblo_mcp.sse_bearer_auth import SSEBearerAuth

# ... in create_server function, SSE mode section:

    else:
        # SSE mode: Auth handled by middleware, client uses token from request context
        sse_auth = SSEBearerAuth()

        client = httpx.AsyncClient(
            base_url=config.api_base_url,
            auth=sse_auth,
            timeout=60.0,
        )
```

**Step 6: Run tests to verify they pass**

Run: `pytest tests/integration/test_server.py -v`
Expected: Tests PASS

**Step 7: Commit**

```bash
git add src/heblo_mcp/sse_bearer_auth.py tests/unit/test_sse_bearer_auth.py src/heblo_mcp/server.py
git commit -m "feat: add SSE bearer auth for per-request token injection"
```

---

## Task 9: Add Integration Tests

**Files:**
- Create: `tests/integration/test_sse_auth_integration.py`

**Step 1: Write integration tests**

Create `tests/integration/test_sse_auth_integration.py`:

```python
"""Integration tests for SSE authentication."""

import pytest
from unittest.mock import AsyncMock, patch, Mock
from heblo_mcp.config import HebloMCPConfig
from heblo_mcp.server import create_server
from tests.fixtures.jwt_fixtures import create_test_jwt, create_test_rsa_keypair


@pytest.fixture
def rsa_keys():
    """Create RSA key pair for testing."""
    return create_test_rsa_keypair()


@pytest.mark.asyncio
async def test_sse_server_accepts_valid_token(rsa_keys):
    """Test that SSE server accepts valid token."""
    private_key, _ = rsa_keys

    # Create config for SSE mode
    config = HebloMCPConfig(
        tenant_id="test-tenant",
        client_id="test-client",
        transport="sse",
        sse_auth_enabled=True
    )

    # Create token
    token = create_test_jwt(
        tenant_id="test-tenant",
        client_id="test-client",
        email="user@example.com",
        private_key=private_key
    )

    # Mock OpenAPI spec fetching
    with patch('heblo_mcp.server.fetch_and_patch_spec', new=AsyncMock(return_value={})):
        server = await create_server(config)

        # Verify server was created
        assert server is not None


@pytest.mark.asyncio
async def test_stdio_server_unchanged():
    """Test that stdio server creation is unchanged."""
    config = HebloMCPConfig(
        tenant_id="test-tenant",
        client_id="test-client",
        transport="stdio"
    )

    # Mock token cache existence
    with patch('heblo_mcp.auth.Path.exists', return_value=True):
        with patch('heblo_mcp.auth.Path.read_text', return_value='{}'):
            with patch('heblo_mcp.server.fetch_and_patch_spec', new=AsyncMock(return_value={})):
                server = await create_server(config)

                # Verify server was created
                assert server is not None
```

**Step 2: Run tests to verify they pass**

Run: `pytest tests/integration/test_sse_auth_integration.py -v`
Expected: Tests PASS

**Step 3: Commit**

```bash
git add tests/integration/test_sse_auth_integration.py
git commit -m "test: add integration tests for SSE authentication"
```

---

## Task 10: Update README Documentation

**Files:**
- Modify: `README.md:227-257`

**Step 1: Add SSE authentication documentation to README**

Add after the "Run Server (SSE mode - cloud/remote)" section in README.md:

```markdown
### SSE Mode Authentication

When deployed in SSE mode, HebloMCP requires OAuth authentication for security.

**How it works:**
1. Claude Code client initiates Azure AD device code flow
2. User authenticates in browser with Microsoft account
3. Client sends Bearer token in Authorization header with each request
4. Server validates JWT token using Azure AD public keys
5. Server uses user's token for all Heblo API calls

**Configuration:**

Add to your Claude Code MCP config:

```json
{
  "mcpServers": {
    "heblo": {
      "url": "https://heblo-mcp.azurewebsites.net",
      "transport": "sse",
      "auth": {
        "type": "oauth",
        "tenant_id": "your-tenant-id",
        "client_id": "your-client-id",
        "scope": "api://8b34be89-cef4-445a-929a-bc1a21dce0cb/access_as_user"
      }
    }
  }
}
```

**Server Environment Variables:**

```bash
HEBLO_TRANSPORT=sse
HEBLO_SSE_AUTH_ENABLED=true
HEBLO_TENANT_ID=your-tenant-id
HEBLO_CLIENT_ID=your-client-id
```

**Security:**
- Each user authenticates with their own Microsoft account
- User-level audit trail in Heblo API
- Stateless token validation (no server sessions)
- Health endpoint (/) bypasses auth for Azure monitoring
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add SSE authentication documentation to README"
```

---

## Task 11: Run Full Test Suite

**Step 1: Run all tests**

Run: `pytest tests/ -v --cov=src/heblo_mcp --cov-report=term-missing`
Expected: All tests PASS with 95%+ coverage for auth modules

**Step 2: Fix any failing tests**

If tests fail, investigate and fix. Commit fixes with descriptive messages.

**Step 3: Run linting**

Run: `black src/ tests/ && ruff check src/ tests/`
Expected: No issues

**Step 4: Commit any formatting changes**

```bash
git add src/ tests/
git commit -m "style: apply black and ruff formatting"
```

---

## Task 12: Manual Testing

**Step 1: Test stdio mode still works**

```bash
# Set environment variables
export HEBLO_TENANT_ID=your-tenant-id
export HEBLO_CLIENT_ID=your-client-id
export HEBLO_TRANSPORT=stdio

# Run login
heblo-mcp login

# Verify token cache created
ls ~/.config/heblo-mcp/token_cache.json
```

Expected: Device code flow works, token cached

**Step 2: Test SSE mode with mock token**

```bash
# Set environment variables
export HEBLO_TENANT_ID=your-tenant-id
export HEBLO_CLIENT_ID=your-client-id
export HEBLO_TRANSPORT=sse
export HEBLO_SSE_AUTH_ENABLED=true

# Start server
heblo-mcp serve-sse
```

Expected: Server starts on port 8000

**Step 3: Test health endpoint bypasses auth**

```bash
curl http://localhost:8000/
```

Expected: Returns health status without requiring auth

**Step 4: Document any issues**

Create issues for any problems found during manual testing.

---

## Success Criteria

- ✓ All unit tests pass
- ✓ All integration tests pass
- ✓ Test coverage >95% for auth modules
- ✓ Stdio mode unchanged and working
- ✓ SSE mode validates tokens
- ✓ Health endpoint bypasses auth
- ✓ Documentation updated
- ✓ No breaking changes to existing deployments

---

## Notes for Implementation

**Key Principles:**
- **TDD**: Write failing tests first, then implement
- **YAGNI**: Only implement what's needed per the design
- **DRY**: Reuse JWT fixtures across tests
- **Frequent commits**: Commit after each task

**Testing Strategy:**
- Unit tests for each component in isolation
- Mock external dependencies (JWKS, Azure AD)
- Integration tests for end-to-end flows
- Backward compatibility tests for stdio mode

**Security:**
- Never log token values
- Validate all JWT claims (aud, iss, exp)
- Use well-tested libraries (PyJWT, cryptography)
- Cache JWKS with reasonable TTL

**Deployment:**
- Set `HEBLO_TRANSPORT=sse` in Azure Web App
- Set `HEBLO_SSE_AUTH_ENABLED=true`
- Health endpoint must work without auth for Azure probes
