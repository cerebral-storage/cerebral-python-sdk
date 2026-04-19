"""Commit entity and Commits collection."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tilde._isoparse import parse_optional as _parse_dt
from tilde._pagination import DEFAULT_PAGE_SIZE, PageResult, PaginatedIterator
from tilde._value_types import ListingEntry

if TYPE_CHECKING:
    from datetime import datetime

    from tilde.client import Client
    from tilde.resources.objects import ReadOnlyObjects


class Commit:
    """A commit in the repository timeline."""

    def __init__(
        self,
        client: Client,
        org: str,
        repo: str,
        *,
        id: str = "",
        committer: str = "",
        committer_type: str = "",
        committer_id: str = "",
        message: str = "",
        meta_range_id: str = "",
        creation_date: datetime | None = None,
        parents: list[str] | None = None,
        metadata: dict[str, str] | None = None,
        object_count: int | None = None,
        total_size: int | None = None,
        is_stale: bool = False,
    ) -> None:
        self._client = client
        self._org = org
        self._repo = repo
        self.id = id
        self._committer = committer
        self._committer_type = committer_type
        self._committer_id = committer_id
        self._message = message
        self._meta_range_id = meta_range_id
        self._creation_date = creation_date
        self._parents: list[str] = list(parents) if parents else []
        self._metadata: dict[str, str] = dict(metadata) if metadata else {}
        self._object_count = object_count
        self._total_size = total_size
        self._is_stale = is_stale
        self._loaded = bool(committer or message)

    def __repr__(self) -> str:
        return f"Commit(id={self.id!r})"

    @classmethod
    def from_dict(cls, client: Client, org: str, repo: str, d: dict[str, Any]) -> Commit:
        c = cls(
            client,
            org,
            repo,
            id=d.get("id", ""),
        )
        c._populate(d)
        return c

    def _populate(self, d: dict[str, Any]) -> None:
        self.id = d.get("id", self.id)
        self._committer = d.get("committer", self._committer)
        self._committer_type = d.get("committer_type", self._committer_type)
        self._committer_id = d.get("committer_id", self._committer_id)
        self._message = d.get("message", self._message)
        self._meta_range_id = d.get("meta_range_id", self._meta_range_id)
        creation_date = _parse_dt(d.get("creation_date"))
        if creation_date is not None:
            self._creation_date = creation_date
        if "parents" in d:
            self._parents = list(d.get("parents") or [])
        if "metadata" in d:
            self._metadata = dict(d.get("metadata") or {})
        if "object_count" in d:
            self._object_count = d.get("object_count")
        if "total_size" in d:
            self._total_size = d.get("total_size")
        self._is_stale = d.get("is_stale", self._is_stale)
        self._loaded = True

    @property
    def _repo_path(self) -> str:
        return f"/organizations/{self._org}/repositories/{self._repo}"

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        data = self._client._get_json(f"{self._repo_path}/commits/{self.id}")
        self._populate(data)

    @property
    def committer(self) -> str:
        self._ensure_loaded()
        return self._committer

    @property
    def committer_type(self) -> str:
        self._ensure_loaded()
        return self._committer_type

    @property
    def committer_id(self) -> str:
        self._ensure_loaded()
        return self._committer_id

    @property
    def message(self) -> str:
        self._ensure_loaded()
        return self._message

    @property
    def meta_range_id(self) -> str:
        self._ensure_loaded()
        return self._meta_range_id

    @property
    def creation_date(self) -> datetime | None:
        self._ensure_loaded()
        return self._creation_date

    @property
    def parents(self) -> list[str]:
        self._ensure_loaded()
        return list(self._parents)

    @property
    def metadata(self) -> dict[str, str]:
        self._ensure_loaded()
        return dict(self._metadata)

    @property
    def object_count(self) -> int | None:
        self._ensure_loaded()
        return self._object_count

    @property
    def total_size(self) -> int | None:
        self._ensure_loaded()
        return self._total_size

    @property
    def is_stale(self) -> bool:
        self._ensure_loaded()
        return self._is_stale

    @property
    def objects(self) -> ReadOnlyObjects:
        """Read-only object access at this commit's snapshot."""
        from tilde.resources.objects import ReadOnlyObjects

        return ReadOnlyObjects(self._client, self._org, self._repo)

    def revert(
        self,
        *,
        message: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> Commit:
        body: dict[str, Any] = {}
        if message is not None:
            body["message"] = message
        if metadata is not None:
            body["metadata"] = metadata
        data = self._client._post_json(f"{self._repo_path}/commits/{self.id}/revert", json=body)
        return Commit(self._client, self._org, self._repo, id=data["commit_id"])

    def diff(
        self,
        *,
        prefix: str | None = None,
        after: str | None = None,
        amount: int | None = None,
        page_size: int | None = None,
        delimiter: str | None = None,
    ) -> PaginatedIterator[ListingEntry]:
        """List changes introduced by this commit (diff against first parent).

        ``amount`` caps the total number of results yielded by the iterator.
        ``page_size`` sets the server-side page size used for each request.
        """
        self._ensure_loaded()
        left = self._parents[0] if self._parents else ""
        right = self.id
        initial_after = after
        repo_path = self._repo_path
        client = self._client

        def fetch_page(cursor: str | None) -> PageResult[ListingEntry]:
            params: dict[str, str | int] = {"left": left, "right": right}
            effective_after = cursor if cursor is not None else initial_after
            if effective_after is not None:
                params["after"] = effective_after
            if prefix is not None:
                params["prefix"] = prefix
            if delimiter is not None:
                params["delimiter"] = delimiter
            params["amount"] = page_size if page_size is not None else DEFAULT_PAGE_SIZE
            data = client._get_json(f"{repo_path}/diff", params=params)
            items = [ListingEntry.from_dict(d) for d in data.get("results", [])]
            pagination = data.get("pagination", {})
            return PageResult(
                items=items,
                has_more=pagination.get("has_more", False),
                next_offset=pagination.get("next_offset"),
                max_per_page=pagination.get("max_per_page"),
            )

        return PaginatedIterator(fetch_page, limit=amount)


class Commits:
    """Commits in a repository's timeline (newest first)."""

    def __init__(self, client: Client, org: str, repo: str) -> None:
        self._client = client
        self._org = org
        self._repo = repo

    def __repr__(self) -> str:
        return f"Commits({self._org}/{self._repo})"

    def list(
        self,
        *,
        ref: str | None = None,
        after: str | None = None,
        amount: int | None = None,
        page_size: int | None = None,
    ) -> PaginatedIterator[Commit]:
        """List commits (newest first).

        ``amount`` caps the total number of commits yielded by the iterator.
        ``page_size`` sets the server-side page size used for each request.
        """
        initial_after = after
        client = self._client
        org = self._org
        repo = self._repo

        def fetch_page(cursor: str | None) -> PageResult[Commit]:
            params: dict[str, str | int] = {}
            if ref is not None:
                params["ref"] = ref
            effective_after = cursor if cursor is not None else initial_after
            if effective_after is not None:
                params["after"] = effective_after
            params["amount"] = page_size if page_size is not None else DEFAULT_PAGE_SIZE
            data = client._get_json(f"/organizations/{org}/repositories/{repo}/log", params=params)
            items = [Commit.from_dict(client, org, repo, d) for d in data.get("results", [])]
            pagination = data.get("pagination", {})
            return PageResult(
                items=items,
                has_more=pagination.get("has_more", False),
                next_offset=pagination.get("next_offset"),
                max_per_page=pagination.get("max_per_page"),
            )

        return PaginatedIterator(fetch_page, limit=amount)

    def get(self, commit_id: str) -> Commit:
        """Get a commit by id."""
        data = self._client._get_json(
            f"/organizations/{self._org}/repositories/{self._repo}/commits/{commit_id}"
        )
        return Commit.from_dict(self._client, self._org, self._repo, data)
