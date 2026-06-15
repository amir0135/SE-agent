"""Entra ID (MSAL) token providers.

The interface lets the deterministic core run with a fake provider; the live provider
lazily imports ``msal`` so the base package needs no network dependencies.
"""

from __future__ import annotations

import abc

from .base import ToolError


class TokenProvider(abc.ABC):
    @abc.abstractmethod
    def get_token(self, scope: str) -> str:
        """Return a bearer access token for the given scope, or raise ToolError('auth')."""
        raise NotImplementedError


class FakeTokenProvider(TokenProvider):
    """Returns a dummy token; used in tests and dry mode. Never hits the network."""

    def __init__(self, token: str = "fake-token") -> None:
        self._token = token

    def get_token(self, scope: str) -> str:  # noqa: ARG002 - scope unused in fake
        return self._token


class MsalTokenProvider(TokenProvider):
    """App-only (client credentials) token provider backed by MSAL.

    Lazily imports ``msal``; only constructed for live runs. Tokens are cached in memory
    by MSAL and never logged or persisted.
    """

    def __init__(self, tenant_id: str, client_id: str, client_secret: str) -> None:
        self._tenant_id = tenant_id
        self._client_id = client_id
        self._client_secret = client_secret
        self._app = None

    def _ensure_app(self):
        if self._app is None:
            try:
                import msal  # type: ignore
            except ImportError as exc:  # pragma: no cover - exercised only in live installs
                raise ToolError(
                    "auth",
                    "msal is not installed; install the 'live' extra to use real CRM auth",
                ) from exc
            self._app = msal.ConfidentialClientApplication(
                client_id=self._client_id,
                client_credential=self._client_secret,
                authority=f"https://login.microsoftonline.com/{self._tenant_id}",
            )
        return self._app

    def get_token(self, scope: str) -> str:
        app = self._ensure_app()
        result = app.acquire_token_for_client(scopes=[scope])
        token = result.get("access_token") if isinstance(result, dict) else None
        if not token:
            # Do not leak result contents (may contain error detail); keep it generic.
            raise ToolError("auth", "Failed to acquire CRM access token")
        return token
