"""Tests for hibp.py's k-anonymity matching logic.

Mocks requests.get — this suite must never make a real network call,
per TODO.md's own note on this module. What's under test here is the
local suffix-matching and error-handling logic, not the live HIBP API.
"""

import pytest

import hibp


class FakeResponse:
    def __init__(self, text="", status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise hibp.requests.HTTPError(f"{self.status_code} error")


def test_empty_or_missing_password_never_hits_network(monkeypatch):
    calls = []
    monkeypatch.setattr(hibp.requests, "get", lambda *a, **k: calls.append(1) or FakeResponse())

    assert hibp.check_password_breached("") is False
    assert hibp.check_password_breached(None) is False
    assert calls == [], "an empty/missing password must never trigger a network call"


def test_matching_suffix_returns_true(monkeypatch):
    # SHA-1("password").upper() = 5BAA61E4C9B93F3F0682250B6CF8331B7EE68FD8
    # prefix "5BAA6", suffix "1E4C9B93F3F0682250B6CF8331B7EE68FD8"
    fake_body = "1E4C9B93F3F0682250B6CF8331B7EE68FD8:3730471\nDEADBEEF00000000000000000000000000:1\n"
    monkeypatch.setattr(hibp.requests, "get", lambda *a, **k: FakeResponse(fake_body))

    assert hibp.check_password_breached("password") is True


def test_no_matching_suffix_returns_false(monkeypatch):
    fake_body = "DEADBEEF00000000000000000000000000:1\n"
    monkeypatch.setattr(hibp.requests, "get", lambda *a, **k: FakeResponse(fake_body))

    assert hibp.check_password_breached("password") is False


def test_suffix_match_is_case_insensitive(monkeypatch):
    fake_body = "1e4c9b93f3f0682250b6cf8331b7ee68fd8:1\n"  # lowercase
    monkeypatch.setattr(hibp.requests, "get", lambda *a, **k: FakeResponse(fake_body))

    assert hibp.check_password_breached("password") is True


def test_network_failure_raises_hibp_error_not_false(monkeypatch):
    def raise_connection_error(*args, **kwargs):
        raise hibp.requests.ConnectionError("no route to host")

    monkeypatch.setattr(hibp.requests, "get", raise_connection_error)

    with pytest.raises(hibp.HibpError):
        hibp.check_password_breached("password")


def test_non_200_response_raises_hibp_error(monkeypatch):
    monkeypatch.setattr(hibp.requests, "get", lambda *a, **k: FakeResponse(status_code=500))

    with pytest.raises(hibp.HibpError):
        hibp.check_password_breached("password")


def test_only_five_char_prefix_is_sent(monkeypatch):
    """The full hash and the plaintext password must never be sent —
    only the 5-character prefix, per the k-anonymity design this
    module documents."""
    captured_urls = []

    def fake_get(url, **kwargs):
        captured_urls.append(url)
        return FakeResponse()

    monkeypatch.setattr(hibp.requests, "get", fake_get)
    hibp.check_password_breached("password")

    assert len(captured_urls) == 1
    assert captured_urls[0].endswith("/range/5BAA6")
    assert "1E4C9B93F3F0682250B6CF8331B7EE68FD8" not in captured_urls[0], (
        "the full hash suffix must never be sent over the network"
    )
    # Note: the hostname itself contains "password" (pwnedpasswords.com)
    # — the real thing to rule out is the *plaintext* appearing as a
    # distinct query value, which the prefix-only URL already can't do.


def test_check_passwords_breached_preserves_order(monkeypatch):
    fake_body = "1E4C9B93F3F0682250B6CF8331B7EE68FD8:1\n"  # matches "password" only

    def fake_get(url, **kwargs):
        return FakeResponse(fake_body if url.endswith("/5BAA6") else "")

    monkeypatch.setattr(hibp.requests, "get", fake_get)

    result = hibp.check_passwords_breached(["password", None, "something-else-entirely", ""])
    assert result == [True, False, False, False]


def test_check_passwords_breached_raises_on_first_failure(monkeypatch):
    def raise_error(*args, **kwargs):
        raise hibp.requests.ConnectionError("offline")

    monkeypatch.setattr(hibp.requests, "get", raise_error)

    with pytest.raises(hibp.HibpError):
        hibp.check_passwords_breached(["password", "other"])
