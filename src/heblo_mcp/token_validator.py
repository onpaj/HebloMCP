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
            # Decode header to get kid
            unverified_header = jwt.get_unverified_header(token)

            # Get signing key from JWKS
            jwks = await self._get_jwks()

            # Find the matching key
            signing_key = None
            for key_data in jwks.get("keys", []):
                if unverified_header.get("kid") == key_data.get("kid") or not unverified_header.get("kid"):
                    # Convert JWK to public key
                    from jwt import PyJWK
                    signing_key = PyJWK(key_data).key
                    break

            if not signing_key:
                raise TokenValidationError("Unable to find matching signing key in JWKS")

            # Validate and decode token
            payload = jwt.decode(
                token,
                signing_key,
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
