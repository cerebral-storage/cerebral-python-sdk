"""Tests for Policy entity and Policies collection."""

import httpx
import pytest

from tilde.models import Attachment, EffectivePolicy, Organization, Policy, ValidationResult


class TestPolicies:
    @pytest.fixture
    def policies(self, client):
        return Organization(client, name="test-org").policies

    def test_create(self, mock_api, policies):
        route = mock_api.post("/organizations/test-org/policies").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "pol-1",
                    "organization_id": "org-1",
                    "name": "deny-deletes",
                    "description": "Deny all deletes",
                    "policy_text": "package tilde\ndefault allow = false",
                    "is_builtin": False,
                    "created_by": "user-1",
                    "created_at": "2025-04-01T10:00:00Z",
                },
            )
        )
        policy = policies.create(
            "deny-deletes",
            "package tilde\ndefault allow = false",
            description="Deny all deletes",
        )
        assert isinstance(policy, Policy)
        assert policy.id == "pol-1"
        assert policy.name == "deny-deletes"
        assert route.called

    def test_list(self, mock_api, policies):
        """list() yields Policy entities, not data summaries."""
        mock_api.get("/organizations/test-org/policies").mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "id": "pol-1",
                            "organization_id": "org-1",
                            "name": "deny-deletes",
                            "description": "",
                            "is_builtin": False,
                            "attachment_count": 2,
                        },
                    ],
                    "pagination": {"has_more": False, "next_offset": None, "max_per_page": 100},
                },
            )
        )
        items = list(policies.list())
        assert len(items) == 1
        assert isinstance(items[0], Policy)
        assert items[0].name == "deny-deletes"
        assert items[0].attachment_count == 2

    def test_get_returns_policy_with_attachments(self, mock_api, policies):
        mock_api.get("/organizations/test-org/policies/pol-1").mock(
            return_value=httpx.Response(
                200,
                json={
                    "policy": {
                        "id": "pol-1",
                        "organization_id": "org-1",
                        "name": "deny-deletes",
                        "description": "Deny all deletes",
                        "policy_text": "package tilde",
                        "is_builtin": False,
                        "created_by": "user-1",
                    },
                    "attachments": [
                        {
                            "policy_id": "pol-1",
                            "policy_name": "deny-deletes",
                            "principal_type": "user",
                            "principal_id": "user-1",
                            "principal_name": "alice",
                            "attached_by": "admin-1",
                        },
                    ],
                },
            )
        )
        policy = policies.get("pol-1")
        assert isinstance(policy, Policy)
        assert policy.name == "deny-deletes"
        attachments = policy.attachments
        assert len(attachments) == 1
        assert attachments[0].principal_id == "user-1"

    def test_update(self, mock_api, client):
        """Policy.update() PUTs to /policies/{id}."""
        mock_api.get("/organizations/test-org/policies/pol-1").mock(
            return_value=httpx.Response(
                200,
                json={
                    "policy": {
                        "id": "pol-1",
                        "organization_id": "org-1",
                        "name": "deny-deletes",
                        "description": "",
                        "policy_text": "",
                        "is_builtin": False,
                        "created_by": "user-1",
                    },
                    "attachments": [],
                },
            )
        )
        route = mock_api.put("/organizations/test-org/policies/pol-1").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "pol-1",
                    "organization_id": "org-1",
                    "name": "updated-policy",
                    "description": "Updated",
                    "policy_text": "package updated",
                    "is_builtin": False,
                    "created_by": "user-1",
                },
            )
        )
        policy = Organization(client, name="test-org").policies.get("pol-1")
        result = policy.update(name="updated-policy", policy_text="package updated")
        assert isinstance(result, Policy)
        assert result.name == "updated-policy"
        assert route.called

    def test_delete_from_collection(self, mock_api, policies):
        route = mock_api.delete("/organizations/test-org/policies/pol-1").mock(
            return_value=httpx.Response(204)
        )
        policies.delete("pol-1")
        assert route.called

    def test_validate(self, mock_api, policies):
        route = mock_api.post("/organizations/test-org/policies:validate").mock(
            return_value=httpx.Response(
                200,
                json={"valid": True, "errors": []},
            )
        )
        result = policies.validate("package tilde\ndefault allow = true")
        assert isinstance(result, ValidationResult)
        assert result.valid is True
        assert result.errors == []
        assert route.called

    def test_attach_via_entity(self, mock_api, client):
        mock_api.get("/organizations/test-org/policies/pol-1").mock(
            return_value=httpx.Response(
                200,
                json={
                    "policy": {
                        "id": "pol-1",
                        "organization_id": "org-1",
                        "name": "pol",
                        "description": "",
                        "policy_text": "",
                        "is_builtin": False,
                        "created_by": "u1",
                    },
                    "attachments": [],
                },
            )
        )
        route = mock_api.post("/organizations/test-org/policies/pol-1/attachments").mock(
            return_value=httpx.Response(201)
        )
        Organization(client, name="test-org").policies.get("pol-1").attach(
            principal_type="user", principal_id="user-1"
        )
        assert route.called

    def test_detach_via_entity(self, mock_api, client):
        mock_api.get("/organizations/test-org/policies/pol-1").mock(
            return_value=httpx.Response(
                200,
                json={
                    "policy": {
                        "id": "pol-1",
                        "organization_id": "org-1",
                        "name": "pol",
                        "description": "",
                        "policy_text": "",
                        "is_builtin": False,
                        "created_by": "u1",
                    },
                    "attachments": [],
                },
            )
        )
        route = mock_api.delete("/organizations/test-org/policies/pol-1/attachments").mock(
            return_value=httpx.Response(204)
        )
        Organization(client, name="test-org").policies.get("pol-1").detach(
            principal_type="user", principal_id="user-1"
        )
        assert route.called

    def test_attachments(self, mock_api, policies):
        mock_api.get("/organizations/test-org/attachments").mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "policy_id": "pol-1",
                            "policy_name": "deny-deletes",
                            "principal_type": "group",
                            "principal_id": "grp-1",
                            "principal_name": "engineers",
                            "attached_by": "admin-1",
                        },
                    ],
                },
            )
        )
        attachments = policies.attachments()
        assert len(attachments) == 1
        assert isinstance(attachments[0], Attachment)
        assert attachments[0].policy_id == "pol-1"

    def test_generate(self, mock_api, policies):
        route = mock_api.post("/organizations/test-org/policies:generate").mock(
            return_value=httpx.Response(200, json={"policy_text": "allow read *"})
        )
        result = policies.generate("allow reading everything")
        assert result == "allow read *"
        assert route.called

    def test_effective_by_user_id(self, mock_api, policies):
        mock_api.get("/organizations/test-org/effective-policies").mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "policy_id": "pol-1",
                            "policy_name": "deny-deletes",
                            "is_builtin": False,
                            "source": "direct",
                            "source_name": "alice",
                        },
                    ],
                },
            )
        )
        effective = policies.effective(user_id="user-1")
        assert len(effective) == 1
        assert isinstance(effective[0], EffectivePolicy)
        assert effective[0].source == "direct"

    def test_effective_by_principal(self, mock_api, policies):
        mock_api.get("/organizations/test-org/effective-policies").mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "policy_id": "pol-2",
                            "policy_name": "agent-policy",
                            "is_builtin": False,
                            "source": "group",
                            "source_name": "agents",
                        },
                    ],
                },
            )
        )
        effective = policies.effective(principal_type="agent", principal_id="agent-1")
        assert len(effective) == 1
        assert effective[0].source == "group"
