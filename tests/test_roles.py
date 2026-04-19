"""Tests for Role, Roles, APIKey on roles, and the Organization.roles accessor."""

import httpx

from tilde.models import APIKey, Organization, Role, Roles

ROLE_RESPONSE = {
    "id": "role-1",
    "organization_id": "org-1",
    "name": "my-role",
    "description": "Test role",
    "created_by": "user-1",
    "created_by_name": "Alice",
    "created_at": "2025-08-01T12:00:00Z",
    "last_used_at": None,
}


def _org(client):
    return Organization(client, name="test-org")


class TestRoles:
    def test_create(self, mock_api, client):
        route = mock_api.post("/organizations/test-org/roles").mock(
            return_value=httpx.Response(200, json=ROLE_RESPONSE)
        )
        role = _org(client).roles.create("my-role", description="Test role")
        assert isinstance(role, Role)
        assert role.name == "my-role"
        assert role.id == "role-1"
        assert role.description == "Test role"
        assert role.created_by == "user-1"
        assert role.created_by_name == "Alice"
        assert route.called

    def test_get(self, mock_api, client):
        mock_api.get("/organizations/test-org/roles/my-role").mock(
            return_value=httpx.Response(200, json=ROLE_RESPONSE)
        )
        role = _org(client).roles.get("my-role")
        assert isinstance(role, Role)
        assert role.name == "my-role"
        assert role.id == "role-1"

    def test_list(self, mock_api, client):
        mock_api.get("/organizations/test-org/roles").mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        ROLE_RESPONSE,
                        {**ROLE_RESPONSE, "id": "role-2", "name": "other-role"},
                    ],
                    "pagination": {"has_more": False, "next_offset": None},
                },
            )
        )
        roles = list(_org(client).roles.list())
        assert len(roles) == 2
        assert all(isinstance(r, Role) for r in roles)
        assert roles[0].name == "my-role"
        assert roles[1].name == "other-role"

    def test_delete(self, mock_api, client):
        route = mock_api.delete("/organizations/test-org/roles/my-role").mock(
            return_value=httpx.Response(204)
        )
        _org(client).roles.delete("my-role")
        assert route.called


class TestRoleAPIKeys:
    def test_list(self, mock_api, client):
        mock_api.get("/organizations/test-org/roles/my-role/auth/keys").mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "id": "key-1",
                            "name": "dev-key",
                            "description": "",
                            "token_hint": "crk-...abc",
                            "created_at": "2025-08-01T12:00:00Z",
                            "last_used_at": None,
                            "revoked_at": None,
                        }
                    ],
                    "pagination": {"has_more": False, "next_offset": None},
                },
            )
        )
        role = Role.from_dict(client, "test-org", ROLE_RESPONSE)
        keys = list(role.api_keys.list())
        assert len(keys) == 1
        assert isinstance(keys[0], APIKey)
        assert keys[0].id == "key-1"

    def test_create_returns_apikey_with_token(self, mock_api, client):
        route = mock_api.post("/organizations/test-org/roles/my-role/auth/keys").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "key-2",
                    "name": "new-key",
                    "description": "",
                    "token": "crk-full-secret-token",
                },
            )
        )
        role = Role.from_dict(client, "test-org", ROLE_RESPONSE)
        key = role.api_keys.create("new-key")
        assert isinstance(key, APIKey)
        assert key.id == "key-2"
        assert key.token == "crk-full-secret-token"
        assert route.called

    def test_get(self, mock_api, client):
        mock_api.get("/organizations/test-org/roles/my-role/auth/keys/key-1").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "key-1",
                    "name": "dev-key",
                    "description": "Development key",
                    "token_hint": "crk-...abc",
                    "created_at": "2025-08-01T12:00:00Z",
                    "last_used_at": None,
                    "revoked_at": None,
                },
            )
        )
        role = Role.from_dict(client, "test-org", ROLE_RESPONSE)
        key = role.api_keys.get("key-1")
        assert isinstance(key, APIKey)
        assert key.id == "key-1"

    def test_revoke(self, mock_api, client):
        mock_api.get("/organizations/test-org/roles/my-role/auth/keys/key-1").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "key-1",
                    "name": "dev-key",
                    "description": "",
                    "token_hint": "crk-...abc",
                    "created_at": "2025-08-01T12:00:00Z",
                    "last_used_at": None,
                    "revoked_at": None,
                },
            )
        )
        route = mock_api.delete("/organizations/test-org/roles/my-role/auth/keys/key-1").mock(
            return_value=httpx.Response(204)
        )
        role = Role.from_dict(client, "test-org", ROLE_RESPONSE)
        role.api_keys.get("key-1").revoke()
        assert route.called


class TestOrganizationRoles:
    def test_roles_property(self, client):
        org = _org(client)
        assert isinstance(org, Organization)
        assert isinstance(org.roles, Roles)
