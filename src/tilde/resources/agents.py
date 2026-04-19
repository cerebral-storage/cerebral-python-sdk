"""Agent, APIKey, and their plural collections."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tilde._isoparse import parse_optional as _parse_dt
from tilde._pagination import DEFAULT_PAGE_SIZE, PageResult, PaginatedIterator

if TYPE_CHECKING:
    from datetime import datetime

    from tilde.client import Client
    from tilde.resources.secrets import Secrets


class APIKey:
    """An API key issued to an agent or role.

    ``token`` is populated only on the ``APIKeys.create(...)`` response (the
    only moment the full token is ever exposed). Afterwards ``token`` is
    ``""`` and the key is identified by ``id`` / ``name`` / ``token_hint``.
    """

    def __init__(
        self,
        client: Client,
        base_path: str,
        *,
        id: str = "",
        name: str = "",
        description: str = "",
        token_hint: str = "",
        token: str = "",
        created_at: datetime | None = None,
        last_used_at: datetime | None = None,
        revoked_at: datetime | None = None,
    ) -> None:
        self._client = client
        self._base_path = base_path
        self.id = id
        self.name = name
        self.description = description
        self.token_hint = token_hint
        self.token = token
        self.created_at = created_at
        self.last_used_at = last_used_at
        self.revoked_at = revoked_at

    def __repr__(self) -> str:
        return f"APIKey(name={self.name!r}, id={self.id!r})"

    @classmethod
    def from_dict(cls, client: Client, base_path: str, d: dict[str, Any]) -> APIKey:
        return cls(
            client,
            base_path,
            id=d.get("id", ""),
            name=d.get("name", ""),
            description=d.get("description", ""),
            token_hint=d.get("token_hint", ""),
            token=d.get("token", ""),
            created_at=_parse_dt(d.get("created_at")),
            last_used_at=_parse_dt(d.get("last_used_at")),
            revoked_at=_parse_dt(d.get("revoked_at")),
        )

    def revoke(self) -> None:
        """Revoke this API key."""
        self._client._delete(f"{self._base_path}/{self.id}")

    def delete(self) -> None:
        """Alias for :meth:`revoke`."""
        self.revoke()


class APIKeys:
    """API keys for an agent or role."""

    def __init__(self, client: Client, base_path: str) -> None:
        self._client = client
        self._base_path = base_path

    def __repr__(self) -> str:
        return f"APIKeys(path={self._base_path!r})"

    def list(
        self,
        *,
        after: str | None = None,
        amount: int | None = None,
        page_size: int | None = None,
    ) -> PaginatedIterator[APIKey]:
        initial_after = after
        client = self._client
        base = self._base_path

        def fetch_page(cursor: str | None) -> PageResult[APIKey]:
            params: dict[str, str | int] = {
                "amount": page_size if page_size is not None else DEFAULT_PAGE_SIZE
            }
            effective_after = cursor if cursor is not None else initial_after
            if effective_after is not None:
                params["after"] = effective_after
            data = client._get_json(base, params=params)
            items = [APIKey.from_dict(client, base, d) for d in data.get("results", [])]
            pagination = data.get("pagination", {})
            return PageResult(
                items=items,
                has_more=pagination.get("has_more", False),
                next_offset=pagination.get("next_offset"),
                max_per_page=pagination.get("max_per_page"),
            )

        return PaginatedIterator(fetch_page, limit=amount)

    def get(self, key_id: str) -> APIKey:
        data = self._client._get_json(f"{self._base_path}/{key_id}")
        return APIKey.from_dict(self._client, self._base_path, data)

    def create(self, name: str) -> APIKey:
        """Create a new API key.

        The returned :class:`APIKey` has its ``token`` field populated — this
        is the only opportunity to capture the full secret.
        """
        data = self._client._post_json(self._base_path, json={"name": name})
        return APIKey.from_dict(self._client, self._base_path, data)

    def delete(self, key_id: str) -> None:
        self._client._delete(f"{self._base_path}/{key_id}")


class Agent:
    """A Tilde agent."""

    def __init__(
        self,
        client: Client,
        org: str,
        *,
        id: str = "",
        name: str = "",
        description: str = "",
        metadata: dict[str, str] | None = None,
        inline_policy: str = "",
        inline_policy_updated_at: datetime | None = None,
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
        self.metadata = metadata or {}
        self.inline_policy = inline_policy
        self.inline_policy_updated_at = inline_policy_updated_at
        self.organization_id = organization_id
        self.created_by_type = created_by_type
        self.created_by = created_by
        self.created_by_name = created_by_name
        self.created_at = created_at
        self.last_used_at = last_used_at

    def __repr__(self) -> str:
        return f"Agent({self.name!r})"

    @classmethod
    def from_dict(cls, client: Client, org: str, d: dict[str, Any]) -> Agent:
        return cls(
            client,
            org,
            id=d.get("id", ""),
            name=d.get("name", ""),
            description=d.get("description", ""),
            metadata=d.get("metadata") or {},
            inline_policy=d.get("inline_policy", ""),
            inline_policy_updated_at=_parse_dt(d.get("inline_policy_updated_at")),
            organization_id=d.get("organization_id", ""),
            created_by_type=d.get("created_by_type", ""),
            created_by=d.get("created_by", ""),
            created_by_name=d.get("created_by_name", ""),
            created_at=_parse_dt(d.get("created_at")),
            last_used_at=_parse_dt(d.get("last_used_at")),
        )

    @property
    def _base_path(self) -> str:
        return f"/organizations/{self._org}/agents/{self.name}"

    @property
    def api_keys(self) -> APIKeys:
        return APIKeys(self._client, f"{self._base_path}/auth/keys")

    @property
    def secrets(self) -> Secrets:
        from tilde.resources.secrets import Secrets

        return Secrets(self._client, f"{self._base_path}/secrets")

    def update(
        self,
        *,
        description: str | None = None,
        metadata: dict[str, str] | None = None,
        inline_policy: str | None = None,
    ) -> Agent:
        body: dict[str, Any] = {}
        if description is not None:
            body["description"] = description
        if metadata is not None:
            body["metadata"] = metadata
        if inline_policy is not None:
            body["inline_policy"] = inline_policy
        data = self._client._put_json(self._base_path, json=body)
        return Agent.from_dict(self._client, self._org, data)

    def delete(self) -> None:
        self._client._delete(self._base_path)


class Agents:
    """Agents belonging to an organization."""

    def __init__(self, client: Client, org: str) -> None:
        self._client = client
        self._org = org

    def __repr__(self) -> str:
        return f"Agents(org={self._org!r})"

    @property
    def _base_path(self) -> str:
        return f"/organizations/{self._org}/agents"

    def list(
        self,
        *,
        after: str | None = None,
        amount: int | None = None,
        page_size: int | None = None,
    ) -> PaginatedIterator[Agent]:
        initial_after = after
        client = self._client
        org = self._org
        base = self._base_path

        def fetch_page(cursor: str | None) -> PageResult[Agent]:
            params: dict[str, str | int] = {
                "amount": page_size if page_size is not None else DEFAULT_PAGE_SIZE
            }
            effective_after = cursor if cursor is not None else initial_after
            if effective_after is not None:
                params["after"] = effective_after
            data = client._get_json(base, params=params)
            items = [Agent.from_dict(client, org, d) for d in data.get("results", [])]
            pagination = data.get("pagination", {})
            return PageResult(
                items=items,
                has_more=pagination.get("has_more", False),
                next_offset=pagination.get("next_offset"),
                max_per_page=pagination.get("max_per_page"),
            )

        return PaginatedIterator(fetch_page, limit=amount)

    def get(self, name: str) -> Agent:
        data = self._client._get_json(f"{self._base_path}/{name}")
        return Agent.from_dict(self._client, self._org, data)

    def create(
        self,
        name: str,
        *,
        description: str = "",
        metadata: dict[str, str] | None = None,
    ) -> Agent:
        body: dict[str, Any] = {"name": name, "description": description}
        if metadata is not None:
            body["metadata"] = metadata
        data = self._client._post_json(self._base_path, json=body)
        return Agent.from_dict(self._client, self._org, data)

    def delete(self, name: str) -> None:
        self._client._delete(f"{self._base_path}/{name}")
