"""Tests for SandboxTrigger, SandboxTriggers, and SandboxTriggerRuns."""

import json

import httpx

from tilde.models import (
    SandboxTrigger,
    SandboxTriggerCondition,
    SandboxTriggerConfig,
    SandboxTriggerRun,
)

BASE_PATH = "/organizations/test-org/repositories/test-repo/sandbox-triggers"

TRIGGER_RESPONSE = {
    "id": "trig-1",
    "repository_id": "repo-1",
    "name": "validate",
    "description": "Run validation",
    "enabled": True,
    "conditions": [
        {"type": "prefix", "prefix": "data/", "diff_type": "added"},
    ],
    "sandbox_config": {
        "image": "python-310",
        "command": ["python", "validate.py"],
        "mountpoint": "/sandbox",
        "path_prefix": "",
        "timeout_seconds": 300,
        "env_vars": {"MODE": "strict"},
    },
    "run_as": None,
    "created_by": "user-1",
    "created_at": "2026-01-15T10:00:00+00:00",
    "updated_at": "2026-01-15T10:01:00+00:00",
}


class TestSandboxTriggerEntity:
    def test_from_dict_parses_nested(self, client):
        trigger = SandboxTrigger.from_dict(client, "test-org", "test-repo", TRIGGER_RESPONSE)
        assert trigger.id == "trig-1"
        assert trigger.name == "validate"
        assert trigger.enabled is True
        assert len(trigger.conditions) == 1
        assert isinstance(trigger.conditions[0], SandboxTriggerCondition)
        assert trigger.conditions[0].prefix == "data/"
        assert isinstance(trigger.sandbox_config, SandboxTriggerConfig)
        assert trigger.sandbox_config.image == "python-310"
        assert trigger.sandbox_config.timeout_seconds == 300
        assert trigger.run_as is None

    def test_from_dict_minimal(self, client):
        trigger = SandboxTrigger.from_dict(client, "test-org", "test-repo", {})
        assert trigger.id == ""
        assert trigger.conditions == []
        assert trigger.sandbox_config is None
        assert trigger.enabled is False

    def test_condition_from_dict(self):
        cond = SandboxTriggerCondition.from_dict(
            {"type": "path_exact", "path": "config.yaml", "diff_type": "modified"}
        )
        assert cond.type == "path_exact"
        assert cond.path == "config.yaml"
        assert cond.diff_type == "modified"


class TestSandboxTriggers:
    def test_create(self, mock_api, repo):
        route = mock_api.post(BASE_PATH).mock(
            return_value=httpx.Response(201, json=TRIGGER_RESPONSE)
        )
        trigger = repo.sandbox_triggers.create(
            name="validate",
            conditions=[{"type": "prefix", "prefix": "data/", "diff_type": "added"}],
            sandbox_config={"image": "python-310", "command": ["python", "validate.py"]},
            description="Run validation",
        )
        assert isinstance(trigger, SandboxTrigger)
        assert trigger.id == "trig-1"
        assert route.called
        payload = json.loads(route.calls[0].request.content)
        assert payload["name"] == "validate"
        assert payload["description"] == "Run validation"

    def test_create_minimal(self, mock_api, repo):
        mock_api.post(BASE_PATH).mock(
            return_value=httpx.Response(
                201, json={"id": "trig-2", "name": "minimal", "enabled": True}
            )
        )
        trigger = repo.sandbox_triggers.create(
            name="minimal",
            conditions=[],
            sandbox_config={"image": "python-310"},
        )
        assert trigger.id == "trig-2"

    def test_list(self, mock_api, repo):
        mock_api.get(BASE_PATH).mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {"id": "trig-1", "name": "validate"},
                        {"id": "trig-2", "name": "lint"},
                    ],
                    "pagination": {"has_more": False, "next_offset": None, "max_per_page": 100},
                },
            )
        )
        triggers = list(repo.sandbox_triggers.list())
        assert len(triggers) == 2
        assert all(isinstance(t, SandboxTrigger) for t in triggers)
        assert triggers[0].id == "trig-1"
        assert triggers[1].id == "trig-2"

    def test_get(self, mock_api, repo):
        mock_api.get(f"{BASE_PATH}/trig-1").mock(
            return_value=httpx.Response(200, json=TRIGGER_RESPONSE)
        )
        trigger = repo.sandbox_triggers.get("trig-1")
        assert isinstance(trigger, SandboxTrigger)
        assert trigger.id == "trig-1"
        assert trigger.name == "validate"


class TestSandboxTriggerMutations:
    def test_update(self, mock_api, repo):
        mock_api.get(f"{BASE_PATH}/trig-1").mock(
            return_value=httpx.Response(200, json=TRIGGER_RESPONSE)
        )
        updated = {**TRIGGER_RESPONSE, "name": "updated-name"}
        route = mock_api.put(f"{BASE_PATH}/trig-1").mock(
            return_value=httpx.Response(200, json=updated)
        )
        trigger = repo.sandbox_triggers.get("trig-1")
        result = trigger.update(name="updated-name")
        assert isinstance(result, SandboxTrigger)
        assert result.name == "updated-name"
        assert route.called

    def test_toggle(self, mock_api, repo):
        mock_api.get(f"{BASE_PATH}/trig-1").mock(
            return_value=httpx.Response(200, json=TRIGGER_RESPONSE)
        )
        toggled = {**TRIGGER_RESPONSE, "enabled": False}
        route = mock_api.patch(f"{BASE_PATH}/trig-1").mock(
            return_value=httpx.Response(200, json=toggled)
        )
        trigger = repo.sandbox_triggers.get("trig-1")
        result = trigger.toggle(enabled=False)
        assert isinstance(result, SandboxTrigger)
        assert result.enabled is False
        payload = json.loads(route.calls[0].request.content)
        assert payload == {"enabled": False}

    def test_delete(self, mock_api, repo):
        mock_api.get(f"{BASE_PATH}/trig-1").mock(
            return_value=httpx.Response(200, json=TRIGGER_RESPONSE)
        )
        route = mock_api.delete(f"{BASE_PATH}/trig-1").mock(return_value=httpx.Response(204))
        trigger = repo.sandbox_triggers.get("trig-1")
        trigger.delete()
        assert route.called


class TestSandboxTriggerRuns:
    def test_list_runs(self, mock_api, repo):
        mock_api.get(f"{BASE_PATH}/trig-1").mock(
            return_value=httpx.Response(200, json=TRIGGER_RESPONSE)
        )
        mock_api.get(f"{BASE_PATH}/trig-1/runs").mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "id": "run-1",
                            "trigger_id": "trig-1",
                            "commit_id": "commit-abc",
                            "status": "completed",
                            "reason": "prefix match",
                            "sandbox_id": "sbx-99",
                            "matched_paths": ["data/file1.csv"],
                        },
                    ],
                    "pagination": {"has_more": False, "next_offset": None, "max_per_page": 100},
                },
            )
        )
        trigger = repo.sandbox_triggers.get("trig-1")
        runs = list(trigger.runs.list())
        assert len(runs) == 1
        assert isinstance(runs[0], SandboxTriggerRun)
        assert runs[0].id == "run-1"
        assert runs[0].status == "completed"
