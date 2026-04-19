"""Organization entity and the Organizations / Members collections."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tilde._isoparse import parse_optional as _parse_dt
from tilde._pagination import PageResult, PaginatedIterator

if TYPE_CHECKING:
    from datetime import datetime

    from tilde.client import Client
    from tilde.resources.agents import Agents
    from tilde.resources.connectors import Connectors
    from tilde.resources.groups import Groups
    from tilde.resources.policies import Policies
    from tilde.resources.repositories import Repositories
    from tilde.resources.roles import Roles


class Organization:
    """A Tilde organization."""

    def __init__(
        self,
        client: Client,
        *,
        id: str = "",
        name: str = "",
        display_name: str = "",
        created_at: datetime | None = None,
    ) -> None:
        self._client = client
        self.id = id
        self.name = name
        self.display_name = display_name
        self.created_at = created_at

    def __repr__(self) -> str:
        return f"Organization({self.name!r})"

    @classmethod
    def from_dict(cls, client: Client, d: dict[str, Any]) -> Organization:
        return cls(
            client,
            id=d.get("id", ""),
            name=d.get("name", ""),
            display_name=d.get("display_name", ""),
            created_at=_parse_dt(d.get("created_at")),
        )

    # -- Sub-collections ------------------------------------------------------

    @property
    def repositories(self) -> Repositories:
        from tilde.resources.repositories import Repositories

        return Repositories(self._client, self.name)

    @property
    def members(self) -> Members:
        return Members(self._client, self.name)

    @property
    def agents(self) -> Agents:
        from tilde.resources.agents import Agents

        return Agents(self._client, self.name)

    @property
    def roles(self) -> Roles:
        from tilde.resources.roles import Roles

        return Roles(self._client, self.name)

    @property
    def groups(self) -> Groups:
        from tilde.resources.groups import Groups

        return Groups(self._client, self.name)

    @property
    def policies(self) -> Policies:
        from tilde.resources.policies import Policies

        return Policies(self._client, self.name)

    @property
    def connectors(self) -> Connectors:
        from tilde.resources.connectors import Connectors

        return Connectors(self._client, self.name)

    def delete(self) -> None:
        """Delete this organization."""
        self._client._delete(f"/organizations/{self.name}")


class Member:
    """A member of an organization."""

    def __init__(
        self,
        client: Client,
        org: str,
        *,
        user_id: str = "",
        username: str = "",
        full_name: str = "",
        email: str = "",
        organization_id: str = "",
        joined_at: datetime | None = None,
    ) -> None:
        self._client = client
        self._org = org
        self.user_id = user_id
        self.username = username
        self.full_name = full_name
        self.email = email
        self.organization_id = organization_id
        self.joined_at = joined_at

    def __repr__(self) -> str:
        return f"Member({self.username!r})"

    @classmethod
    def from_dict(cls, client: Client, org: str, d: dict[str, Any]) -> Member:
        return cls(
            client,
            org,
            user_id=d.get("user_id", ""),
            username=d.get("username", "") or "",
            full_name=d.get("full_name", "") or "",
            email=d.get("email", "") or "",
            organization_id=d.get("organization_id", ""),
            joined_at=_parse_dt(d.get("joined_at")),
        )

    def delete(self) -> None:
        """Remove this member from the organization."""
        self._client._delete(f"/organizations/{self._org}/members/{self.user_id}")


class Members:
    """Members of an organization."""

    def __init__(self, client: Client, org: str) -> None:
        self._client = client
        self._org = org

    def __repr__(self) -> str:
        return f"Members(org={self._org!r})"

    def list(self, *, amount: int | None = None) -> PaginatedIterator[Member]:
        """Lazily iterate the organization's members.

        The server returns the whole list in one response today; the iterator
        fires a single HTTP GET on first iteration so the contract can be
        upgraded to real pagination without breaking callers. ``amount``
        caps the total number of results yielded by the iterator.
        """
        client = self._client
        org = self._org

        def fetch_page(cursor: str | None) -> PageResult[Member]:
            data = client._get_json(f"/organizations/{org}/members")
            items = [Member.from_dict(client, org, d) for d in data.get("results", [])]
            return PageResult(items=items, has_more=False, next_offset=None)

        return PaginatedIterator(fetch_page, limit=amount)

    def get(self, user_id: str) -> Member:
        """Get a member by user ID.

        The server does not expose a per-member GET endpoint; this method
        looks the member up in the org member list.
        """
        for member in self.list():
            if member.user_id == user_id or member.username == user_id:
                return member
        from tilde.exceptions import NotFoundError

        raise NotFoundError(
            404,
            message=f"Member {user_id!r} not found in organization {self._org!r}",
        )

    def create(self, username: str) -> Member:
        """Add a user to this organization by username."""
        self._client._post(
            f"/organizations/{self._org}/members",
            json={"username": username},
        )
        return self.get(username)

    def delete(self, user_id: str) -> None:
        """Remove a member from the organization."""
        self._client._delete(f"/organizations/{self._org}/members/{user_id}")


class Organizations:
    """Organizations the authenticated principal can access."""

    def __init__(self, client: Client) -> None:
        self._client = client

    def __repr__(self) -> str:
        return "Organizations()"

    def list(self, *, amount: int | None = None) -> PaginatedIterator[Organization]:
        """Lazily iterate the organizations the principal belongs to.

        ``amount`` caps the total number of results yielded by the iterator.
        """
        client = self._client

        def fetch_page(cursor: str | None) -> PageResult[Organization]:
            data = client._get_json("/organizations")
            items = [Organization.from_dict(client, d) for d in data.get("results", [])]
            return PageResult(items=items, has_more=False, next_offset=None)

        return PaginatedIterator(fetch_page, limit=amount)

    def get(self, name: str) -> Organization:
        """Get an organization by slug."""
        data = self._client._get_json(f"/organizations/{name}")
        return Organization.from_dict(self._client, data)

    def create(self, name: str, display_name: str) -> Organization:
        """Create an organization."""
        data = self._client._post_json(
            "/organizations",
            json={"name": name, "display_name": display_name},
        )
        return Organization.from_dict(self._client, data)

    def delete(self, name: str) -> None:
        """Delete an organization."""
        self._client._delete(f"/organizations/{name}")
