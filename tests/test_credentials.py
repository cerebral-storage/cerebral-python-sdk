"""Tests for the sandbox identity metadata (IMDS) credentials provider."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import pytest
import respx
from httpx import Response

from tilde._credentials import (
    ENV_SANDBOX_CREDENTIALS_URI,
    SandboxCredentials,
    SandboxCredentialsProvider,
)
from tilde.client import Client
from tilde.exceptions import ConfigurationError, SerializationError, TransportError

METADATA_URL = "http://169.254.170.2/v1/credentials"


def _payload(token: str = "tst-abc", expires_in: int = 900, **extra: object) -> dict[str, object]:
    expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)
    body: dict[str, object] = {
        "access_token": token,
        "expires_at": expires_at.isoformat().replace("+00:00", "Z"),
        "principal_type": "agent",
        "principal_id": "9c8d1b2e-0000-0000-0000-000000000001",
        "principal_name": "deploy-bot",
        "organization_id": "3e100000-0000-0000-0000-000000000000",
        "api_url": "https://api.tilde.run",
    }
    body.update(extra)
    return body


# ---------------------------------------------------------------------------
# Fetching and caching
# ---------------------------------------------------------------------------


class TestFetchAndCache:
    def test_fetches_and_parses(self):
        with respx.mock(assert_all_called=False) as rsps:
            rsps.get(METADATA_URL).mock(return_value=Response(200, json=_payload()))
            with SandboxCredentialsProvider(METADATA_URL) as provider:
                creds = provider.get_credentials()
        assert isinstance(creds, SandboxCredentials)
        assert creds.access_token == "tst-abc"
        assert creds.principal_name == "deploy-bot"
        assert creds.api_url == "https://api.tilde.run"
        assert creds.expires_at.tzinfo is not None

    def test_cached_across_calls(self):
        with respx.mock(assert_all_called=False) as rsps:
            route = rsps.get(METADATA_URL).mock(return_value=Response(200, json=_payload()))
            with SandboxCredentialsProvider(METADATA_URL) as provider:
                first = provider.get_token()
                second = provider.get_token()
        assert first == second == "tst-abc"
        assert route.call_count == 1

    def test_refreshes_when_expiring(self):
        # First response expires within the refresh leeway, forcing a second fetch.
        expiring = _payload(token="tst-one", expires_in=30)
        fresh = _payload(token="tst-two", expires_in=900)
        with respx.mock(assert_all_called=False) as rsps:
            route = rsps.get(METADATA_URL).mock(
                side_effect=[Response(200, json=expiring), Response(200, json=fresh)]
            )
            with SandboxCredentialsProvider(METADATA_URL) as provider:
                assert provider.get_token() == "tst-one"
                assert provider.get_token() == "tst-two"
        assert route.call_count == 2

    def test_force_refresh(self):
        with respx.mock(assert_all_called=False) as rsps:
            route = rsps.get(METADATA_URL).mock(
                side_effect=[
                    Response(200, json=_payload(token="tst-one")),
                    Response(200, json=_payload(token="tst-two")),
                ]
            )
            with SandboxCredentialsProvider(METADATA_URL) as provider:
                assert provider.get_token() == "tst-one"
                assert provider.get_credentials(force_refresh=True).access_token == "tst-two"
        assert route.call_count == 2

    def test_invalidate(self):
        with respx.mock(assert_all_called=False) as rsps:
            route = rsps.get(METADATA_URL).mock(
                side_effect=[
                    Response(200, json=_payload(token="tst-one")),
                    Response(200, json=_payload(token="tst-two")),
                ]
            )
            with SandboxCredentialsProvider(METADATA_URL) as provider:
                assert provider.get_token() == "tst-one"
                provider.invalidate()
                assert provider.get_token() == "tst-two"
        assert route.call_count == 2


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrors:
    def test_non_200_raises_configuration_error(self):
        with (
            respx.mock(assert_all_called=False) as rsps,
            SandboxCredentialsProvider(METADATA_URL) as provider,
            pytest.raises(ConfigurationError),
        ):
            rsps.get(METADATA_URL).mock(return_value=Response(404, text="not found"))
            provider.get_credentials()

    def test_transport_error_wrapped(self):
        with (
            respx.mock(assert_all_called=False) as rsps,
            SandboxCredentialsProvider(METADATA_URL) as provider,
            pytest.raises(TransportError),
        ):
            rsps.get(METADATA_URL).mock(side_effect=httpx.ConnectError("refused"))
            provider.get_credentials()

    def test_invalid_json_raises(self):
        with (
            respx.mock(assert_all_called=False) as rsps,
            SandboxCredentialsProvider(METADATA_URL) as provider,
            pytest.raises(SerializationError),
        ):
            rsps.get(METADATA_URL).mock(return_value=Response(200, text="not-json"))
            provider.get_credentials()

    def test_missing_required_field(self):
        with (
            respx.mock(assert_all_called=False) as rsps,
            SandboxCredentialsProvider(METADATA_URL) as provider,
            pytest.raises(SerializationError),
        ):
            rsps.get(METADATA_URL).mock(
                return_value=Response(200, json={"access_token": "tst-abc"})
            )
            provider.get_credentials()

    def test_bad_expires_at_raises(self):
        with (
            respx.mock(assert_all_called=False) as rsps,
            SandboxCredentialsProvider(METADATA_URL) as provider,
            pytest.raises(SerializationError),
        ):
            rsps.get(METADATA_URL).mock(
                return_value=Response(
                    200,
                    json={"access_token": "tst-abc", "expires_at": "not-a-date"},
                )
            )
            provider.get_credentials()

    def test_non_object_payload(self):
        with (
            respx.mock(assert_all_called=False) as rsps,
            SandboxCredentialsProvider(METADATA_URL) as provider,
            pytest.raises(SerializationError),
        ):
            rsps.get(METADATA_URL).mock(return_value=Response(200, json=["a"]))
            provider.get_credentials()


# ---------------------------------------------------------------------------
# Client integration
# ---------------------------------------------------------------------------


BASE_URL = "https://tilde.run/api/v1"


class TestClientIntegration:
    def test_client_uses_provider_token(self, mock_api):
        mock_api.get("/healthcheck").mock(return_value=Response(200, json={"ok": True}))
        with respx.mock(assert_all_called=False) as meta:
            meta.get(METADATA_URL).mock(
                return_value=Response(200, json=_payload(token="tst-from-imds"))
            )
            provider = SandboxCredentialsProvider(METADATA_URL)
            with Client(credentials_provider=provider) as client:
                client._get_json("/healthcheck")
        auth = mock_api.calls.last.request.headers["authorization"]
        assert auth == "Bearer tst-from-imds"

    def test_provider_overrides_env_api_key(self, mock_api, monkeypatch):
        monkeypatch.setenv("TILDE_API_KEY", "env-key-should-not-be-used")
        mock_api.get("/healthcheck").mock(return_value=Response(200, json={"ok": True}))
        with respx.mock(assert_all_called=False) as meta:
            meta.get(METADATA_URL).mock(
                return_value=Response(200, json=_payload(token="tst-from-imds"))
            )
            provider = SandboxCredentialsProvider(METADATA_URL)
            with Client(credentials_provider=provider) as client:
                client._get_json("/healthcheck")
        auth = mock_api.calls.last.request.headers["authorization"]
        assert auth == "Bearer tst-from-imds"

    def test_autodetects_imds_env_var(self, mock_api, monkeypatch):
        monkeypatch.delenv("TILDE_API_KEY", raising=False)
        monkeypatch.setenv(ENV_SANDBOX_CREDENTIALS_URI, METADATA_URL)
        mock_api.get("/healthcheck").mock(return_value=Response(200, json={"ok": True}))
        with respx.mock(assert_all_called=False) as meta:
            meta.get(METADATA_URL).mock(
                return_value=Response(200, json=_payload(token="tst-autodetected"))
            )
            with Client() as client:
                assert client._credentials_provider is not None
                client._get_json("/healthcheck")
        auth = mock_api.calls.last.request.headers["authorization"]
        assert auth == "Bearer tst-autodetected"

    def test_explicit_api_key_disables_autodetect(self, mock_api, monkeypatch):
        monkeypatch.setenv(ENV_SANDBOX_CREDENTIALS_URI, METADATA_URL)
        mock_api.get("/healthcheck").mock(return_value=Response(200, json={"ok": True}))
        with Client(api_key="explicit-key") as client:
            assert client._credentials_provider is None
            client._get_json("/healthcheck")
        auth = mock_api.calls.last.request.headers["authorization"]
        assert auth == "Bearer explicit-key"

    def test_api_url_env_var_sets_endpoint(self, monkeypatch):
        monkeypatch.delenv("TILDE_ENDPOINT_URL", raising=False)
        monkeypatch.setenv("TILDE_API_URL", "https://sandbox.tilde.run")
        client = Client(api_key="test-key")
        try:
            assert client._config.endpoint_url == "https://sandbox.tilde.run"
            assert client._config.base_url == "https://sandbox.tilde.run/api/v1"
        finally:
            client.close()

    def test_endpoint_url_env_wins_over_api_url(self, monkeypatch):
        monkeypatch.setenv("TILDE_ENDPOINT_URL", "https://explicit.tilde.run")
        monkeypatch.setenv("TILDE_API_URL", "https://sandbox.tilde.run")
        client = Client(api_key="test-key")
        try:
            assert client._config.endpoint_url == "https://explicit.tilde.run"
        finally:
            client.close()

    def test_client_close_closes_provider(self, monkeypatch):
        monkeypatch.delenv("TILDE_API_KEY", raising=False)
        monkeypatch.setenv(ENV_SANDBOX_CREDENTIALS_URI, METADATA_URL)
        client = Client()
        provider = client._credentials_provider
        assert provider is not None
        client.close()
        # httpx.Client.is_closed reflects close state; reused close is idempotent.
        assert provider._http.is_closed
