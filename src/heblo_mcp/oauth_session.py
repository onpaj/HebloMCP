"""OAuth session storage for authorization code flow proxy.

Manages temporary storage of OAuth state, PKCE challenges, and authorization codes
during the OAuth flow between Claude Desktop and Azure AD.
"""

import secrets
import time
from dataclasses import dataclass
from threading import Lock
from typing import Dict, Optional


@dataclass
class OAuthState:
    """OAuth authorization request state."""

    code_challenge: str
    code_challenge_method: str
    redirect_uri: str
    scope: str
    created_at: float


@dataclass
class ProxyCode:
    """Proxy authorization code mapping to Azure AD token."""

    access_token: str
    code_challenge: str  # Store to verify against code_verifier
    created_at: float


class OAuthSessionStore:
    """Thread-safe in-memory storage for OAuth flow state.

    Stores temporary OAuth state and proxy codes with automatic expiration.
    Not suitable for multi-instance deployments (use Redis/database for that).
    """

    def __init__(self, state_ttl: int = 600, code_ttl: int = 300):
        """Initialize session store.

        Args:
            state_ttl: Time-to-live for OAuth state in seconds (default: 10 min)
            code_ttl: Time-to-live for proxy codes in seconds (default: 5 min)
        """
        self.state_ttl = state_ttl
        self.code_ttl = code_ttl

        self._states: Dict[str, OAuthState] = {}
        self._codes: Dict[str, ProxyCode] = {}
        self._lock = Lock()

    def store_state(
        self,
        state: str,
        code_challenge: str,
        code_challenge_method: str,
        redirect_uri: str,
        scope: str,
    ) -> None:
        """Store OAuth authorization request state.

        Args:
            state: OAuth state parameter
            code_challenge: PKCE code challenge
            code_challenge_method: PKCE challenge method (S256)
            redirect_uri: Claude Desktop callback URI
            scope: Requested OAuth scopes
        """
        with self._lock:
            self._cleanup_expired_states()
            self._states[state] = OAuthState(
                code_challenge=code_challenge,
                code_challenge_method=code_challenge_method,
                redirect_uri=redirect_uri,
                scope=scope,
                created_at=time.time(),
            )

    def get_state(self, state: str) -> Optional[OAuthState]:
        """Retrieve and remove OAuth state.

        Args:
            state: OAuth state parameter

        Returns:
            OAuthState if found and not expired, None otherwise
        """
        with self._lock:
            self._cleanup_expired_states()
            return self._states.pop(state, None)

    def create_proxy_code(self, access_token: str, code_challenge: str) -> str:
        """Create proxy authorization code for Azure AD token.

        Args:
            access_token: Azure AD access token
            code_challenge: PKCE code challenge to verify later

        Returns:
            Generated proxy authorization code
        """
        proxy_code = secrets.token_urlsafe(32)

        with self._lock:
            self._cleanup_expired_codes()
            self._codes[proxy_code] = ProxyCode(
                access_token=access_token,
                code_challenge=code_challenge,
                created_at=time.time(),
            )

        return proxy_code

    def exchange_code(self, code: str, code_verifier: str) -> Optional[str]:
        """Exchange proxy code for access token and verify PKCE.

        Args:
            code: Proxy authorization code
            code_verifier: PKCE code verifier

        Returns:
            Access token if code is valid and PKCE verified, None otherwise
        """
        with self._lock:
            self._cleanup_expired_codes()
            proxy_code = self._codes.pop(code, None)

            if not proxy_code:
                return None

            # Verify PKCE challenge
            import base64
            import hashlib

            # Compute challenge from verifier
            challenge = (
                base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest())
                .decode()
                .rstrip("=")
            )

            if challenge != proxy_code.code_challenge:
                return None

            return proxy_code.access_token

    def _cleanup_expired_states(self) -> None:
        """Remove expired OAuth states (must be called with lock held)."""
        now = time.time()
        expired = [
            state for state, data in self._states.items() if now - data.created_at > self.state_ttl
        ]
        for state in expired:
            del self._states[state]

    def _cleanup_expired_codes(self) -> None:
        """Remove expired proxy codes (must be called with lock held)."""
        now = time.time()
        expired = [
            code for code, data in self._codes.items() if now - data.created_at > self.code_ttl
        ]
        for code in expired:
            del self._codes[code]
