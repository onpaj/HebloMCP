"""Tests for user context model."""

from heblo_mcp.user_context import UserContext


def test_user_context_creation():
    """Test creating a user context."""
    ctx = UserContext(
        email="user@example.com", tenant_id="tenant-123", object_id="obj-456", token="fake-token"
    )
    assert ctx.email == "user@example.com"
    assert ctx.tenant_id == "tenant-123"
    assert ctx.object_id == "obj-456"
    assert ctx.token == "fake-token"


def test_user_context_repr_hides_token():
    """Test that repr doesn't expose token."""
    ctx = UserContext(
        email="user@example.com", tenant_id="tenant-123", object_id="obj-456", token="secret-token"
    )
    repr_str = repr(ctx)
    assert "secret-token" not in repr_str
    assert "user@example.com" in repr_str
