"""Policy entity and Policies collection."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tilde._isoparse import parse_optional as _parse_dt
from tilde._pagination import DEFAULT_PAGE_SIZE, PageResult, PaginatedIterator
from tilde._value_types import Attachment, EffectivePolicy, ValidationResult

if TYPE_CHECKING:
    import builtins
    from datetime import datetime

    from tilde.client import Client


class Policy:
    """A Rego policy defined within an organization."""

    def __init__(
        self,
        client: Client,
        org: str,
        *,
        id: str = "",
        name: str = "",
        description: str = "",
        policy_text: str = "",
        is_builtin: bool = False,
        organization_id: str = "",
        created_by_type: str = "",
        created_by: str = "",
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        attachment_count: int = 0,
        attachments: builtins.list[Attachment] | None = None,
    ) -> None:
        self._client = client
        self._org = org
        self.id = id
        self.name = name
        self.description = description
        self.policy_text = policy_text
        self.is_builtin = is_builtin
        self.organization_id = organization_id
        self.created_by_type = created_by_type
        self.created_by = created_by
        self.created_at = created_at
        self.updated_at = updated_at
        self.attachment_count = attachment_count
        self._attachments: builtins.list[Attachment] = list(attachments) if attachments else []

    def __repr__(self) -> str:
        return f"Policy({self.name!r})"

    @classmethod
    def from_dict(cls, client: Client, org: str, d: dict[str, Any]) -> Policy:
        policy_d = d.get("policy", d) if "policy" in d else d
        attachments = [Attachment.from_dict(a) for a in d.get("attachments", [])]
        return cls(
            client,
            org,
            id=policy_d.get("id", ""),
            name=policy_d.get("name", ""),
            description=policy_d.get("description", ""),
            policy_text=policy_d.get("policy_text", ""),
            is_builtin=policy_d.get("is_builtin", False),
            organization_id=policy_d.get("organization_id", ""),
            created_by_type=policy_d.get("created_by_type", ""),
            created_by=policy_d.get("created_by", ""),
            created_at=_parse_dt(policy_d.get("created_at")),
            updated_at=_parse_dt(policy_d.get("updated_at")),
            attachment_count=policy_d.get("attachment_count", 0),
            attachments=attachments,
        )

    @property
    def _base_path(self) -> str:
        return f"/organizations/{self._org}/policies/{self.id}"

    @property
    def attachments(self) -> builtins.list[Attachment]:
        return list(self._attachments)

    def update(
        self,
        *,
        name: str | None = None,
        description: str | None = None,
        policy_text: str | None = None,
    ) -> Policy:
        body: dict[str, str] = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if policy_text is not None:
            body["policy_text"] = policy_text
        data = self._client._put_json(self._base_path, json=body)
        return Policy.from_dict(self._client, self._org, data)

    def delete(self) -> None:
        self._client._delete(self._base_path)

    def attach(self, *, principal_type: str, principal_id: str) -> None:
        self._client._post(
            f"{self._base_path}/attachments",
            json={"principal_type": principal_type, "principal_id": principal_id},
        )

    def detach(self, *, principal_type: str, principal_id: str) -> None:
        self._client._delete(
            f"{self._base_path}/attachments",
            params={"principal_type": principal_type, "principal_id": principal_id},
        )


class Policies:
    """Policies belonging to an organization."""

    def __init__(self, client: Client, org: str) -> None:
        self._client = client
        self._org = org

    def __repr__(self) -> str:
        return f"Policies(org={self._org!r})"

    @property
    def _base_path(self) -> str:
        return f"/organizations/{self._org}/policies"

    def list(
        self,
        *,
        after: str | None = None,
        amount: int | None = None,
        page_size: int | None = None,
    ) -> PaginatedIterator[Policy]:
        initial_after = after
        client = self._client
        org = self._org
        base = self._base_path

        def fetch_page(cursor: str | None) -> PageResult[Policy]:
            params: dict[str, str | int] = {
                "amount": page_size if page_size is not None else DEFAULT_PAGE_SIZE
            }
            effective_after = cursor if cursor is not None else initial_after
            if effective_after is not None:
                params["after"] = effective_after
            data = client._get_json(base, params=params)
            items = [Policy.from_dict(client, org, d) for d in data.get("results", [])]
            pagination = data.get("pagination", {})
            return PageResult(
                items=items,
                has_more=pagination.get("has_more", False),
                next_offset=pagination.get("next_offset"),
                max_per_page=pagination.get("max_per_page"),
            )

        return PaginatedIterator(fetch_page, limit=amount)

    def get(self, policy_id: str) -> Policy:
        data = self._client._get_json(f"{self._base_path}/{policy_id}")
        return Policy.from_dict(self._client, self._org, data)

    def create(self, name: str, policy_text: str, *, description: str = "") -> Policy:
        body: dict[str, str] = {"name": name, "policy_text": policy_text}
        if description:
            body["description"] = description
        data = self._client._post_json(self._base_path, json=body)
        return Policy.from_dict(self._client, self._org, data)

    def delete(self, policy_id: str) -> None:
        self._client._delete(f"{self._base_path}/{policy_id}")

    def validate(self, policy_text: str) -> ValidationResult:
        """Validate a policy document without saving."""
        data = self._client._post_json(
            f"{self._base_path}:validate",
            json={"policy_text": policy_text},
        )
        return ValidationResult.from_dict(data)

    def generate(self, prompt: str) -> str:
        """Generate a policy from a natural-language prompt."""
        data = self._client._post_json(
            f"{self._base_path}:generate",
            json={"prompt": prompt},
        )
        return str(data["policy_text"])

    def attachments(self) -> builtins.list[Attachment]:
        """List all policy attachments in this organization."""
        data = self._client._get_json(f"/organizations/{self._org}/attachments")
        return [Attachment.from_dict(d) for d in data.get("results", [])]

    def effective(
        self,
        *,
        principal_type: str | None = None,
        principal_id: str | None = None,
        user_id: str | None = None,
    ) -> builtins.list[EffectivePolicy]:
        """Get effective policies for a principal."""
        params: dict[str, str] = {}
        if user_id is not None:
            params["user_id"] = user_id
        if principal_type is not None:
            params["principal_type"] = principal_type
        if principal_id is not None:
            params["principal_id"] = principal_id
        data = self._client._get_json(
            f"/organizations/{self._org}/effective-policies",
            params=params,
        )
        return [EffectivePolicy.from_dict(d) for d in data.get("results", [])]
