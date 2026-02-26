"""Unit tests for configuration module."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from heblo_mcp.config import HebloMCPConfig


def test_config_default_values(monkeypatch, tmp_path):
    """Test that configuration has correct default values."""
    # Clear env to test actual defaults
    monkeypatch.delenv("HEBLO_TENANT_ID", raising=False)
    monkeypatch.delenv("HEBLO_CLIENT_ID", raising=False)
    monkeypatch.delenv("HEBLO_API_SCOPE", raising=False)
    # Change to non-existent directory to avoid loading .env
    monkeypatch.chdir(tmp_path)

    config = HebloMCPConfig(
        tenant_id="test-tenant",
        client_id="test-client",
    )

    assert config.tenant_id == "test-tenant"
    assert config.client_id == "test-client"
    # Default scope from config.py
    assert config.api_scope == "api://8b34be89-cef4-445a-929a-bc1a21dce0cb/access_as_user"
    assert config.api_base_url == "https://heblo.anela.cz"
    assert config.openapi_spec_url == "https://heblo.stg.anela.cz/swagger/v1/swagger.json"
    assert isinstance(config.token_cache_path, Path)


def test_config_required_fields(monkeypatch, tmp_path):
    """Test that required fields are validated."""
    # Clear all env vars that might provide defaults
    monkeypatch.delenv("HEBLO_TENANT_ID", raising=False)
    monkeypatch.delenv("HEBLO_CLIENT_ID", raising=False)
    monkeypatch.delenv("HEBLO_API_SCOPE", raising=False)
    # Change to non-existent directory to avoid loading .env
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValidationError) as exc_info:
        HebloMCPConfig()

    errors = exc_info.value.errors()
    assert len(errors) >= 2  # At least tenant_id and client_id
    error_fields = {e["loc"][0] for e in errors}
    assert "tenant_id" in error_fields
    assert "client_id" in error_fields


def test_config_custom_values(tmp_path: Path):
    """Test that custom values can be set."""
    custom_cache = tmp_path / "custom_cache.json"

    config = HebloMCPConfig(
        tenant_id="custom-tenant",
        client_id="custom-client",
        api_scope="custom-scope",
        api_base_url="https://custom.example.com",
        openapi_spec_url="https://custom.example.com/spec.json",
        token_cache_path=custom_cache,
    )

    assert config.tenant_id == "custom-tenant"
    assert config.client_id == "custom-client"
    assert config.api_scope == "custom-scope"
    assert config.api_base_url == "https://custom.example.com"
    assert config.openapi_spec_url == "https://custom.example.com/spec.json"
    assert config.token_cache_path == custom_cache


def test_config_creates_cache_directory(tmp_path: Path):
    """Test that configuration creates token cache directory."""
    cache_path = tmp_path / "nested" / "dir" / "cache.json"

    config = HebloMCPConfig(
        tenant_id="test-tenant",
        client_id="test-client",
        token_cache_path=cache_path,
    )

    assert config.token_cache_path.parent.exists()
    assert config.token_cache_path.parent.is_dir()


def test_config_from_env(monkeypatch, tmp_path: Path):
    """Test that configuration can be loaded from environment variables."""
    cache_path = tmp_path / "cache.json"

    monkeypatch.setenv("HEBLO_TENANT_ID", "env-tenant")
    monkeypatch.setenv("HEBLO_CLIENT_ID", "env-client")
    monkeypatch.setenv("HEBLO_API_SCOPE", "env-scope")
    monkeypatch.setenv("HEBLO_API_BASE_URL", "https://env.example.com")
    monkeypatch.setenv("HEBLO_TOKEN_CACHE_PATH", str(cache_path))

    config = HebloMCPConfig()

    assert config.tenant_id == "env-tenant"
    assert config.client_id == "env-client"
    assert config.api_scope == "env-scope"
    assert config.api_base_url == "https://env.example.com"
