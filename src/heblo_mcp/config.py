"""Configuration management for HebloMCP server."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


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
