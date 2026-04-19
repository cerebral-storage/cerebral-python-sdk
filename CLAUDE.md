# Tilde Python SDK

Python SDK for the Tilde data versioning API (`https://tilde.run`).

## Project Layout

```
src/tilde/              # Package source
  __init__.py           # Public exports + module-level API (configure, repository, organizations)
  client.py             # HTTP client wrapping httpx (lazy init, context manager)
  models.py             # Dataclass models (slots=True) with from_dict() classmethods
  exceptions.py         # Exception hierarchy: TildeError → APIError → status-specific errors
  _config.py            # Config resolution (env vars: TILDE_API_KEY, TILDE_ENDPOINT_URL)
  _version.py           # Single source of truth for version string
  _pagination.py        # Offset-based PaginatedIterator (generic, TypeVar-based)
  _object_reader.py     # Streaming file-like reader with optional caching
  _output_stream.py     # OutputStream for sandbox command stdout/stderr
  resources/            # Resource classes for each API domain
    repositories.py     # Repository resource
    sessions.py         # Session resource (transactional put/get/delete + commit/rollback)
    objects.py          # ReadOnlyObjectCollection + SessionObjectCollection
    commits.py          # Commit timeline and diffs
    organizations.py    # Org CRUD + membership
    groups.py           # Group management
    policies.py         # Rego policy validation and attachment
    connectors.py       # S3 and other connectors
    imports.py          # Import job queuing and status
tests/                  # pytest + respx (HTTP mocking)
  conftest.py           # Fixtures: mock_api, client, repo
  test_*.py             # One test file per module
  typecheck/            # mypy strict-mode type assertions

docs/                   # MkDocs (material theme) documentation
openapi.yaml            # OpenAPI spec for the Tilde API
```

## Naming Conventions

The public API follows a strict, uniform shape. Resource classes are **singular
nouns** that name real entities (`Organization`, `Repository`, `Agent`,
`Role`, `Sandbox`, `SandboxTrigger`, `Group`, `Policy`, `Connector`, `Secret`,
`APIKey`, `Commit`, `Member`, `ImportJob`). Never introduce `FooData`,
`FooResource`, `FooInfo`, `FooSummary`, or `FooDetail` variants — the entity
class itself carries both data and behaviour.

Collections are **plural nouns** (`organizations`, `repositories`, `members`,
`agents`, `roles`, `api_keys`, `groups`, `policies`, `connectors`, `sandboxes`,
`sandbox_triggers`, `imports`, `secrets`, `commits`). They live as attributes
or properties on the parent entity (or the `Client`).

Every collection exposes the same three verbs where applicable:

- `.list()` → **lazy iterator** (`PaginatedIterator[T]`) of the singular
  entity. Even non-paginated endpoints wrap their one-shot response in the
  same iterator contract so callers can always iterate; callers that want a
  materialised list do ``list(col.list())``. For example,
  ``tilde.organizations.list()`` yields the organizations the authenticated
  principal belongs to.
- `.get(key)` → the singular entity (fetches / resolves by id or name).
- `.create(...)` → the newly-created singular entity. If the server's POST
  doesn't return the created entity, the collection follows up with a GET so
  the caller always receives a populated entity instance.

There is exactly **one** shorthand exception: `tilde.repository('org/repo')`
returns a `Repository` directly. The shorthand does not exist for any other
entity — callers use the full
`tilde.organizations.get('org').repositories.get('repo')` chain (or the
equivalent on a `Client`).

Entity classes are plain regular classes (not `@dataclass`), constructed
internally with a client reference plus their fields. They expose data via
attributes/properties and actions via methods. Sub-collections are exposed as
plural-noun properties (e.g. `organization.repositories`,
`agent.api_keys`). Value-only helper types (`Entry`, `ListingEntry`,
`ValidationResult`, `PutObjectResult`, etc.) remain `@dataclass(slots=True)`
because they are pure data with no behaviour.

## Key Architecture Details

- **HTTP layer**: `Client` wraps `httpx.Client` with lazy initialization and proper cleanup via context manager. Methods: `_get`, `_post`, `_put`, `_delete`, `_head`, `_stream`, plus `_*_json` convenience variants.
- **Resources**: Each API domain has a resource class. The `Client` creates resources; resources hold a back-reference to the client for HTTP calls.
- **Sessions**: Transactional model — `repo.session()` returns a context manager that auto-rolls back on exception. Supports `commit(message)` and `rollback()`.
- **Pagination**: Generic `PaginatedIterator[T]` using offset-based `after` cursor, default page size 100.
- **Models**: Pure value-only helper types (`Entry`, `ListingEntry`, `ValidationResult`, `PutObjectResult`, `CopyObjectResult`, `ObjectMetadata`, `CommitResult`, `SourceMetadata`) are frozen `@dataclass(slots=True)` with `from_dict()` classmethods. They must use the `@_compact_repr` decorator (defined in `models.py`) so that `repr()` omits default-valued fields. ISO 8601 datetime parsing via `_parse_dt()`.
- **Entity classes** (see *Naming Conventions*): regular classes living in `resources/`. They hold a client reference, carry their data via attributes, and define `__repr__` that shows key identifying info (e.g. `Repository('org/name')`, `Session(id='...')`). They expose sub-collections as plural-noun properties.
- **OutputStream** (`_output_stream.py`): Stream wrapper for sandbox command stdout/stderr. `RunResult.stdout` and `RunResult.stderr` are `OutputStream` instances. Methods: `read()` → bytes, `text(encoding)` → str, `iter_bytes(chunk_size)`, `iter_text(chunk_size)`, `iter_lines()`. Supports lazy loading from HTTP endpoints (data fetched and cached on first access) or in-memory construction from bytes.
- **Errors**: `TildeError` base → `APIError` (HTTP 400+) → status-specific subclasses (401, 403, 404, 409, 410, 412, 423, 5xx). Also `ConfigurationError`, `TransportError`, `SerializationError`.
## Commands

### Install dependencies
```
uv sync --all-extras
```

### Run tests
```
uv run pytest
```

### Run tests with coverage
```
uv run pytest --cov=tilde --cov-report=term-missing
```

### Lint
```
uv run ruff check src/ tests/
```

### Format check
```
uv run ruff format --check src/ tests/
```

### Auto-format
```
uv run ruff format src/ tests/
```

### Type check
```
uv run mypy src/tilde/
uv run mypy tests/typecheck/ --strict
```

### Build
```
uv build
```

Output goes to `dist/` (wheel + sdist).

### Publish
```
uv publish
```

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs on push/PR to `main`:
- Tests against Python 3.11, 3.12, 3.13
- Lint → format check → mypy (src) → mypy (typecheck) → pytest with coverage

## API Coverage Notes

- The OAuth2 endpoints in `openapi.yaml` (`/auth/oauth/*`) are browser-based flows and do **not** need to be implemented in the SDK.

## Verification

After modifying Python code, always run the full check suite before considering the task done:

```
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/tilde/
uv run pytest
```

If ruff format reports issues, run `uv run ruff format src/ tests/` to auto-fix.

## Secret Scanning

Pre-commit and CI use **detect-secrets** (Yelp, Apache 2.0) to catch leaked credentials. Known false positives (dummy test keys, env var names, doc placeholders) are tracked in `.secrets.baseline` with `"is_secret": false` — **not** with inline `# pragma: allowlist secret` comments, especially not in user-facing files like README.md.

If detect-secrets flags a new false positive:
1. Regenerate the baseline: `detect-secrets scan --exclude-files '\.mypy_cache' --exclude-files 'uv\.lock' --exclude-files '\.venv' --exclude-files 'dist/' --exclude-files '\.git/' > .secrets.baseline`
2. Mark false positives: `detect-secrets audit .secrets.baseline` (interactive — press `n` for false positives)
3. Commit the updated `.secrets.baseline`

## Code Style

- **Ruff** with line-length 100, target Python 3.10
- Rule sets: E, F, I, UP, B, SIM, TCH, RUF
- **mypy** strict mode enabled
- **Top-level `tilde` surface is intentionally tiny**: ``Client``,
  ``configure``, ``repository``, ``organizations`` (a live property on the
  module, powered by a ``types.ModuleType`` subclass), and ``__version__``.
  Every noun — entity classes and plural collections — lives in
  :mod:`tilde.models`. Every error lives in :mod:`tilde.exceptions`. Nothing
  else is re-exported at the top level.
