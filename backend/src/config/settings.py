from typing import Literal
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ML_", extra="forbid")
    environment: Literal["development", "test", "production"] = "development"
    auth_mode: Literal["demo", "local_token", "oidc"] = "demo"
    runner_mode: Literal["fixture", "pilot"] = "fixture"
    database_url: str | None = None
    artifact_root: str = "artifacts"
    emergency_stop: bool = False
    customer_code_enabled: bool = False
    control_api_enabled: bool = False
    identity_public_key_path: str | None = None
    identity_issuer: str = "migratelens-local"
    identity_audience: str = "migratelens-control"

    @model_validator(mode="after")
    def secure_environment(self):
        if self.customer_code_enabled:
            raise ValueError("Customer code execution is not implemented or approved")
        if self.environment == "production":
            raise ValueError(
                "Production is gated: OIDC, isolated runner and pilot sign-off are not verified."
            )
        if self.runner_mode != "fixture":
            raise ValueError("Only explicitly labeled fixture execution is implemented.")
        if self.control_api_enabled:
            if self.auth_mode != "local_token" or not self.identity_public_key_path:
                raise ValueError("Control API requires a configured local token verifier")
            if not self.database_url or not self.database_url.startswith("postgresql+psycopg2://"):
                raise ValueError("Control API requires a PostgreSQL runtime connection")
        elif self.auth_mode != "demo":
            raise ValueError(
                "Only explicitly labeled demo identity is available without the control API"
            )
        return self
