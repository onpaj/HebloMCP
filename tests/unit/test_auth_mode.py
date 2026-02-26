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
