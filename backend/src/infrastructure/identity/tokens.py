"""Pinned-key token verification; tenant permissions always come from the database.

This is a verifier boundary, not a production OIDC discovery/login integration.
The caller supplies trusted issuer, audience and public key configuration.
"""

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey

from src.domain.control import AccessDenied, Principal


class TokenVerifier:
    def __init__(self, public_key: bytes, issuer: str, audience: str):
        key = serialization.load_pem_public_key(public_key)
        if not isinstance(key, RSAPublicKey) or key.key_size < 2048:
            raise ValueError("An RSA public key of at least 2048 bits is required")
        if not issuer or not audience:
            raise ValueError("Trusted issuer and audience are required")
        self.key = key
        self.issuer = issuer
        self.audience = audience

    def verify(self, token: str) -> Principal:
        if not token or len(token) > 16384:
            raise AccessDenied("Invalid authentication token")
        try:
            claims = jwt.decode(
                token,
                self.key,
                algorithms=["RS256"],
                issuer=self.issuer,
                audience=self.audience,
                options={"require": ["sub", "iss", "aud", "iat", "exp", "jti"]},
            )
            if (
                type(claims["iat"]) is not int
                or type(claims["exp"]) is not int
                or not 0 < claims["exp"] - claims["iat"] <= 900
            ):
                raise AccessDenied("Invalid authentication token lifetime")
            return Principal(claims["sub"])
        except jwt.InvalidTokenError as exc:
            raise AccessDenied("Invalid authentication token") from exc
