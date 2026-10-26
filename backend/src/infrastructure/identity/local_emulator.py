"""Disposable development identity issuer. Never serves production traffic."""

import os
import stat
import time
from pathlib import Path

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey

from src.domain.control import Principal


class LocalIdentityEmulator:
    def __init__(self, directory: Path, *, environment: str):
        if environment not in {"development", "test"}:
            raise ValueError("Local identity emulator is disabled outside development and tests")
        self.directory = directory
        self.private_path = directory / "private.pem"
        self.public_path = directory / "public.pem"

    def initialize(self) -> Path:
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.directory.chmod(0o700)
        if self.private_path.exists() or self.public_path.exists():
            raise FileExistsError("Identity already initialized; keys are never overwritten")
        private = rsa.generate_private_key(public_exponent=65537, key_size=3072)
        encoded = private.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        fd = os.open(self.private_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        try:
            with os.fdopen(fd, "wb") as output:
                output.write(encoded)
            public_fd = os.open(
                self.public_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o644
            )
            with os.fdopen(public_fd, "wb") as output:
                output.write(
                    private.public_key().public_bytes(
                        serialization.Encoding.PEM,
                        serialization.PublicFormat.SubjectPublicKeyInfo,
                    )
                )
        except Exception:
            self.private_path.unlink(missing_ok=True)
            self.public_path.unlink(missing_ok=True)
            raise
        return self.public_path

    def issue(self, subject: str, *, ttl_seconds: int = 300) -> str:
        principal = Principal(subject)
        if not 1 <= ttl_seconds <= 900:
            raise ValueError("Token lifetime must be between 1 and 900 seconds")
        if stat.S_IMODE(self.private_path.stat().st_mode) & 0o077:
            raise PermissionError("Local signing key must be readable only by its owner")
        private = serialization.load_pem_private_key(self.private_path.read_bytes(), password=None)
        if not isinstance(private, RSAPrivateKey) or private.key_size < 2048:
            raise ValueError("Local signing key must be an RSA key of at least 2048 bits")
        now = int(time.time())
        return jwt.encode(
            {
                "sub": principal.subject,
                "iss": "migratelens-local",
                "aud": "migratelens-control",
                "iat": now,
                "exp": now + ttl_seconds,
                "jti": os.urandom(16).hex(),
            },
            private,
            algorithm="RS256",
        )
