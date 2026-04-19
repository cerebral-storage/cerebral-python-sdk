"""Secret entity and Secrets collection."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tilde._isoparse import parse_optional as _parse_dt
from tilde._pagination import PageResult, PaginatedIterator

if TYPE_CHECKING:
    from datetime import datetime

    from tilde.client import Client


class Secret:
    """A single secret entry.

    ``value`` is populated when the secret is fetched via
    :meth:`Secrets.get`.  List responses return ``Secret`` objects with
    metadata only — accessing ``value`` on one of those triggers a
    lazy fetch.
    """

    def __init__(
        self,
        client: Client,
        base_path: str,
        *,
        name: str,
        value: str | None = None,
        created_by_type: str = "",
        created_by: str = "",
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        self._client = client
        self._base_path = base_path
        self.name = name
        self._value = value
        self.created_by_type = created_by_type
        self.created_by = created_by
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self) -> str:
        return f"Secret({self.name!r})"

    @classmethod
    def from_dict(cls, client: Client, base_path: str, d: dict[str, Any]) -> Secret:
        return cls(
            client,
            base_path,
            name=d.get("key", d.get("name", "")),
            value=d.get("value"),
            created_by_type=d.get("created_by_type", ""),
            created_by=d.get("created_by", ""),
            created_at=_parse_dt(d.get("created_at")),
            updated_at=_parse_dt(d.get("updated_at")),
        )

    @property
    def value(self) -> str:
        """The decrypted secret value. Fetched on first access if not cached."""
        if self._value is None:
            data = self._client._get_json(f"{self._base_path}/{self.name}")
            self._value = str(data.get("value", ""))
        return self._value

    def delete(self) -> None:
        self._client._delete(f"{self._base_path}/{self.name}")


class Secrets:
    """Secrets stored at a repository or an agent."""

    def __init__(self, client: Client, base_path: str) -> None:
        self._client = client
        self._base_path = base_path

    def __repr__(self) -> str:
        return f"Secrets(path={self._base_path!r})"

    def list(self, *, amount: int | None = None) -> PaginatedIterator[Secret]:
        """Lazily iterate secrets. ``amount`` caps the total results yielded."""
        client = self._client
        base = self._base_path

        def fetch_page(cursor: str | None) -> PageResult[Secret]:
            data = client._get_json(base)
            items = [Secret.from_dict(client, base, d) for d in data.get("results", [])]
            return PageResult(items=items, has_more=False, next_offset=None)

        return PaginatedIterator(fetch_page, limit=amount)

    def get(self, name: str) -> Secret:
        data = self._client._get_json(f"{self._base_path}/{name}")
        value = str(data.get("value", ""))
        return Secret(
            self._client,
            self._base_path,
            name=name,
            value=value,
        )

    def create(self, name: str, value: str) -> Secret:
        """Create or update a secret."""
        self._client._put_json(f"{self._base_path}/{name}", json={"value": value})
        return Secret(
            self._client,
            self._base_path,
            name=name,
            value=value,
        )

    def delete(self, name: str) -> None:
        self._client._delete(f"{self._base_path}/{name}")
