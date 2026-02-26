"""User context model for authenticated requests."""

from dataclasses import dataclass


@dataclass
class UserContext:
    """Represents an authenticated user's context.

    Attributes:
        email: User's email address
        tenant_id: Azure AD tenant ID
        object_id: User's object ID in Azure AD
        token: Access token for API calls
    """

    email: str
    tenant_id: str
    object_id: str
    token: str

    def __repr__(self) -> str:
        """String representation without exposing token."""
        return f"UserContext(email={self.email!r}, tenant_id={self.tenant_id!r}, object_id={self.object_id!r})"
