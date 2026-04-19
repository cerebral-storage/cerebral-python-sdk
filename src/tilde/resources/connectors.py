"""Connector entity and its plural collections."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tilde._isoparse import parse_optional as _parse_dt
from tilde._pagination import PageResult, PaginatedIterator

if TYPE_CHECKING:
    from datetime import datetime

    from tilde.client import Client


class Connector:
    """An external data source connector (S3, GCS, etc.)."""

    def __init__(
        self,
        client: Client,
        org: str,
        *,
        id: str = "",
        name: str = "",
        type: str = "",
        source_uri: str = "",
        disabled: bool = False,
        public_key: str | None = None,
        created_at: datetime | None = None,
    ) -> None:
        self._client = client
        self._org = org
        self.id = id
        self.name = name
        self.type = type
        self.source_uri = source_uri
        self.disabled = disabled
        self.public_key = public_key
        self.created_at = created_at

    def __repr__(self) -> str:
        return f"Connector({self.name!r}, type={self.type!r})"

    @classmethod
    def from_dict(cls, client: Client, org: str, d: dict[str, Any]) -> Connector:
        return cls(
            client,
            org,
            id=d.get("id", ""),
            name=d.get("name", ""),
            type=d.get("type", ""),
            source_uri=d.get("source_uri", ""),
            disabled=d.get("disabled", False),
            public_key=d.get("public_key"),
            created_at=_parse_dt(d.get("created_at")),
        )

    def delete(self) -> None:
        self._client._delete(f"/organizations/{self._org}/connectors/{self.id}")


class Connectors:
    """Org-level connector CRUD."""

    def __init__(self, client: Client, org: str) -> None:
        self._client = client
        self._org = org

    def __repr__(self) -> str:
        return f"Connectors(org={self._org!r})"

    @property
    def _base_path(self) -> str:
        return f"/organizations/{self._org}/connectors"

    def list(self, *, amount: int | None = None) -> PaginatedIterator[Connector]:
        """Lazily iterate connectors. ``amount`` caps the total results yielded."""
        client = self._client
        org = self._org
        base = self._base_path

        def fetch_page(cursor: str | None) -> PageResult[Connector]:
            data = client._get_json(base)
            items = [Connector.from_dict(client, org, d) for d in data.get("results", [])]
            return PageResult(items=items, has_more=False, next_offset=None)

        return PaginatedIterator(fetch_page, limit=amount)

    def get(self, connector_id: str) -> Connector:
        data = self._client._get_json(f"{self._base_path}/{connector_id}")
        return Connector.from_dict(self._client, self._org, data)

    def create(
        self,
        name: str,
        type: str,
        source_uri: str,
        config: dict[str, Any],
    ) -> Connector:
        data = self._client._post_json(
            self._base_path,
            json={"name": name, "type": type, "source_uri": source_uri, "config": config},
        )
        return Connector.from_dict(self._client, self._org, data)

    def delete(self, connector_id: str) -> None:
        self._client._delete(f"{self._base_path}/{connector_id}")


class RepositoryConnectors:
    """Repository-scoped connector attachment operations."""

    def __init__(self, client: Client, org: str, repo: str) -> None:
        self._client = client
        self._org = org
        self._repo = repo

    def __repr__(self) -> str:
        return f"RepositoryConnectors({self._org}/{self._repo})"

    @property
    def _base_path(self) -> str:
        return f"/organizations/{self._org}/repositories/{self._repo}/connectors"

    def list(self, *, amount: int | None = None) -> PaginatedIterator[Connector]:
        """Lazily iterate attached connectors. ``amount`` caps the total results yielded."""
        client = self._client
        org = self._org
        base = self._base_path

        def fetch_page(cursor: str | None) -> PageResult[Connector]:
            data = client._get_json(base)
            items = [Connector.from_dict(client, org, d) for d in data.get("results", [])]
            return PageResult(items=items, has_more=False, next_offset=None)

        return PaginatedIterator(fetch_page, limit=amount)

    def attach(self, connector_id: str) -> None:
        self._client._post(self._base_path, json={"connector_id": connector_id})

    def detach(self, connector_id: str) -> None:
        self._client._delete(f"{self._base_path}/{connector_id}")
