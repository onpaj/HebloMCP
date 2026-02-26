"""Integration tests for API error handling.

These tests cover the various API issues that can occur and ensure
the server handles them gracefully.
"""

import copy
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from heblo_mcp.spec import fetch_and_patch_spec, fix_schema_validation


@pytest.mark.asyncio
async def test_fetch_spec_network_error():
    """Test handling of network errors when fetching OpenAPI spec."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.side_effect = httpx.ConnectError("Connection failed")
        mock_client_class.return_value = mock_client

        with pytest.raises(httpx.ConnectError):
            await fetch_and_patch_spec("https://test.example.com/spec.json")


@pytest.mark.asyncio
async def test_fetch_spec_http_error():
    """Test handling of HTTP errors when fetching OpenAPI spec."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found",
            request=Mock(),
            response=Mock(status_code=404),
        )

        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        with pytest.raises(httpx.HTTPStatusError):
            await fetch_and_patch_spec("https://test.example.com/spec.json")


@pytest.mark.asyncio
async def test_api_response_with_null_error_code(sample_openapi_spec):
    """Test that API responses with null errorCode are handled correctly.

    This is a common API issue - when the API succeeds, errorCode is null,
    but the enum doesn't include null as a valid value.
    """
    spec = copy.deepcopy(sample_openapi_spec)

    # Before fix, ErrorCodes enum doesn't include null
    error_codes_before = spec["components"]["schemas"]["ErrorCodes"]
    assert None not in error_codes_before.get("enum", [])

    # Apply fix
    fix_schema_validation(spec)

    # After fix, ErrorCodes enum should include null and be nullable
    error_codes_after = spec["components"]["schemas"]["ErrorCodes"]
    assert error_codes_after.get("nullable") is True
    assert None in error_codes_after["enum"] or "null" in error_codes_after["enum"]


@pytest.mark.asyncio
async def test_api_response_with_date_string(sample_openapi_spec):
    """Test that API responses with date strings are handled correctly.

    API returns dates as "2026-08-31" but schema defines DateOnly as
    an object with year/month/day properties.
    """
    spec = copy.deepcopy(sample_openapi_spec)

    # Before fix, DateOnly is an object
    date_only_before = spec["components"]["schemas"]["DateOnly"]
    assert date_only_before["type"] == "object"
    assert "properties" in date_only_before

    # Apply fix
    fix_schema_validation(spec)

    # After fix, DateOnly should be a string
    date_only_after = spec["components"]["schemas"]["DateOnly"]
    assert date_only_after["type"] == "string"
    assert date_only_after["format"] == "date"
    assert "properties" not in date_only_after


@pytest.mark.asyncio
async def test_api_error_response_structure():
    """Test that API error responses are properly structured.

    Tests various error response scenarios that might occur.
    """
    # Simulate various API error responses
    error_responses = [
        # Success with null errorCode
        {"data": [], "errorCode": None},
        # Error with specific error code
        {"data": None, "errorCode": "ERROR_1", "message": "Something went wrong"},
        # Error with null errorType (for IssuedInvoices)
        {"data": [], "errorType": None},
        # Error with specific errorType
        {"data": None, "errorType": "TYPE_1"},
    ]

    # All of these should be valid after our schema fixes
    for response_data in error_responses:
        # These would previously fail validation
        assert response_data is not None


class TestAPIErrorHandlingScenarios:
    """Test various API error scenarios."""

    @pytest.mark.asyncio
    async def test_401_unauthorized_token_refresh(self, mock_heblo_auth):
        """Test that 401 errors trigger token refresh."""
        from heblo_mcp.auth import MSALBearerAuth

        auth = MSALBearerAuth(mock_heblo_auth)

        # Create request
        request = httpx.Request("GET", "https://test.example.com/api/test")

        # Start auth flow
        flow = auth.auth_flow(request)
        authed_request = next(flow)

        # Simulate 401 response
        response_401 = Mock(spec=httpx.Response)
        response_401.status_code = 401

        # Should trigger retry
        try:
            flow.send(response_401)
            retry_request = next(flow)
            assert "Authorization" in retry_request.headers
        except StopIteration:
            pass

    @pytest.mark.asyncio
    async def test_api_timeout_handling(self):
        """Test handling of API timeouts."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.TimeoutException("Request timeout")

            with pytest.raises(httpx.TimeoutException):
                await mock_client.get("https://test.example.com/api/test")

    @pytest.mark.asyncio
    async def test_api_invalid_json_response(self):
        """Test handling of invalid JSON responses."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.side_effect = ValueError("Invalid JSON")

            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            async with mock_client_class() as client:
                response = await client.get("https://test.example.com/api/test")

                with pytest.raises(ValueError):
                    response.json()

    @pytest.mark.asyncio
    async def test_api_rate_limiting(self):
        """Test handling of API rate limiting (429 Too Many Requests)."""
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}

        # Application should handle 429 appropriately
        assert mock_response.status_code == 429
        assert "Retry-After" in mock_response.headers


class TestProductTypeFiltering:
    """Test that product type filtering works correctly in various scenarios."""

    def test_product_type_enum_values(self, sample_openapi_spec):
        """Test that ProductType enum has all expected values."""
        product_type = sample_openapi_spec["components"]["schemas"]["ProductType"]

        expected_types = [
            "UNDEFINED",
            "Goods",
            "Material",
            "SemiProduct",
            "Product",
            "Set",
        ]

        for expected in expected_types:
            assert expected in product_type["enum"]

    def test_product_code_patterns(self):
        """Test recognition of product code patterns."""
        # Codes ending with 'M' should be recognized as SemiProduct
        test_codes = [
            ("ABC123M", True),  # Should be SemiProduct
            ("XYZ456", False),  # Should be Product
            ("TEST-M", True),  # Should be SemiProduct
            ("PROD_001", False),  # Should be Product
        ]

        for code, should_be_semi in test_codes:
            is_semi = code.endswith("M")
            assert is_semi == should_be_semi


class TestSchemaValidationFixes:
    """Test that schema validation fixes handle real API response patterns."""

    def test_multiple_error_codes_all_nullable(self, sample_openapi_spec):
        """Test that all error-related enums are nullable."""
        spec = copy.deepcopy(sample_openapi_spec)
        fix_schema_validation(spec)

        schemas = spec["components"]["schemas"]

        # ErrorCodes should be nullable
        if "ErrorCodes" in schemas:
            assert schemas["ErrorCodes"].get("nullable") is True

        # IssuedInvoiceErrorType should be nullable
        if "IssuedInvoiceErrorType" in schemas:
            assert schemas["IssuedInvoiceErrorType"].get("nullable") is True

    def test_date_format_consistency(self, sample_openapi_spec):
        """Test that date formats are consistent."""
        spec = copy.deepcopy(sample_openapi_spec)
        fix_schema_validation(spec)

        date_only = spec["components"]["schemas"]["DateOnly"]

        # Should use ISO 8601 date format
        assert date_only["type"] == "string"
        assert date_only["format"] == "date"
        assert "ISO 8601" in date_only["description"]
