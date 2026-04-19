"""Tests for Secret and Secrets (repository + agent)."""

import httpx

from tilde.models import Organization, Secret, Secrets

REPO_SECRETS_PATH = "/organizations/test-org/repositories/test-repo/secrets"
AGENT_SECRETS_PATH = "/organizations/test-org/agents/data-pipeline/secrets"


class TestRepositorySecrets:
    def test_create(self, mock_api, repo):
        route = mock_api.put(f"{REPO_SECRETS_PATH}/DB_PASSWORD").mock(
            return_value=httpx.Response(200, json={"key": "DB_PASSWORD"})
        )
        s = repo.secrets.create("DB_PASSWORD", "supersecret")
        assert isinstance(s, Secret)
        assert s.name == "DB_PASSWORD"
        assert s.value == "supersecret"
        assert route.called
        import json

        payload = json.loads(route.calls[0].request.content)
        assert payload == {"value": "supersecret"}

    def test_get_returns_secret_with_value(self, mock_api, repo):
        mock_api.get(f"{REPO_SECRETS_PATH}/DB_PASSWORD").mock(
            return_value=httpx.Response(
                200,
                json={"key": "DB_PASSWORD", "value": "supersecret"},
            )
        )
        s = repo.secrets.get("DB_PASSWORD")
        assert isinstance(s, Secret)
        assert s.name == "DB_PASSWORD"
        assert s.value == "supersecret"

    def test_delete(self, mock_api, repo):
        route = mock_api.delete(f"{REPO_SECRETS_PATH}/DB_PASSWORD").mock(
            return_value=httpx.Response(204)
        )
        repo.secrets.delete("DB_PASSWORD")
        assert route.called

    def test_list(self, mock_api, repo):
        mock_api.get(REPO_SECRETS_PATH).mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "key": "DB_PASSWORD",
                            "created_by_type": "user",
                            "created_by": "user-1",
                            "created_at": "2026-01-15T10:00:00+00:00",
                            "updated_at": "2026-01-15T10:00:00+00:00",
                        },
                        {
                            "key": "API_KEY",
                            "created_by_type": "agent",
                            "created_by": "agent-1",
                            "created_at": "2026-01-16T10:00:00+00:00",
                            "updated_at": "2026-01-16T10:00:00+00:00",
                        },
                    ]
                },
            )
        )
        secrets = list(repo.secrets.list())
        assert len(secrets) == 2
        assert all(isinstance(s, Secret) for s in secrets)
        assert secrets[0].name == "DB_PASSWORD"
        assert secrets[0].created_by_type == "user"
        assert secrets[0].created_at is not None

    def test_list_empty(self, mock_api, repo):
        mock_api.get(REPO_SECRETS_PATH).mock(return_value=httpx.Response(200, json={"results": []}))
        assert list(repo.secrets.list()) == []


class TestSecretValueLazyLoad:
    def test_value_lazy_loads_on_first_access(self, mock_api, repo):
        """A Secret returned from list() has no value cached; .value triggers a GET."""
        mock_api.get(REPO_SECRETS_PATH).mock(
            return_value=httpx.Response(
                200,
                json={"results": [{"key": "DB_PASSWORD"}]},
            )
        )
        mock_api.get(f"{REPO_SECRETS_PATH}/DB_PASSWORD").mock(
            return_value=httpx.Response(
                200,
                json={"key": "DB_PASSWORD", "value": "fetched-lazily"},
            )
        )
        secrets = list(repo.secrets.list())
        assert secrets[0].value == "fetched-lazily"

    def test_delete_via_entity(self, mock_api, repo):
        route = mock_api.delete(f"{REPO_SECRETS_PATH}/DB_PASSWORD").mock(
            return_value=httpx.Response(204)
        )
        mock_api.get(f"{REPO_SECRETS_PATH}/DB_PASSWORD").mock(
            return_value=httpx.Response(200, json={"key": "DB_PASSWORD", "value": "x"})
        )
        repo.secrets.get("DB_PASSWORD").delete()
        assert route.called


class TestAgentSecrets:
    def _get_agent(self, mock_api, client):
        mock_api.get("/organizations/test-org/agents/data-pipeline").mock(
            return_value=httpx.Response(
                200,
                json={"id": "agent-1", "name": "data-pipeline", "organization_id": "org-1"},
            )
        )
        return Organization(client, name="test-org").agents.get("data-pipeline")

    def test_create(self, mock_api, client):
        agent = self._get_agent(mock_api, client)
        route = mock_api.put(f"{AGENT_SECRETS_PATH}/DB_PASSWORD").mock(
            return_value=httpx.Response(200, json={"key": "DB_PASSWORD"})
        )
        s = agent.secrets.create("DB_PASSWORD", "supersecret")
        assert isinstance(s, Secret)
        assert s.value == "supersecret"
        assert route.called

    def test_get(self, mock_api, client):
        agent = self._get_agent(mock_api, client)
        mock_api.get(f"{AGENT_SECRETS_PATH}/DB_PASSWORD").mock(
            return_value=httpx.Response(
                200,
                json={"key": "DB_PASSWORD", "value": "supersecret"},
            )
        )
        s = agent.secrets.get("DB_PASSWORD")
        assert s.value == "supersecret"

    def test_delete(self, mock_api, client):
        agent = self._get_agent(mock_api, client)
        route = mock_api.delete(f"{AGENT_SECRETS_PATH}/DB_PASSWORD").mock(
            return_value=httpx.Response(204)
        )
        agent.secrets.delete("DB_PASSWORD")
        assert route.called

    def test_list(self, mock_api, client):
        agent = self._get_agent(mock_api, client)
        mock_api.get(AGENT_SECRETS_PATH).mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "key": "DB_PASSWORD",
                            "created_by_type": "user",
                            "created_by": "user-1",
                            "created_at": "2026-01-15T10:00:00+00:00",
                            "updated_at": "2026-01-15T10:00:00+00:00",
                        },
                    ]
                },
            )
        )
        secrets = list(agent.secrets.list())
        assert len(secrets) == 1
        assert secrets[0].name == "DB_PASSWORD"


class TestSecretsRepr:
    def test_repr(self, repo):
        s = repo.secrets
        assert isinstance(s, Secrets)
        assert "secrets" in repr(s)
