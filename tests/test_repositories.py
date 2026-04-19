"""Tests for Repository entity and Repositories collection."""

import httpx

from tilde.models import Repository
from tilde.resources.sessions import Session


class TestRepository:
    def test_lazy_loading(self, mock_api, repo):
        """Accessing .description triggers GET /organizations/test-org/repositories/test-repo."""
        mock_api.get("/organizations/test-org/repositories/test-repo").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "repo-1",
                    "organization_id": "org-1",
                    "name": "test-repo",
                    "description": "A test repository",
                    "visibility": "private",
                    "created_by": "user-1",
                    "created_at": "2025-01-15T10:00:00Z",
                },
            )
        )
        desc = repo.description
        assert desc == "A test repository"

    def test_properties(self, mock_api, repo):
        """All lazy-loaded properties are correctly populated."""
        mock_api.get("/organizations/test-org/repositories/test-repo").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "repo-1",
                    "organization_id": "org-1",
                    "name": "test-repo",
                    "description": "desc",
                    "visibility": "public",
                    "created_by": "user-42",
                    "created_at": "2025-06-01T12:30:00Z",
                },
            )
        )
        assert repo.id == "repo-1"
        assert repo.description == "desc"
        assert repo.visibility == "public"
        assert repo.created_by == "user-42"
        assert repo.created_at is not None
        assert repo.created_at.year == 2025

    def test_update_returns_repository(self, mock_api, repo):
        """PUT returns a Repository (never a data struct)."""
        route = mock_api.put("/organizations/test-org/repositories/test-repo").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "repo-1",
                    "organization_id": "org-1",
                    "name": "test-repo",
                    "description": "updated desc",
                    "visibility": "private",
                    "created_by": "user-1",
                    "created_at": "2025-01-15T10:00:00Z",
                },
            )
        )
        result = repo.update(description="updated desc", visibility="private")
        assert isinstance(result, Repository)
        assert result.description == "updated desc"
        # update() returns self, mutating it in place
        assert result is repo
        assert route.called

    def test_delete(self, mock_api, repo):
        """DELETE /organizations/test-org/repositories/test-repo."""
        route = mock_api.delete("/organizations/test-org/repositories/test-repo").mock(
            return_value=httpx.Response(204)
        )
        repo.delete()
        assert route.called

    def test_session(self, mock_api, repo):
        """repo.session() creates a Session via POST .../sessions."""
        mock_api.post("/organizations/test-org/repositories/test-repo/sessions").mock(
            return_value=httpx.Response(201, json={"session_id": "sess-repo-1"})
        )
        session = repo.session()
        assert isinstance(session, Session)
        assert session.session_id == "sess-repo-1"

    def test_attach(self, repo):
        """repo.attach() returns a Session without API call."""
        session = repo.attach("sess-existing")
        assert isinstance(session, Session)
        assert session.session_id == "sess-existing"

    def test_update_with_retention_settings(self, mock_api, repo):
        """update() sends session_max_duration_days and retention_days."""
        route = mock_api.put("/organizations/test-org/repositories/test-repo").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "repo-1",
                    "organization_id": "org-1",
                    "name": "test-repo",
                    "description": "",
                    "visibility": "private",
                    "session_max_duration_days": 3,
                    "retention_days": 30,
                    "created_by": "user-1",
                    "created_at": "2025-01-15T10:00:00Z",
                },
            )
        )
        result = repo.update(session_max_duration_days=3, retention_days=30)
        assert isinstance(result, Repository)
        assert result.session_max_duration_days == 3
        assert result.retention_days == 30
        assert route.called

    def test_retention_properties(self, mock_api, repo):
        """Lazy-loaded session_max_duration_days and retention_days properties."""
        mock_api.get("/organizations/test-org/repositories/test-repo").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "repo-1",
                    "organization_id": "org-1",
                    "name": "test-repo",
                    "description": "",
                    "visibility": "private",
                    "session_max_duration_days": 7,
                    "retention_days": 14,
                    "created_by": "user-1",
                    "created_at": "2025-01-15T10:00:00Z",
                },
            )
        )
        assert repo.session_max_duration_days == 7
        assert repo.retention_days == 14


class TestRepositories:
    def test_list_returns_repositories(self, mock_api, client):
        """Repositories.list() returns Repository entities, not data structs."""
        mock_api.get("/organizations/test-org/repositories").mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "id": "repo-1",
                            "organization_id": "org-1",
                            "name": "alpha",
                            "description": "A",
                            "visibility": "private",
                            "created_at": "2025-01-15T10:00:00Z",
                        },
                        {
                            "id": "repo-2",
                            "organization_id": "org-1",
                            "name": "beta",
                            "description": "B",
                            "visibility": "public",
                            "created_at": "2025-01-15T10:00:00Z",
                        },
                    ],
                    "pagination": {"has_more": False},
                },
            )
        )
        from tilde.resources.organizations import Organization

        repos = list(Organization(client, name="test-org").repositories.list())
        assert len(repos) == 2
        assert all(isinstance(r, Repository) for r in repos)
        assert repos[0].name == "alpha"
        assert repos[1].name == "beta"

    def test_create_returns_repository(self, mock_api, client):
        """Repositories.create() returns a Repository entity."""
        mock_api.post("/organizations/test-org/repositories").mock(
            return_value=httpx.Response(
                201,
                json={
                    "id": "repo-new",
                    "organization_id": "org-1",
                    "name": "created",
                    "description": "",
                    "visibility": "private",
                    "created_at": "2025-01-15T10:00:00Z",
                },
            )
        )
        from tilde.resources.organizations import Organization

        repo = Organization(client, name="test-org").repositories.create("created")
        assert isinstance(repo, Repository)
        assert repo.name == "created"

    def test_get_returns_repository(self, client):
        """Repositories.get() returns an unloaded Repository handle without a network call."""
        from tilde.resources.organizations import Organization

        repo = Organization(client, name="test-org").repositories.get("docs")
        assert isinstance(repo, Repository)
        assert repo.name == "docs"
