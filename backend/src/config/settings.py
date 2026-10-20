from typing import Literal
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ML_", extra="forbid")
    environment: Literal["development", "test", "production"] = "development"
    auth_mode: Literal["demo", "oidc"] = "demo"
    runner_mode: Literal["fixture", "pilot"] = "fixture"
    database_url: str = "postgresql+psycopg2://localhost:55432/migratelens"
    artifact_root: str = "artifacts"
    temporal_address: str = "localhost:7233"
    emergency_stop: bool = False
    customer_code_enabled: bool = False

    @model_validator(mode="after")
    def secure_environment(self):
        if self.customer_code_enabled:
            raise ValueError("Customer code execution is not implemented or approved")
        if self.environment == "production":
            raise ValueError(
                "Production is gated: OIDC, isolated runner and pilot sign-off are not verified."
            )
        if self.auth_mode != "demo" or self.runner_mode != "fixture":
            raise ValueError(
                "Only explicitly labeled demo identity and fixture execution are implemented."
            )
        return self
