"""Unit tests for OpenAPI spec patching module."""

import copy

import pytest

from heblo_mcp.spec import fix_schema_validation, inject_metadata


def test_inject_metadata(sample_openapi_spec):
    """Test that metadata is correctly injected into OpenAPI spec."""
    spec = copy.deepcopy(sample_openapi_spec)

    inject_metadata(spec)

    # Check catalog list endpoint
    catalog_list = spec["paths"]["/api/Catalog"]["get"]
    assert "operationId" in catalog_list
    assert catalog_list["operationId"] == "catalog_list"
    assert "summary" in catalog_list
    assert "HINT" in catalog_list["summary"]

    # Check catalog composition endpoint
    catalog_comp = spec["paths"]["/api/Catalog/{productCode}/composition"]["get"]
    assert "operationId" in catalog_comp
    assert catalog_comp["operationId"] == "catalog_composition"
    assert "summary" in catalog_comp
    assert "HINT" in catalog_comp["summary"]


def test_inject_metadata_preserves_existing(sample_openapi_spec):
    """Test that existing operationId and summary are not overwritten."""
    spec = copy.deepcopy(sample_openapi_spec)

    # Add existing metadata
    spec["paths"]["/api/Catalog"]["get"]["operationId"] = "existing_id"
    spec["paths"]["/api/Catalog"]["get"]["summary"] = "Existing summary"

    inject_metadata(spec)

    # Existing values should be preserved
    catalog_list = spec["paths"]["/api/Catalog"]["get"]
    assert catalog_list["operationId"] == "existing_id"
    assert catalog_list["summary"] == "Existing summary"


def test_inject_metadata_handles_missing_paths():
    """Test that inject_metadata handles spec without paths."""
    spec = {"openapi": "3.0.1", "info": {"title": "Test"}}

    # Should not raise exception
    inject_metadata(spec)


def test_fix_schema_validation_error_codes(sample_openapi_spec):
    """Test that ErrorCodes enum is made nullable."""
    spec = copy.deepcopy(sample_openapi_spec)

    fix_schema_validation(spec)

    error_codes = spec["components"]["schemas"]["ErrorCodes"]

    # Should have null in enum
    assert None in error_codes["enum"] or "null" in error_codes["enum"]

    # Should be marked as nullable
    assert error_codes.get("nullable") is True


def test_fix_schema_validation_issued_invoice_error_type(sample_openapi_spec):
    """Test that IssuedInvoiceErrorType enum is made nullable."""
    spec = copy.deepcopy(sample_openapi_spec)

    fix_schema_validation(spec)

    error_type = spec["components"]["schemas"]["IssuedInvoiceErrorType"]

    # Should have null in enum
    assert None in error_type["enum"] or "null" in error_type["enum"]

    # Should be marked as nullable
    assert error_type.get("nullable") is True


def test_fix_schema_validation_date_only(sample_openapi_spec):
    """Test that DateOnly schema is converted from object to string."""
    spec = copy.deepcopy(sample_openapi_spec)

    fix_schema_validation(spec)

    date_only = spec["components"]["schemas"]["DateOnly"]

    # Should be changed to string type
    assert date_only["type"] == "string"
    assert date_only["format"] == "date"
    assert "description" in date_only

    # Should not have object properties
    assert "properties" not in date_only


def test_fix_schema_validation_handles_missing_schemas():
    """Test that fix_schema_validation handles spec without schemas."""
    spec = {"openapi": "3.0.1", "info": {"title": "Test"}}

    # Should not raise exception
    fix_schema_validation(spec)


def test_fix_schema_validation_idempotent(sample_openapi_spec):
    """Test that fix_schema_validation is idempotent."""
    spec = copy.deepcopy(sample_openapi_spec)

    # Apply fixes twice
    fix_schema_validation(spec)
    spec_after_first = copy.deepcopy(spec)

    fix_schema_validation(spec)
    spec_after_second = copy.deepcopy(spec)

    # Should be identical
    assert spec_after_first == spec_after_second


def test_fix_schema_validation_preserves_existing_enums(sample_openapi_spec):
    """Test that existing enum values are preserved."""
    spec = copy.deepcopy(sample_openapi_spec)

    original_error_codes = spec["components"]["schemas"]["ErrorCodes"]["enum"].copy()

    fix_schema_validation(spec)

    error_codes = spec["components"]["schemas"]["ErrorCodes"]

    # Original values should still be present
    for value in original_error_codes:
        assert value in error_codes["enum"]


def test_full_spec_patching_pipeline(sample_openapi_spec):
    """Test the complete spec patching pipeline."""
    spec = copy.deepcopy(sample_openapi_spec)

    # Apply both fixes
    fix_schema_validation(spec)
    inject_metadata(spec)

    # Verify ErrorCodes is fixed
    assert spec["components"]["schemas"]["ErrorCodes"]["nullable"] is True

    # Verify DateOnly is fixed
    assert spec["components"]["schemas"]["DateOnly"]["type"] == "string"

    # Verify metadata is injected
    assert "operationId" in spec["paths"]["/api/Catalog"]["get"]
    assert "summary" in spec["paths"]["/api/Catalog"]["get"]
