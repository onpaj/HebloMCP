"""Pytest configuration and shared fixtures for HebloMCP tests."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import httpx
import pytest
from msal import PublicClientApplication, SerializableTokenCache

from heblo_mcp.auth import HebloAuth
from heblo_mcp.config import HebloMCPConfig


@pytest.fixture
def temp_token_cache(tmp_path: Path) -> Path:
    """Provide a temporary token cache path for testing.

    Args:
        tmp_path: Pytest temporary directory fixture

    Returns:
        Path to temporary token cache file
    """
    cache_path = tmp_path / "token_cache.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    return cache_path


@pytest.fixture
def mock_config(temp_token_cache: Path) -> HebloMCPConfig:
    """Provide a mock HebloMCP configuration for testing.

    Args:
        temp_token_cache: Temporary token cache path

    Returns:
        Mock configuration instance
    """
    return HebloMCPConfig(
        tenant_id="test-tenant-id",
        client_id="test-client-id",
        api_scope="api://test/access_as_user",
        api_base_url="https://test.example.com",
        openapi_spec_url="https://test.example.com/swagger.json",
        token_cache_path=temp_token_cache,
    )


@pytest.fixture
def mock_msal_app(monkeypatch) -> Mock:
    """Provide a mocked MSAL PublicClientApplication.

    Args:
        monkeypatch: Pytest monkeypatch fixture

    Returns:
        Mock MSAL application
    """
    mock_app = Mock(spec=PublicClientApplication)

    # Mock successful token acquisition
    mock_app.acquire_token_silent.return_value = {
        "access_token": "mock-access-token",
        "token_type": "Bearer",
        "expires_in": 3600,
    }

    # Mock account retrieval
    mock_app.get_accounts.return_value = [
        {"username": "test@example.com", "home_account_id": "test-account-id"}
    ]

    # Mock device flow
    mock_app.initiate_device_flow.return_value = {
        "user_code": "TEST123",
        "device_code": "device-code-123",
        "verification_uri": "https://microsoft.com/devicelogin",
        "message": "Go to https://microsoft.com/devicelogin and enter TEST123",
    }

    mock_app.acquire_token_by_device_flow.return_value = {
        "access_token": "new-mock-token",
        "token_type": "Bearer",
        "expires_in": 3600,
    }

    # Patch MSAL constructor
    def mock_pca_constructor(*args, **kwargs):
        return mock_app

    monkeypatch.setattr(
        "heblo_mcp.auth.msal.PublicClientApplication",
        mock_pca_constructor,
    )

    return mock_app


@pytest.fixture
def mock_token_cache(monkeypatch) -> Mock:
    """Provide a mocked MSAL token cache.

    Args:
        monkeypatch: Pytest monkeypatch fixture

    Returns:
        Mock token cache
    """
    mock_cache = Mock(spec=SerializableTokenCache)
    mock_cache.has_state_changed = False
    mock_cache.serialize.return_value = json.dumps({"test": "cache"})

    monkeypatch.setattr(
        "heblo_mcp.auth.msal.SerializableTokenCache",
        lambda: mock_cache,
    )

    return mock_cache


@pytest.fixture
def mock_heblo_auth(
    mock_config: HebloMCPConfig, mock_msal_app: Mock, mock_token_cache: Mock
) -> HebloAuth:
    """Provide a mock HebloAuth instance with mocked MSAL.

    Args:
        mock_config: Mock configuration
        mock_msal_app: Mock MSAL application
        mock_token_cache: Mock token cache

    Returns:
        HebloAuth instance with mocked dependencies
    """
    return HebloAuth(
        tenant_id=mock_config.tenant_id,
        client_id=mock_config.client_id,
        scope=mock_config.api_scope,
        cache_path=mock_config.token_cache_path,
    )


@pytest.fixture
def sample_openapi_spec() -> dict[str, Any]:
    """Provide a sample OpenAPI spec for testing.

    Returns:
        Sample OpenAPI specification dictionary
    """
    return {
        "openapi": "3.0.1",
        "info": {
            "title": "Heblo API",
            "version": "1.0",
        },
        "paths": {
            "/api/Catalog": {
                "get": {
                    "tags": ["Catalog"],
                    "parameters": [
                        {
                            "name": "ProductTypes",
                            "in": "query",
                            "schema": {
                                "type": "array",
                                "items": {"$ref": "#/components/schemas/ProductType"},
                            },
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Success",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/CatalogListResponse"}
                                }
                            },
                        }
                    },
                }
            },
            "/api/Catalog/{productCode}/composition": {
                "get": {
                    "tags": ["Catalog"],
                    "parameters": [
                        {
                            "name": "productCode",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Success",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/CompositionResponse"}
                                }
                            },
                        }
                    },
                }
            },
        },
        "components": {
            "schemas": {
                "ProductType": {
                    "enum": [
                        "UNDEFINED",
                        "Goods",
                        "Material",
                        "SemiProduct",
                        "Product",
                        "Set",
                    ],
                    "type": "string",
                },
                "ErrorCodes": {
                    "enum": ["ERROR_1", "ERROR_2", "ERROR_3"],
                    "type": "string",
                },
                "IssuedInvoiceErrorType": {
                    "enum": ["TYPE_1", "TYPE_2"],
                    "type": "string",
                },
                "DateOnly": {
                    "type": "object",
                    "properties": {
                        "year": {"type": "integer"},
                        "month": {"type": "integer"},
                        "day": {"type": "integer"},
                    },
                },
                "CatalogListResponse": {
                    "type": "object",
                    "properties": {
                        "data": {"type": "array"},
                        "errorCode": {"$ref": "#/components/schemas/ErrorCodes"},
                    },
                },
                "CompositionResponse": {
                    "type": "object",
                    "properties": {
                        "composition": {"type": "array"},
                        "errorCode": {"$ref": "#/components/schemas/ErrorCodes"},
                    },
                },
            }
        },
    }


@pytest.fixture
def mock_httpx_client() -> Mock:
    """Provide a mocked httpx AsyncClient.

    Returns:
        Mock httpx client
    """
    client = Mock(spec=httpx.AsyncClient)

    # Mock successful API responses
    async def mock_get(*args, **kwargs):
        response = Mock(spec=httpx.Response)
        response.status_code = 200
        response.json.return_value = {
            "data": [],
            "errorCode": None,
        }
        return response

    client.get = mock_get

    return client
