"""Harness settings: process environment only, the same on the course platform and on your computer.

The course runner sets these variables. Locally, scripts/run_local.py sets the same ones before starting us.
The harness never reads .env and never logs in.
"""

from __future__ import annotations

from pydantic import SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

# Variables the agent under test needs; the harness checks they are present, then passes them on unchanged.
MODEL_VARIABLES = ("OPENAI_BASE_URL", "OPENAI_API_KEY", "OPENAI_MODEL")
# Optional model settings, passed on to the agent when present (agent-contract.md §2).
OPTIONAL_MODEL_VARIABLES = ("OPENAI_PROJECT_ID", "OPENAI_EXTRA_BODY")


class SettingsMissing(Exception):
    """Required variables are missing. Holds their names only, never values."""

    def __init__(self, names: list[str]) -> None:
        super().__init__(f"missing or invalid environment variables: {', '.join(names)}")
        self.names = names


class HarnessSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore", env_ignore_empty=True)

    agentswitch_base_url: str
    agentswitch_token: SecretStr
    agentswitch_instance: str
    agentswitch_run_id: str | None = None
    openai_base_url: str | None = None
    openai_api_key: SecretStr | None = None
    openai_model: str | None = None

    @property
    def base_url(self) -> str:
        return self.agentswitch_base_url.rstrip("/")

    def missing_model_variables(self) -> list[str]:
        values = {
            "OPENAI_BASE_URL": self.openai_base_url,
            "OPENAI_API_KEY": self.openai_api_key,
            "OPENAI_MODEL": self.openai_model,
        }
        return [name for name in MODEL_VARIABLES if not values[name]]

    def secrets(self) -> list[str]:
        """Values that must never appear in a record, a log or results.json."""
        found = [self.agentswitch_token.get_secret_value()]
        if self.openai_api_key:
            found.append(self.openai_api_key.get_secret_value())
        return [s for s in found if len(s) >= 6]


def load_settings() -> HarnessSettings:
    try:
        return HarnessSettings()  # values come from the process environment
    except ValidationError as e:
        names = sorted({"_".join(str(p) for p in err["loc"]).upper() for err in e.errors()})
        raise SettingsMissing(names) from None
