"""OAuth 2.0 proxy endpoints for Claude Desktop authentication.

Proxies OAuth authorization code flow between Claude Desktop and Azure AD.
"""

import httpx
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse

from heblo_mcp.config import HebloMCPConfig
from heblo_mcp.oauth_session import OAuthSessionStore


class OAuthEndpoints:
    """OAuth 2.0 authorization code flow proxy endpoints."""

    def __init__(self, config: HebloMCPConfig, session_store: OAuthSessionStore):
        """Initialize OAuth endpoints.

        Args:
            config: HebloMCP configuration
            session_store: OAuth session storage
        """
        self.config = config
        self.session_store = session_store
        self.tenant_id = config.tenant_id
        self.client_id = config.client_id
        self.client_secret = getattr(config, "client_secret", None)

        # Azure AD OAuth endpoints
        self.azure_authorize_url = (
            f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/authorize"
        )
        self.azure_token_url = (
            f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        )

    async def authorize(self, request: Request) -> RedirectResponse:
        """/authorize endpoint - Start OAuth flow.

        Claude Desktop calls this to initiate OAuth. We proxy to Azure AD.

        Args:
            request: Starlette request with OAuth parameters

        Returns:
            Redirect to Azure AD authorization endpoint
        """
        # Extract OAuth parameters from Claude Desktop
        client_id = request.query_params.get("client_id")
        redirect_uri = request.query_params.get("redirect_uri")
        state = request.query_params.get("state")
        code_challenge = request.query_params.get("code_challenge")
        code_challenge_method = request.query_params.get("code_challenge_method")
        scope = request.query_params.get("scope", "claudeai")

        # Validate required parameters
        if not all([client_id, redirect_uri, state, code_challenge, code_challenge_method]):
            return JSONResponse(
                {"error": "invalid_request", "error_description": "Missing required OAuth parameters"},
                status_code=400,
            )

        # Validate client_id matches our configuration
        if client_id != self.client_id:
            return JSONResponse(
                {
                    "error": "invalid_client",
                    "error_description": f"Unknown client_id. Expected: {self.client_id}",
                },
                status_code=400,
            )

        # Store OAuth state for callback
        self.session_store.store_state(
            state=state,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            redirect_uri=redirect_uri,
            scope=scope,
        )

        # Build Azure AD authorization URL
        # We use our own callback URL, not Claude's
        azure_redirect_uri = str(request.url_for("oauth_callback"))

        # Map Claude Desktop scope to Azure AD scope
        # Claude sends "claudeai", we need the actual API scope
        azure_scope = self.config.api_scope

        azure_params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": azure_redirect_uri,
            "scope": azure_scope,
            "state": state,  # Pass through state to maintain session
            "response_mode": "query",
        }

        # Build authorization URL
        from urllib.parse import urlencode

        auth_url = f"{self.azure_authorize_url}?{urlencode(azure_params)}"

        return RedirectResponse(url=auth_url, status_code=302)

    async def callback(self, request: Request) -> RedirectResponse:
        """/callback endpoint - Handle Azure AD callback.

        Azure AD redirects here after user authentication. We exchange the
        code for a token and redirect back to Claude Desktop.

        Args:
            request: Starlette request with authorization code

        Returns:
            Redirect to Claude Desktop callback with proxy code
        """
        # Get authorization code and state from Azure AD
        code = request.query_params.get("code")
        state = request.query_params.get("state")
        error = request.query_params.get("error")

        # Handle Azure AD errors
        if error:
            error_description = request.query_params.get("error_description", "Unknown error")
            return JSONResponse(
                {"error": error, "error_description": error_description}, status_code=400
            )

        if not code or not state:
            return JSONResponse(
                {"error": "invalid_request", "error_description": "Missing code or state"},
                status_code=400,
            )

        # Retrieve stored OAuth state
        oauth_state = self.session_store.get_state(state)
        if not oauth_state:
            return JSONResponse(
                {
                    "error": "invalid_request",
                    "error_description": "Invalid or expired state parameter",
                },
                status_code=400,
            )

        # Exchange authorization code for access token with Azure AD
        try:
            access_token = await self._exchange_code_for_token(code, str(request.url_for("oauth_callback")))
        except Exception as e:
            return JSONResponse(
                {"error": "server_error", "error_description": f"Token exchange failed: {str(e)}"},
                status_code=500,
            )

        # Create proxy authorization code
        proxy_code = self.session_store.create_proxy_code(
            access_token=access_token, code_challenge=oauth_state.code_challenge
        )

        # Redirect back to Claude Desktop with proxy code
        from urllib.parse import urlencode

        callback_params = {"code": proxy_code, "state": state}

        callback_url = f"{oauth_state.redirect_uri}?{urlencode(callback_params)}"

        return RedirectResponse(url=callback_url, status_code=302)

    async def token(self, request: Request) -> JSONResponse:
        """/token endpoint - Exchange proxy code for access token.

        Claude Desktop calls this to exchange the proxy code for an access token.

        Args:
            request: Starlette request with token exchange parameters

        Returns:
            JSON response with access token
        """
        # Parse form data
        form = await request.form()
        grant_type = form.get("grant_type")
        code = form.get("code")
        code_verifier = form.get("code_verifier")
        client_id = form.get("client_id")

        # Validate parameters
        if grant_type != "authorization_code":
            return JSONResponse(
                {
                    "error": "unsupported_grant_type",
                    "error_description": "Only authorization_code grant type is supported",
                },
                status_code=400,
            )

        if not all([code, code_verifier, client_id]):
            return JSONResponse(
                {"error": "invalid_request", "error_description": "Missing required parameters"},
                status_code=400,
            )

        if client_id != self.client_id:
            return JSONResponse(
                {"error": "invalid_client", "error_description": "Invalid client_id"}, status_code=400
            )

        # Exchange proxy code for access token (with PKCE verification)
        access_token = self.session_store.exchange_code(code, code_verifier)

        if not access_token:
            return JSONResponse(
                {
                    "error": "invalid_grant",
                    "error_description": "Invalid authorization code or code verifier",
                },
                status_code=400,
            )

        # Return access token in OAuth 2.0 format
        return JSONResponse(
            {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": 3600,  # Azure AD tokens typically expire in 1 hour
            }
        )

    async def _exchange_code_for_token(self, code: str, redirect_uri: str) -> str:
        """Exchange authorization code for access token with Azure AD.

        Args:
            code: Authorization code from Azure AD
            redirect_uri: Redirect URI used in authorization request

        Returns:
            Access token from Azure AD

        Raises:
            Exception: If token exchange fails
        """
        if not self.client_secret:
            raise Exception(
                "Client secret not configured. Set HEBLO_CLIENT_SECRET environment variable."
            )

        # Prepare token request
        token_data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
            "scope": self.config.api_scope,
        }

        # Exchange code for token
        async with httpx.AsyncClient() as client:
            response = await client.post(self.azure_token_url, data=token_data, timeout=10.0)

            if response.status_code != 200:
                error_data = response.json()
                raise Exception(
                    f"Azure AD token exchange failed: {error_data.get('error_description', response.text)}"
                )

            token_response = response.json()
            return token_response["access_token"]
