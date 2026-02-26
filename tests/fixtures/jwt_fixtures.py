"""JWT token fixtures for testing."""

import time

import jwt


def create_test_jwt(
    tenant_id: str = "test-tenant",
    client_id: str = "test-client",
    email: str = "user@example.com",
    object_id: str = "obj-123",
    expired: bool = False,
    wrong_audience: bool = False,
    wrong_issuer: bool = False,
    private_key: str | None = None,
) -> str:
    """Create a test JWT token.

    Args:
        tenant_id: Azure AD tenant ID
        client_id: Application client ID
        email: User email
        object_id: User object ID
        expired: If True, create an expired token
        wrong_audience: If True, use wrong audience
        wrong_issuer: If True, use wrong issuer
        private_key: RSA private key (PEM format). If None, uses HS256 with "secret"

    Returns:
        JWT token string
    """
    now = int(time.time())
    exp = now - 3600 if expired else now + 3600

    payload = {
        "aud": "wrong-client" if wrong_audience else client_id,
        "iss": (
            "https://login.microsoftonline.com/wrong-tenant/v2.0"
            if wrong_issuer
            else f"https://login.microsoftonline.com/{tenant_id}/v2.0"
        ),
        "exp": exp,
        "iat": now,
        "nbf": now,
        "preferred_username": email,
        "oid": object_id,
        "sub": object_id,
        "tid": tenant_id,
        "scp": "access_as_user",
    }

    if private_key:
        return jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": "test-key-1"})
    else:
        # For simple tests, use HS256 with shared secret
        return jwt.encode(payload, "test-secret", algorithm="HS256")


def create_test_rsa_keypair() -> tuple[str, str]:
    """Create a test RSA key pair.

    Returns:
        Tuple of (private_key_pem, public_key_pem)
    """
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    return private_pem, public_pem


def create_test_jwks(public_key_pem: str, kid: str = "test-key-1") -> dict:
    """Create a test JWKS (JSON Web Key Set) from a public key.

    Args:
        public_key_pem: Public key in PEM format
        kid: Key ID

    Returns:
        JWKS dictionary
    """
    import base64

    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization

    # Load public key
    public_key = serialization.load_pem_public_key(
        public_key_pem.encode("utf-8"), backend=default_backend()
    )

    # Extract public numbers
    numbers = public_key.public_numbers()

    # Convert to base64url
    def int_to_base64url(n):
        return (
            base64.urlsafe_b64encode(n.to_bytes((n.bit_length() + 7) // 8, byteorder="big"))
            .rstrip(b"=")
            .decode("utf-8")
        )

    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "kid": kid,
                "n": int_to_base64url(numbers.n),
                "e": int_to_base64url(numbers.e),
            }
        ]
    }
