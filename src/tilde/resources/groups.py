"""Group entity and Groups collection."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tilde._isoparse import parse_optional as _parse_dt
from tilde._pagination import DEFAULT_PAGE_SIZE, PageResult, PaginatedIterator
from tilde._value_types import Attachment, EffectiveGroup, GroupMember

if TYPE_CHECKING:
    import builtins
    from datetime import datetime

    from tilde.client import Client


class GroupMembers:
    """Members of a group."""

    def __init__(self, client: Client, org: str, group_id: str) -> None:
        self._client = client
        self._org = org
        self._group_id = group_id

    def __repr__(self) -> str:
        return f"GroupMembers(group_id={self._group_id!r})"

    @property
    def _base_path(self) -> str:
        return f"/organizations/{self._org}/groups/{self._group_id}/members"

    def list(self, *, amount: int | None = None) -> PaginatedIterator[GroupMember]:
        """Lazily iterate members currently attached to the group.

        ``amount`` caps the total number of results yielded by the iterator.
        """
        client = self._client
        group_path = f"/organizations/{self._org}/groups/{self._group_id}"

        def fetch_page(cursor: str | None) -> PageResult[GroupMember]:
            data = client._get_json(group_path)
            items = [GroupMember.from_dict(m) for m in data.get("members", [])]
            return PageResult(items=items, has_more=False, next_offset=None)

        return PaginatedIterator(fetch_page, limit=amount)

    def create(self, *, subject_type: str, subject_id: str) -> GroupMember:
        """Add a user or group to this group."""
        self._client._post(
            self._base_path,
            json={"subject_type": subject_type, "subject_id": subject_id},
        )
        for m in self.list():
            if m.subject_type == subject_type and m.subject_id == subject_id:
                return m
        return GroupMember(subject_type=subject_type, subject_id=subject_id)

    def delete(self, *, subject_type: str, subject_id: str) -> None:
        """Remove a member from the group."""
        self._client._delete(
            self._base_path,
            params={"subject_type": subject_type, "subject_id": subject_id},
        )


class Group:
    """A Tilde group (a collection of principals)."""

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
        created_at: datetime | None = None,
        members: builtins.list[GroupMember] | None = None,
        attachments: builtins.list[Attachment] | None = None,
    ) -> None:
        self._client = client
        self._org = org
        self.id = id
        self.name = name
        self.description = description
        self.organization_id = organization_id
        self.created_by_type = created_by_type
        self.created_by = created_by
        self.created_at = created_at
        self._members: builtins.list[GroupMember] = list(members) if members else []
        self._attachments: builtins.list[Attachment] = list(attachments) if attachments else []

    def __repr__(self) -> str:
        return f"Group({self.name!r})"

    @classmethod
    def from_dict(cls, client: Client, org: str, d: dict[str, Any]) -> Group:
        group_d = d.get("group", d) if "group" in d else d
        members = [GroupMember.from_dict(m) for m in d.get("members", [])]
        attachments = [Attachment.from_dict(a) for a in d.get("attachments", [])]
        return cls(
            client,
            org,
            id=group_d.get("id", ""),
            name=group_d.get("name", ""),
            description=group_d.get("description", ""),
            organization_id=group_d.get("organization_id", ""),
            created_by_type=group_d.get("created_by_type", ""),
            created_by=group_d.get("created_by", ""),
            created_at=_parse_dt(group_d.get("created_at")),
            members=members,
            attachments=attachments,
        )

    @property
    def _base_path(self) -> str:
        return f"/organizations/{self._org}/groups/{self.id}"

    @property
    def members(self) -> GroupMembers:
        return GroupMembers(self._client, self._org, self.id)

    @property
    def attachments(self) -> builtins.list[Attachment]:
        return list(self._attachments)

    def update(
        self,
        *,
        name: str | None = None,
        description: str | None = None,
    ) -> Group:
        body: dict[str, str] = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        data = self._client._put_json(self._base_path, json=body)
        return Group.from_dict(self._client, self._org, data)

    def delete(self) -> None:
        self._client._delete(self._base_path)


class Groups:
    """Groups belonging to an organization."""

    def __init__(self, client: Client, org: str) -> None:
        self._client = client
        self._org = org

    def __repr__(self) -> str:
        return f"Groups(org={self._org!r})"

    @property
    def _base_path(self) -> str:
        return f"/organizations/{self._org}/groups"

    def list(
        self,
        *,
        after: str | None = None,
        amount: int | None = None,
        page_size: int | None = None,
    ) -> PaginatedIterator[Group]:
        initial_after = after
        client = self._client
        org = self._org
        base = self._base_path

        def fetch_page(cursor: str | None) -> PageResult[Group]:
            params: dict[str, str | int] = {
                "amount": page_size if page_size is not None else DEFAULT_PAGE_SIZE
            }
            effective_after = cursor if cursor is not None else initial_after
            if effective_after is not None:
                params["after"] = effective_after
            data = client._get_json(base, params=params)
            items = [Group.from_dict(client, org, d) for d in data.get("results", [])]
            pagination = data.get("pagination", {})
            return PageResult(
                items=items,
                has_more=pagination.get("has_more", False),
                next_offset=pagination.get("next_offset"),
                max_per_page=pagination.get("max_per_page"),
            )

        return PaginatedIterator(fetch_page, limit=amount)

    def get(self, group_id: str) -> Group:
        data = self._client._get_json(f"{self._base_path}/{group_id}")
        return Group.from_dict(self._client, self._org, data)

    def create(self, name: str, *, description: str = "") -> Group:
        body: dict[str, str] = {"name": name}
        if description:
            body["description"] = description
        data = self._client._post_json(self._base_path, json=body)
        return Group.from_dict(self._client, self._org, data)

    def delete(self, group_id: str) -> None:
        self._client._delete(f"{self._base_path}/{group_id}")

    def effective(self, principal_type: str, principal_id: str) -> builtins.list[EffectiveGroup]:
        """Get effective group memberships for a principal."""
        data = self._client._get_json(
            f"/organizations/{self._org}/effective-groups",
            params={"principal_type": principal_type, "principal_id": principal_id},
        )
        return [EffectiveGroup.from_dict(d) for d in data.get("results", [])]
