"""Data types and entity classes — public home for every SDK noun.

This module is a pure re-export aggregator with no runtime dependencies on
code it re-exports.  The dependency graph it sits on top of is a strict DAG:

* :mod:`tilde._value_types` defines the pure dataclass value types and has
  no other in-package dependencies.
* :mod:`tilde.resources.*` modules import their value types from
  ``tilde._value_types`` (not from this module), plus pagination and ISO
  helpers.
* :mod:`tilde.models` (this file) imports from both layers, re-exports
  everything, and is imported only by user code and by :mod:`tilde.__init__`.

Because resources don't import from this module, there is no cycle to break.

Typical imports::

    from tilde.models import Organization, Repository, Commit, ListingEntry
"""

from __future__ import annotations

from tilde._credentials import SandboxCredentials, SandboxCredentialsProvider
from tilde._output_stream import OutputStream
from tilde._value_types import (
    Attachment,
    CommitResult,
    CopyObjectResult,
    EffectiveGroup,
    EffectivePolicy,
    Entry,
    EntryRecord,
    GroupMember,
    ListingEntry,
    ObjectMetadata,
    PutObjectResult,
    RunResult,
    SandboxTriggerCondition,
    SandboxTriggerConfig,
    SourceMetadata,
    ValidationError,
    ValidationResult,
)
from tilde.resources.agents import Agent, Agents, APIKey, APIKeys
from tilde.resources.commits import Commit, Commits
from tilde.resources.connectors import Connector, Connectors, RepositoryConnectors
from tilde.resources.groups import Group, GroupMembers, Groups
from tilde.resources.imports import ImportJob, Imports
from tilde.resources.objects import ReadOnlyObjects, SessionObjects
from tilde.resources.organizations import Member, Members, Organization, Organizations
from tilde.resources.policies import Policies, Policy
from tilde.resources.repositories import Repositories, Repository
from tilde.resources.roles import Role, Roles
from tilde.resources.sandbox_triggers import (
    SandboxTrigger,
    SandboxTriggerRun,
    SandboxTriggerRuns,
    SandboxTriggers,
)
from tilde.resources.sandboxes import LogStream, Sandbox, Sandboxes, SandboxStatus
from tilde.resources.secrets import Secret, Secrets
from tilde.resources.sessions import Session
from tilde.resources.shell import Shell

__all__ = [
    "APIKey",
    "APIKeys",
    "Agent",
    "Agents",
    "Attachment",
    "Commit",
    "CommitResult",
    "Commits",
    "Connector",
    "Connectors",
    "CopyObjectResult",
    "EffectiveGroup",
    "EffectivePolicy",
    "Entry",
    "EntryRecord",
    "Group",
    "GroupMember",
    "GroupMembers",
    "Groups",
    "ImportJob",
    "Imports",
    "ListingEntry",
    "LogStream",
    "Member",
    "Members",
    "ObjectMetadata",
    "Organization",
    "Organizations",
    "OutputStream",
    "Policies",
    "Policy",
    "PutObjectResult",
    "ReadOnlyObjects",
    "Repositories",
    "Repository",
    "RepositoryConnectors",
    "Role",
    "Roles",
    "RunResult",
    "Sandbox",
    "SandboxCredentials",
    "SandboxCredentialsProvider",
    "SandboxStatus",
    "SandboxTrigger",
    "SandboxTriggerCondition",
    "SandboxTriggerConfig",
    "SandboxTriggerRun",
    "SandboxTriggerRuns",
    "SandboxTriggers",
    "Sandboxes",
    "Secret",
    "Secrets",
    "Session",
    "SessionObjects",
    "Shell",
    "SourceMetadata",
    "ValidationError",
    "ValidationResult",
]
