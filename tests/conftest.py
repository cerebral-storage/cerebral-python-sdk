import pytest
import respx

from tilde import _config
from tilde.client import Client

BASE_URL = "https://tilde.run/api/v1"


@pytest.fixture(autouse=True)
def _isolate_tilde_config_file(tmp_path, monkeypatch):
    """Isolate ~/.tilde/config.yaml for every test.

    Without this, tests that exercise default config resolution would pick up
    a real config file on the developer's machine and behave unpredictably.
    """
    monkeypatch.setattr(_config, "_default_config_path", lambda: tmp_path / "config.yaml")


@pytest.fixture
def mock_api():
    """respx mock router scoped to the Tilde API base URL."""
    with respx.mock(base_url=BASE_URL, assert_all_called=False) as rsps:
        yield rsps


@pytest.fixture
def client():
    """Client configured with a test API key."""
    c = Client(api_key="test-key")
    yield c
    c.close()


@pytest.fixture
def repo(client):
    """Repository resource for 'test-org/test-repo'."""
    return client.repository("test-org/test-repo")
