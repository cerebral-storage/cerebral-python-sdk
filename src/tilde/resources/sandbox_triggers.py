"""SandboxTrigger entity and SandboxTriggers collection."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tilde._isoparse import parse_optional as _parse_dt
from tilde._pagination import DEFAULT_PAGE_SIZE, PageResult, PaginatedIterator
from tilde._value_types import SandboxTriggerCondition, SandboxTriggerConfig

if TYPE_CHECKING:
    import builtins
    from datetime import datetime

    from tilde.client import Client


class SandboxTriggerRun:
    """A single execution of a sandbox trigger."""

    def __init__(
        self,
        *,
        id: str = "",
        repository_id: str = "",
        trigger_id: str = "",
        commit_id: str = "",
        status: str = "",
        reason: str = "",
        sandbox_id: str | None = None,
        matched_paths: list[str] | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        self.id = id
        self.repository_id = repository_id
        self.trigger_id = trigger_id
        self.commit_id = commit_id
        self.status = status
        self.reason = reason
        self.sandbox_id = sandbox_id
        self.matched_paths: list[str] = list(matched_paths) if matched_paths else []
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self) -> str:
        return f"SandboxTriggerRun(id={self.id!r}, status={self.status!r})"

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SandboxTriggerRun:
        return cls(
            id=d.get("id", ""),
            repository_id=d.get("repository_id", ""),
            trigger_id=d.get("trigger_id", ""),
            commit_id=d.get("commit_id", ""),
            status=d.get("status", ""),
            reason=d.get("reason", ""),
            sandbox_id=d.get("sandbox_id"),
            matched_paths=d.get("matched_paths", []),
            created_at=_parse_dt(d.get("created_at")),
            updated_at=_parse_dt(d.get("updated_at")),
        )


class SandboxTriggerRuns:
    """Runs for a sandbox trigger."""

    def __init__(self, client: Client, base_path: str) -> None:
        self._client = client
        self._base_path = base_path

    def __repr__(self) -> str:
        return f"SandboxTriggerRuns(path={self._base_path!r})"

    def list(
        self,
        *,
        after: str | None = None,
        amount: int | None = None,
        page_size: int | None = None,
    ) -> PaginatedIterator[SandboxTriggerRun]:
        initial_after = after
        client = self._client
        base = self._base_path

        def fetch_page(cursor: str | None) -> PageResult[SandboxTriggerRun]:
            params: dict[str, str | int] = {
                "amount": page_size if page_size is not None else DEFAULT_PAGE_SIZE
            }
            effective_after = cursor if cursor is not None else initial_after
            if effective_after is not None:
                params["after"] = effective_after
            data = client._get_json(base, params=params)
            items = [SandboxTriggerRun.from_dict(d) for d in data.get("results", [])]
            pagination = data.get("pagination", {})
            return PageResult(
                items=items,
                has_more=pagination.get("has_more", False),
                next_offset=pagination.get("next_offset"),
                max_per_page=pagination.get("max_per_page"),
            )

        return PaginatedIterator(fetch_page, limit=amount)


class SandboxTrigger:
    """A sandbox trigger definition."""

    def __init__(
        self,
        client: Client,
        org: str,
        repo: str,
        *,
        id: str = "",
        name: str = "",
        description: str = "",
        enabled: bool = False,
        conditions: list[SandboxTriggerCondition] | None = None,
        sandbox_config: SandboxTriggerConfig | None = None,
        run_as: dict[str, str] | None = None,
        repository_id: str = "",
        created_by: str = "",
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        self._client = client
        self._org = org
        self._repo = repo
        self.id = id
        self.name = name
        self.description = description
        self.enabled = enabled
        self.conditions: list[SandboxTriggerCondition] = list(conditions) if conditions else []
        self.sandbox_config = sandbox_config
        self.run_as = run_as
        self.repository_id = repository_id
        self.created_by = created_by
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self) -> str:
        return f"SandboxTrigger(id={self.id!r}, name={self.name!r})"

    @property
    def _base_path(self) -> str:
        return f"/organizations/{self._org}/repositories/{self._repo}/sandbox-triggers/{self.id}"

    @classmethod
    def from_dict(cls, client: Client, org: str, repo: str, d: dict[str, Any]) -> SandboxTrigger:
        sc = d.get("sandbox_config")
        return cls(
            client,
            org,
            repo,
            id=d.get("id", ""),
            name=d.get("name", ""),
            description=d.get("description", ""),
            enabled=d.get("enabled", False),
            conditions=[SandboxTriggerCondition.from_dict(c) for c in d.get("conditions", [])],
            sandbox_config=SandboxTriggerConfig.from_dict(sc) if sc else None,
            run_as=d.get("run_as"),
            repository_id=d.get("repository_id", ""),
            created_by=d.get("created_by", ""),
            created_at=_parse_dt(d.get("created_at")),
            updated_at=_parse_dt(d.get("updated_at")),
        )

    @property
    def runs(self) -> SandboxTriggerRuns:
        return SandboxTriggerRuns(self._client, f"{self._base_path}/runs")

    def refresh(self) -> SandboxTrigger:
        """Re-fetch trigger metadata from the server."""
        data = self._client._get_json(self._base_path)
        fresh = SandboxTrigger.from_dict(self._client, self._org, self._repo, data)
        self.__dict__.update(fresh.__dict__)
        return self

    def update(
        self,
        *,
        name: str | None = None,
        description: str | None = None,
        conditions: list[dict[str, Any]] | None = None,
        sandbox_config: dict[str, Any] | None = None,
        run_as: dict[str, str] | None = None,
    ) -> SandboxTrigger:
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if conditions is not None:
            body["conditions"] = conditions
        if sandbox_config is not None:
            body["sandbox_config"] = sandbox_config
        if run_as is not None:
            body["run_as"] = run_as
        data = self._client._put_json(self._base_path, json=body)
        return SandboxTrigger.from_dict(self._client, self._org, self._repo, data)

    def toggle(self, *, enabled: bool) -> SandboxTrigger:
        data = self._client._patch_json(self._base_path, json={"enabled": enabled})
        return SandboxTrigger.from_dict(self._client, self._org, self._repo, data)

    def delete(self) -> None:
        self._client._delete(self._base_path)


class SandboxTriggers:
    """Sandbox triggers in a repository."""

    def __init__(self, client: Client, org: str, repo: str) -> None:
        self._client = client
        self._org = org
        self._repo = repo

    def __repr__(self) -> str:
        return f"SandboxTriggers({self._org}/{self._repo})"

    @property
    def _base_path(self) -> str:
        return f"/organizations/{self._org}/repositories/{self._repo}/sandbox-triggers"

    def list(
        self,
        *,
        after: str | None = None,
        amount: int | None = None,
        page_size: int | None = None,
    ) -> PaginatedIterator[SandboxTrigger]:
        initial_after = after
        client = self._client
        org = self._org
        repo = self._repo
        base = self._base_path

        def fetch_page(cursor: str | None) -> PageResult[SandboxTrigger]:
            params: dict[str, str | int] = {
                "amount": page_size if page_size is not None else DEFAULT_PAGE_SIZE
            }
            effective_after = cursor if cursor is not None else initial_after
            if effective_after is not None:
                params["after"] = effective_after
            data = client._get_json(base, params=params)
            items = [
                SandboxTrigger.from_dict(client, org, repo, d) for d in data.get("results", [])
            ]
            pagination = data.get("pagination", {})
            return PageResult(
                items=items,
                has_more=pagination.get("has_more", False),
                next_offset=pagination.get("next_offset"),
                max_per_page=pagination.get("max_per_page"),
            )

        return PaginatedIterator(fetch_page, limit=amount)

    def get(self, trigger_id: str) -> SandboxTrigger:
        data = self._client._get_json(f"{self._base_path}/{trigger_id}")
        return SandboxTrigger.from_dict(self._client, self._org, self._repo, data)

    def create(
        self,
        *,
        name: str,
        conditions: builtins.list[dict[str, Any]],
        sandbox_config: dict[str, Any],
        description: str = "",
        run_as: dict[str, str] | None = None,
    ) -> SandboxTrigger:
        body: dict[str, Any] = {
            "name": name,
            "conditions": conditions,
            "sandbox_config": sandbox_config,
        }
        if description:
            body["description"] = description
        if run_as is not None:
            body["run_as"] = run_as
        data = self._client._post_json(self._base_path, json=body)
        return SandboxTrigger.from_dict(self._client, self._org, self._repo, data)

    def delete(self, trigger_id: str) -> None:
        self._client._delete(f"{self._base_path}/{trigger_id}")
