"""Tests for Agents, Agent, APIKeys, APIKey, and the Organization chain."""

import httpx

from tilde.models import Agent, Agents, APIKey, Organization, Repositories, Repository

AGENT_RESPONSE = {
    "id": "agent-1",
    "organization_id": "org-1",
    "name": "my-agent",
    "description": "Test agent",
    "metadata": {"env": "prod"},
    "inline_policy": "",
    "inline_policy_updated_at": None,
    "created_by_type": "user",
    "created_by": "user-1",
    "created_by_name": "alice",
    "created_at": "2025-08-01T12:00:00Z",
    "last_used_at": None,
}


def _org(client):
    return Organization(client, name="test-org")


class TestAgents:
    def test_create(self, mock_api, client):
        """POST /organizations/test-org/agents."""
        route = mock_api.post("/organizations/test-org/agents").mock(
            return_value=httpx.Response(200, json=AGENT_RESPONSE)
        )
        agent = _org(client).agents.create(
            "my-agent", description="Test agent", metadata={"env": "prod"}
        )
        assert isinstance(agent, Agent)
        assert agent.name == "my-agent"
        assert agent.id == "agent-1"
        assert agent.description == "Test agent"
        assert agent.metadata == {"env": "prod"}
        assert route.called

    def test_get(self, mock_api, client):
        mock_api.get("/organizations/test-org/agents/my-agent").mock(
            return_value=httpx.Response(200, json=AGENT_RESPONSE)
        )
        agent = _org(client).agents.get("my-agent")
        assert isinstance(agent, Agent)
        assert agent.name == "my-agent"
        assert agent.id == "agent-1"

    def test_list(self, mock_api, client):
        mock_api.get("/organizations/test-org/agents").mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        AGENT_RESPONSE,
                        {**AGENT_RESPONSE, "id": "agent-2", "name": "other-agent"},
                    ],
                    "pagination": {"has_more": False, "next_offset": None},
                },
            )
        )
        agents = list(_org(client).agents.list())
        assert len(agents) == 2
        assert all(isinstance(a, Agent) for a in agents)
        assert agents[0].name == "my-agent"
        assert agents[1].name == "other-agent"

    def test_update(self, mock_api, client):
        updated = {**AGENT_RESPONSE, "description": "Updated"}
        route = mock_api.put("/organizations/test-org/agents/my-agent").mock(
            return_value=httpx.Response(200, json=updated)
        )
        agent = _org(client).agents.get.__wrapped__ if False else None  # placeholder
        # Normal path: fetch agent then call .update()
        mock_api.get("/organizations/test-org/agents/my-agent").mock(
            return_value=httpx.Response(200, json=AGENT_RESPONSE)
        )
        agent = _org(client).agents.get("my-agent").update(description="Updated")
        assert isinstance(agent, Agent)
        assert agent.description == "Updated"
        assert route.called

    def test_update_inline_policy(self, mock_api, client):
        updated = {**AGENT_RESPONSE, "inline_policy": "allow read *"}
        mock_api.get("/organizations/test-org/agents/my-agent").mock(
            return_value=httpx.Response(200, json=AGENT_RESPONSE)
        )
        route = mock_api.put("/organizations/test-org/agents/my-agent").mock(
            return_value=httpx.Response(200, json=updated)
        )
        agent = _org(client).agents.get("my-agent").update(inline_policy="allow read *")
        assert isinstance(agent, Agent)
        assert agent.inline_policy == "allow read *"
        assert route.called

    def test_delete(self, mock_api, client):
        route = mock_api.delete("/organizations/test-org/agents/my-agent").mock(
            return_value=httpx.Response(204)
        )
        _org(client).agents.delete("my-agent")
        assert route.called


class TestAPIKeys:
    def test_list(self, mock_api, client):
        mock_api.get("/organizations/test-org/agents/my-agent/auth/keys").mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "id": "key-1",
                            "name": "dev-key",
                            "description": "",
                            "token_hint": "cak-...abc",
                            "created_at": "2025-08-01T12:00:00Z",
                            "last_used_at": None,
                            "revoked_at": None,
                        }
                    ],
                    "pagination": {"has_more": False, "next_offset": None},
                },
            )
        )
        agent = Agent.from_dict(client, "test-org", AGENT_RESPONSE)
        keys = list(agent.api_keys.list())
        assert len(keys) == 1
        assert isinstance(keys[0], APIKey)
        assert keys[0].id == "key-1"
        assert keys[0].name == "dev-key"
        assert keys[0].token_hint == "cak-...abc"

    def test_create_returns_apikey_with_token(self, mock_api, client):
        """Create surfaces the plaintext token exactly once on the returned APIKey."""
        route = mock_api.post("/organizations/test-org/agents/my-agent/auth/keys").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "key-2",
                    "name": "new-key",
                    "description": "",
                    "token": "cak-full-secret-token",
                    "token_hint": "cak-...token",
                },
            )
        )
        agent = Agent.from_dict(client, "test-org", AGENT_RESPONSE)
        key = agent.api_keys.create("new-key")
        assert isinstance(key, APIKey)
        assert key.id == "key-2"
        assert key.token == "cak-full-secret-token"
        assert route.called

    def test_get(self, mock_api, client):
        mock_api.get("/organizations/test-org/agents/my-agent/auth/keys/key-1").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "key-1",
                    "name": "dev-key",
                    "description": "Development key",
                    "token_hint": "cak-...abc",
                    "created_at": "2025-08-01T12:00:00Z",
                    "last_used_at": None,
                    "revoked_at": None,
                },
            )
        )
        agent = Agent.from_dict(client, "test-org", AGENT_RESPONSE)
        key = agent.api_keys.get("key-1")
        assert isinstance(key, APIKey)
        assert key.id == "key-1"
        assert key.name == "dev-key"
        assert key.token_hint == "cak-...abc"

    def test_revoke(self, mock_api, client):
        mock_api.get("/organizations/test-org/agents/my-agent/auth/keys/key-1").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "key-1",
                    "name": "dev-key",
                    "description": "",
                    "token_hint": "cak-...abc",
                    "created_at": "2025-08-01T12:00:00Z",
                    "last_used_at": None,
                    "revoked_at": None,
                },
            )
        )
        route = mock_api.delete("/organizations/test-org/agents/my-agent/auth/keys/key-1").mock(
            return_value=httpx.Response(204)
        )
        agent = Agent.from_dict(client, "test-org", AGENT_RESPONSE)
        key = agent.api_keys.get("key-1")
        key.revoke()
        assert route.called


class TestOrganizationSubCollections:
    def test_agents_property(self, client):
        org = _org(client)
        assert isinstance(org, Organization)
        assert isinstance(org.agents, Agents)

    def test_repositories_property(self, client):
        org = _org(client)
        assert isinstance(org.repositories, Repositories)

    def test_list_repositories(self, mock_api, client):
        mock_api.get("/organizations/test-org/repositories").mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "id": "repo-1",
                            "organization_id": "org-1",
                            "name": "repo-one",
                            "description": "First repo",
                        }
                    ],
                    "pagination": {"has_more": False, "next_offset": None},
                },
            )
        )
        repos = list(_org(client).repositories.list())
        assert len(repos) == 1
        assert isinstance(repos[0], Repository)
        assert repos[0].name == "repo-one"

    def test_create_repository_returns_repository(self, mock_api, client):
        route = mock_api.post("/organizations/test-org/repositories").mock(
            return_value=httpx.Response(
                201,
                json={
                    "id": "repo-new",
                    "organization_id": "org-1",
                    "name": "my-repo",
                    "description": "A new repo",
                    "visibility": "private",
                    "created_by": "user-1",
                    "created_at": "2025-08-01T12:00:00Z",
                },
            )
        )
        repo = _org(client).repositories.create("my-repo", description="A new repo")
        assert isinstance(repo, Repository)
        assert repo.id == "repo-new"
        assert repo.name == "my-repo"
        assert repo.description == "A new repo"
        assert repo.visibility == "private"
        assert route.called
