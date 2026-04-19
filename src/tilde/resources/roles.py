"""Role entity and Roles collection."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tilde._isoparse import parse_optional as _parse_dt
from tilde._pagination import DEFAULT_PAGE_SIZE, PageResult, PaginatedIterator
from tilde.resources.agents import APIKeys

if TYPE_CHECKING:
    from datetime import datetime

    from tilde.client import Client


class Role:
    """A role — a named principal whose identity is assumed via an API key."""

    def __init__(
        self,
        client: Client,
        org: str,
        *,
        id: str = "",
        name: str = "",
        description: str = "",
        organization_id: str = "",
        created_by_type: str = "",
        created_by: str = "",
        created_by_name: str = "",
        created_at: datetime | None = None,
        last_used_at: datetime | None = None,
    ) -> None:
        self._client = client
        self._org = org
        self.id = id
        self.name = name
        self.description = description
        self.organization_id = organization_id
        self.created_by_type = created_by_type
        self.created_by = created_by
        self.created_by_name = created_by_name
        self.created_at = created_at
        self.last_used_at = last_used_at

    def __repr__(self) -> str:
        return f"Role({self.name!r})"

    @classmethod
    def from_dict(cls, client: Client, org: str, d: dict[str, Any]) -> Role:
        return cls(
            client,
            org,
            id=d.get("id", ""),
            name=d.get("name", ""),
            description=d.get("description", ""),
            organization_id=d.get("organization_id", ""),
            created_by_type=d.get("created_by_type", ""),
            created_by=d.get("created_by", ""),
            created_by_name=d.get("created_by_name", ""),
            created_at=_parse_dt(d.get("created_at")),
            last_used_at=_parse_dt(d.get("last_used_at")),
        )

    @property
    def _base_path(self) -> str:
        return f"/organizations/{self._org}/roles/{self.name}"

    @property
    def api_keys(self) -> APIKeys:
        return APIKeys(self._client, f"{self._base_path}/auth/keys")

    def delete(self) -> None:
        self._client._delete(self._base_path)


class Roles:
    """Roles belonging to an organization."""

    def __init__(self, client: Client, org: str) -> None:
        self._client = client
        self._org = org

    def __repr__(self) -> str:
        return f"Roles(org={self._org!r})"

    @property
    def _base_path(self) -> str:
        return f"/organizations/{self._org}/roles"

    def list(
        self,
        *,
        after: str | None = None,
        amount: int | None = None,
        page_size: int | None = None,
    ) -> PaginatedIterator[Role]:
        initial_after = after
        client = self._client
        org = self._org
        base = self._base_path

        def fetch_page(cursor: str | None) -> PageResult[Role]:
            params: dict[str, str | int] = {
                "amount": page_size if page_size is not None else DEFAULT_PAGE_SIZE
            }
            effective_after = cursor if cursor is not None else initial_after
            if effective_after is not None:
                params["after"] = effective_after
            data = client._get_json(base, params=params)
            items = [Role.from_dict(client, org, d) for d in data.get("results", [])]
            pagination = data.get("pagination", {})
            return PageResult(
                items=items,
                has_more=pagination.get("has_more", False),
                next_offset=pagination.get("next_offset"),
                max_per_page=pagination.get("max_per_page"),
            )

        return PaginatedIterator(fetch_page, limit=amount)

    def get(self, name: str) -> Role:
        data = self._client._get_json(f"{self._base_path}/{name}")
        return Role.from_dict(self._client, self._org, data)

    def create(self, name: str, *, description: str = "") -> Role:
        body: dict[str, str] = {"name": name, "description": description}
        data = self._client._post_json(self._base_path, json=body)
        return Role.from_dict(self._client, self._org, data)

    def delete(self, name: str) -> None:
        self._client._delete(f"{self._base_path}/{name}")
