"""Sandbox identity metadata (IMDS) credentials provider.

Inside a Tilde sandbox, a link-local metadata endpoint returns a short-lived
bearer token scoped to the sandbox's target principal.  The server-side spec
is the *Sandbox Identity Metadata Endpoint* design, modeled after AWS IMDS /
ECS task roles.

When :envvar:`TILDE_SANDBOX_CREDENTIALS_URI` is set and no static API key is
configured, the SDK fetches tokens from that URL and refreshes them before
expiry.  Statically configured credentials (``Client(api_key=...)``,
:envvar:`TILDE_API_KEY`, or ``~/.tilde/config.yaml``) always take precedence
so a caller's deliberate credentials are never silently overridden by the
sandbox metadata endpoint.  When :envvar:`TILDE_API_URL` is also set, it
supplies the base URL of the Tilde API to call with those tokens.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from tilde._isoparse import parse_iso_datetime
from tilde.exceptions import ConfigurationError, SerializationError, TransportError

ENV_SANDBOX_CREDENTIALS_URI = "TILDE_SANDBOX_CREDENTIALS_URI"
ENV_API_URL = "TILDE_API_URL"

# Refresh a little before expiry so requests never race an expiring token.
_REFRESH_LEEWAY = timedelta(minutes=2)


@dataclass(frozen=True)
class SandboxCredentials:
    """Credentials returned by the sandbox metadata endpoint."""

    access_token: str
    expires_at: datetime
    principal_type: str | None = None
    principal_id: str | None = None
    principal_name: str | None = None
    organization_id: str | None = None
    api_url: str | None = None


class SandboxCredentialsProvider:
    """Fetches and caches sandbox-principal credentials.

    The provider is thread-safe: concurrent callers share a single in-flight
    refresh.  Credentials are refreshed when they are within
    :data:`_REFRESH_LEEWAY` of expiry.
    """

    def __init__(
        self,
        credentials_uri: str,
        *,
        http_client: httpx.Client | None = None,
        timeout: float = 5.0,
    ) -> None:
        self._uri = credentials_uri
        self._lock = threading.Lock()
        self._cached: SandboxCredentials | None = None
        if http_client is None:
            self._http = httpx.Client(timeout=timeout)
            self._owns_http = True
        else:
            self._http = http_client
            self._owns_http = False

    @property
    def credentials_uri(self) -> str:
        return self._uri

    def get_credentials(self, *, force_refresh: bool = False) -> SandboxCredentials:
        """Return cached credentials, fetching fresh ones if needed."""
        with self._lock:
            if (
                not force_refresh
                and self._cached is not None
                and not self._is_expiring(self._cached)
            ):
                return self._cached
            self._cached = self._fetch()
            return self._cached

    def get_token(self) -> str:
        """Return the current bearer token, refreshing if needed."""
        return self.get_credentials().access_token

    def invalidate(self) -> None:
        """Drop the cached credentials so the next call refetches."""
        with self._lock:
            self._cached = None

    def close(self) -> None:
        if self._owns_http:
            self._http.close()

    def __enter__(self) -> SandboxCredentialsProvider:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    # -- internals -----------------------------------------------------------

    def _is_expiring(self, creds: SandboxCredentials) -> bool:
        return datetime.now(timezone.utc) + _REFRESH_LEEWAY >= creds.expires_at

    def _fetch(self) -> SandboxCredentials:
        try:
            response = self._http.get(self._uri)
        except httpx.TransportError as exc:
            raise TransportError(f"Sandbox credentials fetch failed: {exc}", cause=exc) from exc
        if response.status_code != 200:
            raise ConfigurationError(
                f"Sandbox credentials endpoint {self._uri} returned "
                f"{response.status_code}: {response.text[:200]}"
            )
        try:
            payload = response.json()
        except Exception as exc:
            raise SerializationError(
                f"Invalid JSON from sandbox credentials endpoint: {exc}"
            ) from exc
        return _parse_credentials(payload)


def _parse_credentials(payload: Any) -> SandboxCredentials:
    if not isinstance(payload, dict):
        raise SerializationError("Sandbox credentials payload must be a JSON object")
    try:
        access_token = payload["access_token"]
        expires_at_raw = payload["expires_at"]
    except KeyError as exc:
        raise SerializationError(
            f"Sandbox credentials payload missing field: {exc.args[0]}"
        ) from exc
    if not isinstance(access_token, str) or not access_token:
        raise SerializationError("Sandbox credentials access_token must be a non-empty string")
    if not isinstance(expires_at_raw, str):
        raise SerializationError("Sandbox credentials expires_at must be an ISO 8601 string")
    try:
        expires_at = _parse_expires_at(expires_at_raw)
    except ValueError as exc:
        raise SerializationError(f"Invalid expires_at in sandbox credentials: {exc}") from exc
    return SandboxCredentials(
        access_token=access_token,
        expires_at=expires_at,
        principal_type=_optional_str(payload.get("principal_type")),
        principal_id=_optional_str(payload.get("principal_id")),
        principal_name=_optional_str(payload.get("principal_name")),
        organization_id=_optional_str(payload.get("organization_id")),
        api_url=_optional_str(payload.get("api_url")),
    )


def _parse_expires_at(value: str) -> datetime:
    dt = parse_iso_datetime(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _optional_str(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None
