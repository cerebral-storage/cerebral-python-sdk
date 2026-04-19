"""Tilde Python SDK.

Quick start::

    import tilde

    # One-shot shorthand for a specific repo
    repo = tilde.repository('my-org/repo1')

    # Full chain for every other entity
    org = tilde.organizations.get('my-org')
    for repo in org.repositories.list():
        print(repo.name)

The top-level namespace is intentionally small: just :class:`Client`,
:func:`configure`, :func:`repository`, and :data:`organizations`.  Entity
classes live in :mod:`tilde.models`; exception classes live in
:mod:`tilde.exceptions`.
"""

from __future__ import annotations

import sys as _sys
import types as _types
from typing import TYPE_CHECKING as _TYPE_CHECKING

from tilde._version import __version__
from tilde.client import Client

if _TYPE_CHECKING:
    from tilde._credentials import SandboxCredentialsProvider
    from tilde.resources.organizations import Organizations
    from tilde.resources.repositories import Repository

__all__ = [
    "Client",
    "__version__",
    "configure",
    "organizations",
    "repository",
]

_default_client: Client | None = None


def configure(
    *,
    api_key: str | None = None,
    endpoint_url: str | None = None,
    default_sandbox_image: str | None = None,
    credentials_provider: SandboxCredentialsProvider | None = None,
) -> None:
    """(Re)configure the default client used by :data:`organizations`
    and :func:`repository`.
    """
    global _default_client
    if _default_client is not None:
        _default_client.close()
    _default_client = Client(
        api_key=api_key,
        endpoint_url=endpoint_url,
        default_sandbox_image=default_sandbox_image,
        credentials_provider=credentials_provider,
    )


def _get_default_client() -> Client:
    global _default_client
    if _default_client is None:
        _default_client = Client()
    return _default_client


def repository(repo_path: str) -> Repository:
    """Get a :class:`~tilde.models.Repository` via the default client.

    ``tilde.repository('org/repo')`` is the only shorthand in the SDK; every
    other entity is reached through :data:`organizations`.
    """
    return _get_default_client().repository(repo_path)


class _TildeModule(_types.ModuleType):
    """Module subclass that exposes ``organizations`` as a live attribute.

    Using a ModuleType subclass (rather than PEP 562 ``__getattr__``) means
    ``organizations`` appears in :func:`dir` and in static introspection,
    matching the documented public surface.
    """

    @property
    def organizations(self) -> Organizations:
        """The :class:`~tilde.models.Organizations` collection on the default client."""
        return _get_default_client().organizations

    def __dir__(self) -> list[str]:
        base = list(super().__dir__())
        if "organizations" not in base:
            base.append("organizations")
        return sorted(base)


_sys.modules[__name__].__class__ = _TildeModule
