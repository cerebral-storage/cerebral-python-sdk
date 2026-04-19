"""Imports collection and ImportJob entity."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tilde._isoparse import parse_optional as _parse_dt

if TYPE_CHECKING:
    from datetime import datetime

    from tilde.client import Client


class ImportJob:
    """A single repository-import job."""

    def __init__(
        self,
        client: Client,
        org: str,
        repo: str,
        *,
        id: str = "",
        status: str = "",
        repository_id: str = "",
        connector_id: str = "",
        source_prefix: str = "",
        destination_path: str = "",
        commit_message: str = "",
        objects_imported: int | None = None,
        commit_id: str = "",
        error: str = "",
        source_repository_id: str = "",
        source_organization: str = "",
        source_repository: str = "",
        created_by_type: str = "",
        created_by: str = "",
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        self._client = client
        self._org = org
        self._repo = repo
        self.id = id
        self.status = status
        self.repository_id = repository_id
        self.connector_id = connector_id
        self.source_prefix = source_prefix
        self.destination_path = destination_path
        self.commit_message = commit_message
        self.objects_imported = objects_imported
        self.commit_id = commit_id
        self.error = error
        self.source_repository_id = source_repository_id
        self.source_organization = source_organization
        self.source_repository = source_repository
        self.created_by_type = created_by_type
        self.created_by = created_by
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self) -> str:
        return f"ImportJob(id={self.id!r}, status={self.status!r})"

    @classmethod
    def from_dict(cls, client: Client, org: str, repo: str, d: dict[str, Any]) -> ImportJob:
        return cls(
            client,
            org,
            repo,
            id=d.get("id", ""),
            status=d.get("status", ""),
            repository_id=d.get("repository_id", ""),
            connector_id=d.get("connector_id", ""),
            source_prefix=d.get("source_prefix", ""),
            destination_path=d.get("destination_path", ""),
            commit_message=d.get("commit_message", ""),
            objects_imported=d.get("objects_imported"),
            commit_id=d.get("commit_id", ""),
            error=d.get("error", ""),
            source_repository_id=d.get("source_repository_id", ""),
            source_organization=d.get("source_organization", ""),
            source_repository=d.get("source_repository", ""),
            created_by_type=d.get("created_by_type", ""),
            created_by=d.get("created_by", ""),
            created_at=_parse_dt(d.get("created_at")),
            updated_at=_parse_dt(d.get("updated_at")),
        )

    def refresh(self) -> ImportJob:
        """Re-fetch this job's status from the server."""
        data = self._client._get_json(
            f"/organizations/{self._org}/repositories/{self._repo}/import/{self.id}"
        )
        fresh = ImportJob.from_dict(self._client, self._org, self._repo, data)
        self.__dict__.update(fresh.__dict__)
        return self


class Imports:
    """Import jobs queued on a repository.

    Two distinct sources — external connector vs another Tilde repository —
    are supported via :meth:`create_from_connector` and
    :meth:`create_from_repository`. Both return a fully-populated
    :class:`ImportJob` (by calling GET immediately after the POST).
    """

    def __init__(self, client: Client, org: str, repo: str) -> None:
        self._client = client
        self._org = org
        self._repo = repo

    def __repr__(self) -> str:
        return f"Imports({self._org}/{self._repo})"

    @property
    def _base_path(self) -> str:
        return f"/organizations/{self._org}/repositories/{self._repo}/import"

    def get(self, job_id: str) -> ImportJob:
        data = self._client._get_json(f"{self._base_path}/{job_id}")
        return ImportJob.from_dict(self._client, self._org, self._repo, data)

    def create_from_connector(
        self,
        connector_id: str,
        destination_path: str,
        *,
        source_prefix: str | None = None,
        commit_message: str | None = None,
    ) -> ImportJob:
        """Queue an import from an external connector."""
        body: dict[str, Any] = {
            "connector_id": connector_id,
            "destination_path": destination_path,
        }
        if source_prefix is not None:
            body["source_prefix"] = source_prefix
        if commit_message is not None:
            body["commit_message"] = commit_message
        data = self._client._post_json(self._base_path, json=body)
        job_id = str(data.get("job_id", ""))
        return self.get(job_id)

    def create_from_repository(
        self,
        repo_path: str,
        destination_path: str,
        *,
        source_prefix: str | None = None,
        commit_message: str | None = None,
    ) -> ImportJob:
        """Queue a cross-repository import.

        Args:
            repo_path: Source repository in ``"org/repo"`` format.
        """
        parts = repo_path.split("/", 1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError(f"Invalid repository path {repo_path!r}: expected 'org/repo' format")
        body: dict[str, Any] = {
            "source_organization": parts[0],
            "source_repository": parts[1],
            "destination_path": destination_path,
        }
        if source_prefix is not None:
            body["source_prefix"] = source_prefix
        if commit_message is not None:
            body["commit_message"] = commit_message
        data = self._client._post_json(self._base_path, json=body)
        job_id = str(data.get("job_id", ""))
        return self.get(job_id)
