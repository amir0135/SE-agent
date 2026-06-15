"""Configuration loaded entirely from the environment (Constitution: no secrets in code)."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env(name: str) -> str | None:
    value = os.environ.get(name)
    return value.strip() if value and value.strip() else None


@dataclass(frozen=True)
class CrmConfig:
    crm_url: str | None
    tenant_id: str | None
    client_id: str | None
    client_secret: str | None

    @property
    def configured(self) -> bool:
        # Minimum to attempt live CRM access: an org URL plus an Entra app identity.
        return bool(self.crm_url and self.tenant_id and self.client_id)


@dataclass(frozen=True)
class LlmConfig:
    provider: str | None
    endpoint: str | None
    api_key: str | None
    deployment: str | None

    @property
    def configured(self) -> bool:
        return bool(self.provider and self.api_key and self.deployment)


@dataclass(frozen=True)
class Settings:
    crm: CrmConfig
    llm: LlmConfig
    force_dry_run: bool

    @classmethod
    def from_env(cls) -> "Settings":
        crm = CrmConfig(
            crm_url=_env("SEAGENT_CRM_URL"),
            tenant_id=_env("SEAGENT_ENTRA_TENANT_ID"),
            client_id=_env("SEAGENT_ENTRA_CLIENT_ID"),
            client_secret=_env("SEAGENT_ENTRA_CLIENT_SECRET"),
        )
        llm = LlmConfig(
            provider=_env("SEAGENT_LLM_PROVIDER"),
            endpoint=_env("SEAGENT_LLM_ENDPOINT"),
            api_key=_env("SEAGENT_LLM_API_KEY"),
            deployment=_env("SEAGENT_LLM_DEPLOYMENT"),
        )
        force = (_env("SEAGENT_DRY_RUN") or "").lower() in {"1", "true", "yes"}
        return cls(crm=crm, llm=llm, force_dry_run=force)

    @property
    def dry_run(self) -> bool:
        """Dry mode: no live LLM is available, or it was explicitly forced."""
        return self.force_dry_run or not self.llm.configured
