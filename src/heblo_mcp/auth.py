"""Authentication handling for HebloMCP using MSAL device code flow."""

import json
from pathlib import Path
from typing import Generator

import httpx
import msal


class HebloAuth:
    """Manages Azure AD authentication using MSAL device code flow.

    Handles token acquisition, caching, and silent renewal. Tokens are cached
    to disk for reuse across sessions.
    """

    def __init__(self, tenant_id: str, client_id: str, scope: str, cache_path: Path):
        """Initialize MSAL authentication.

        Args:
            tenant_id: Azure AD tenant ID
            client_id: Azure AD application (client) ID
            scope: API scope (e.g., api://xxx/access_as_user)
            cache_path: Path to token cache file
        """
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.scope = scope
        self.cache_path = cache_path

        # Initialize token cache
        self.cache = msal.SerializableTokenCache()
        if cache_path.exists():
            self.cache.deserialize(cache_path.read_text())

        # Create MSAL public client application
        authority = f"https://login.microsoftonline.com/{tenant_id}"
        self.app = msal.PublicClientApplication(
            client_id=client_id,
            authority=authority,
            token_cache=self.cache,
        )

    def _save_cache(self) -> None:
        """Persist token cache to disk if it has changed."""
        if self.cache.has_state_changed:
            self.cache_path.write_text(self.cache.serialize())

    def login(self) -> dict:
        """Perform interactive device code authentication.

        Displays a URL and code for the user to visit in a browser.
        Waits for the user to complete authentication.

        Returns:
            Authentication result with access token

        Raises:
            Exception: If authentication fails
        """
        flow = self.app.initiate_device_flow(scopes=[self.scope])

        if "user_code" not in flow:
            raise Exception(f"Failed to create device flow: {flow.get('error_description')}")

        # Display instructions to user
        print("\n" + "=" * 70)
        print("DEVICE CODE AUTHENTICATION")
        print("=" * 70)
        print(f"\n{flow['message']}\n")
        print("=" * 70 + "\n")

        # Wait for user to complete authentication
        result = self.app.acquire_token_by_device_flow(flow)

        if "access_token" not in result:
            error = result.get("error_description", result.get("error", "Unknown error"))
            raise Exception(f"Authentication failed: {error}")

        self._save_cache()
        return result

    def get_token(self) -> str:
        """Get access token, using cached token if available.

        Attempts silent token acquisition from cache first. If no cached token
        is available, raises an exception - user must call login() first.

        Returns:
            Access token string

        Raises:
            Exception: If no cached token is available
        """
        # Try to get token silently from cache
        accounts = self.app.get_accounts()

        if accounts:
            # Use the first account (device code flow typically has one account)
            result = self.app.acquire_token_silent(scopes=[self.scope], account=accounts[0])

            if result and "access_token" in result:
                self._save_cache()
                return result["access_token"]

        # No cached token available
        raise Exception(
            "No cached authentication token found. "
            "Please run 'heblo-mcp login' to authenticate."
        )


class MSALBearerAuth(httpx.Auth):
    """httpx Auth handler that injects Bearer tokens and handles 401 retries.

    Uses HebloAuth to obtain fresh tokens on-demand and automatically retries
    requests that fail with 401 Unauthorized.
    """

    def __init__(self, heblo_auth: HebloAuth):
        """Initialize Bearer auth handler.

        Args:
            heblo_auth: HebloAuth instance for token acquisition
        """
        self.heblo_auth = heblo_auth

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        """Implement httpx auth flow with Bearer token injection and 401 retry.

        Args:
            request: The outgoing HTTP request

        Yields:
            Request with Authorization header, handles 401 retries
        """
        # Get fresh token and inject into request
        token = self.heblo_auth.get_token()
        request.headers["Authorization"] = f"Bearer {token}"

        # Send request
        response = yield request

        # If 401, try to get a fresh token and retry once
        if response.status_code == 401:
            # Clear the cached token by forcing a new silent acquisition
            token = self.heblo_auth.get_token()
            request.headers["Authorization"] = f"Bearer {token}"
            yield request
