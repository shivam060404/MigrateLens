"""Real RSA verification with ephemeral test keys; no network identity-provider claim."""

from time import time

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from src.domain.control import AccessDenied, Principal
from src.infrastructure.identity.tokens import TokenVerifier


@pytest.fixture(scope="module")
def identity():
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = private.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return private, TokenVerifier(public, "local-fictional", "migratelens-control")


def claims():
    now = int(time())
    return {
        "sub": "alice",
        "iss": "local-fictional",
        "aud": "migratelens-control",
        "iat": now,
        "exp": now + 300,
        "jti": "test-token",
    }


def test_verified_identity_does_not_take_permissions_from_token(identity):
    private, verifier = identity
    token = jwt.encode(
        {**claims(), "tenant": "attacker", "role": "owner"}, private, algorithm="RS256"
    )
    assert verifier.verify(token) == Principal("alice")


@pytest.mark.parametrize(
    "overrides",
    [
        {"iss": "other"},
        {"aud": "other"},
        {"exp": 1},
        {"sub": ""},
        {"iat": 1},
        {"exp": int(time()) + 3600},
        {"sub": 42},
    ],
)
def test_invalid_claims_fail_closed(identity, overrides):
    private, verifier = identity
    with pytest.raises(AccessDenied):
        verifier.verify(jwt.encode({**claims(), **overrides}, private, algorithm="RS256"))


@pytest.mark.parametrize("missing", ["sub", "iss", "aud", "iat", "exp", "jti"])
def test_required_claims(identity, missing):
    private, verifier = identity
    payload = claims()
    del payload[missing]
    with pytest.raises(AccessDenied):
        verifier.verify(jwt.encode(payload, private, algorithm="RS256"))


def test_wrong_signer_and_algorithm(identity):
    _, verifier = identity
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    for token in [
        jwt.encode(claims(), other, algorithm="RS256"),
        jwt.encode(claims(), "untrusted-secret-for-algorithm-test-only", algorithm="HS256"),
    ]:
        with pytest.raises(AccessDenied):
            verifier.verify(token)
