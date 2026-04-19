"""Tests for Imports and ImportJob."""

import httpx
import pytest

from tilde.models import ImportJob


class TestImports:
    def test_create_from_connector_returns_importjob(self, mock_api, repo):
        """POST+GET roundtrip: create returns a fully-populated ImportJob."""
        mock_api.post("/organizations/test-org/repositories/test-repo/import").mock(
            return_value=httpx.Response(202, json={"job_id": "job-abc-123"})
        )
        mock_api.get("/organizations/test-org/repositories/test-repo/import/job-abc-123").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "job-abc-123",
                    "status": "queued",
                    "connector_id": "conn-1",
                    "source_prefix": "data/",
                    "destination_path": "imported/",
                    "commit_message": "Import data from S3",
                },
            )
        )
        job = repo.imports.create_from_connector(
            connector_id="conn-1",
            destination_path="imported/",
            source_prefix="data/",
            commit_message="Import data from S3",
        )
        assert isinstance(job, ImportJob)
        assert job.id == "job-abc-123"
        assert job.status == "queued"

    def test_create_from_repository_returns_importjob(self, mock_api, repo):
        mock_api.post("/organizations/test-org/repositories/test-repo/import").mock(
            return_value=httpx.Response(202, json={"job_id": "job-cross-1"})
        )
        mock_api.get("/organizations/test-org/repositories/test-repo/import/job-cross-1").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "job-cross-1",
                    "status": "queued",
                    "source_organization": "other-org",
                    "source_repository": "other-repo",
                    "destination_path": "cross-imported/",
                    "commit_message": "Cross-repo import",
                },
            )
        )
        job = repo.imports.create_from_repository(
            "other-org/other-repo",
            destination_path="cross-imported/",
            commit_message="Cross-repo import",
        )
        assert isinstance(job, ImportJob)
        assert job.id == "job-cross-1"

    def test_create_from_repository_invalid_path(self, repo):
        with pytest.raises(ValueError, match="expected 'org/repo' format"):
            repo.imports.create_from_repository("bad-path", destination_path="dest/")

    def test_get(self, mock_api, repo):
        mock_api.get("/organizations/test-org/repositories/test-repo/import/job-abc-123").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "job-abc-123",
                    "repository_id": "repo-1",
                    "connector_id": "conn-1",
                    "source_prefix": "data/",
                    "destination_path": "imported/",
                    "commit_message": "Import data from S3",
                    "status": "completed",
                    "objects_imported": 150,
                    "commit_id": "import-commit-id",
                    "error": "",
                    "created_by": "user-1",
                    "created_at": "2025-06-15T10:00:00Z",
                    "updated_at": "2025-06-15T10:05:00Z",
                },
            )
        )
        job = repo.imports.get("job-abc-123")
        assert isinstance(job, ImportJob)
        assert job.id == "job-abc-123"
        assert job.status == "completed"
        assert job.objects_imported == 150
        assert job.commit_id == "import-commit-id"
        assert job.source_prefix == "data/"

    def test_refresh(self, mock_api, repo):
        mock_api.get("/organizations/test-org/repositories/test-repo/import/job-abc-123").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "job-abc-123",
                    "status": "in_progress",
                    "objects_imported": 50,
                },
            )
        )
        job = repo.imports.get("job-abc-123")
        assert job.status == "in_progress"
        # Second call: now completed
        mock_api.get("/organizations/test-org/repositories/test-repo/import/job-abc-123").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "job-abc-123",
                    "status": "completed",
                    "objects_imported": 100,
                },
            )
        )
        job.refresh()
        assert job.status == "completed"
        assert job.objects_imported == 100
