"""Shared pytest fixtures for the test suite.

reset_graph_state is autouse — graph.py's module-level singleton (see
graph.py's own docstring on why it's a singleton) would otherwise leak
nodes/edges between tests depending on run order. Everything else is
opt-in per test, via an explicit fixture parameter, so a test that
genuinely exercises hibp.py's own network layer (tests/test_hibp.py)
isn't silently overridden by a suite-wide patch meant for everyone
else.
"""

import pytest

import graph
import hibp
import store


@pytest.fixture(autouse=True)
def reset_graph_state():
    graph.reset_graph()
    yield
    graph.reset_graph()


@pytest.fixture
def isolated_store(tmp_path, monkeypatch):
    """Point store.py at a throwaway directory instead of the real
    per-OS app data path, and guarantee the store is closed after the
    test even if it fails midway — store.py's connection/key state is
    a module-level singleton (Phase 0 supports one open vault per
    process, per its own docstring), so leaving it open would leak
    into whichever test runs next.
    """
    monkeypatch.setattr(store, "get_app_data_dir", lambda: tmp_path)
    yield tmp_path
    store.store_close()


@pytest.fixture
def no_network_hibp(monkeypatch):
    """Patch hibp.check_passwords_breached so importer tests never
    make a real network call — everything comes back "not breached"
    unless a test overrides this again itself (monkeypatch stacks
    cleanly within one test). Tests of hibp.py's own matching logic
    mock requests.get directly instead — see tests/test_hibp.py.
    """
    def fake_check(passwords):
        return [False] * len(passwords)

    monkeypatch.setattr(hibp, "check_passwords_breached", fake_check)
    return fake_check
