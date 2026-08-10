"""Tests for importers/_shared.py: the common account dict shape,
days_since()'s date parsing, password-reuse detection, and the
Have I Been Pwned breach-check helper's honest degradation on
failure."""

import pytest

import hibp
from importers._shared import compute_breach_flags, compute_reuse_flags, days_since, new_account


def test_new_account_default_shape():
    account = new_account("Gmail")
    assert account == {
        "name": "Gmail",
        "url": None,
        "has_totp": False,
        "has_passkey": False,
        "password_age_days": None,
        "password_reused": False,
        "breached": False,
        "breach_check_failed": False,
    }


def test_days_since_none_is_none_not_zero():
    assert days_since(None) is None


def test_days_since_iso_string_with_z_suffix():
    result = days_since("2020-01-01T00:00:00Z")
    assert isinstance(result, int)
    assert result > 1000  # comfortably in the past


def test_days_since_unix_timestamp():
    result = days_since(0)  # 1970-01-01
    assert isinstance(result, int)
    assert result > 1000


def test_days_since_unparseable_is_none_not_zero():
    assert days_since("not a date") is None
    assert days_since("") is None


def test_compute_reuse_flags_detects_duplicates_only():
    flags = compute_reuse_flags(["same", "same", "different", None, ""])
    assert flags == [True, True, False, False, False]


def test_compute_reuse_flags_all_unique_is_all_false():
    assert compute_reuse_flags(["a", "b", "c"]) == [False, False, False]


def test_compute_breach_flags_normal_path(no_network_hibp, monkeypatch):
    def fake_check(passwords):
        return [p == "breached-one" for p in passwords]

    monkeypatch.setattr(hibp, "check_passwords_breached", fake_check)

    breached, failed = compute_breach_flags(["breached-one", "clean-one", None])
    assert breached == [True, False, False]
    assert failed == [False, False, False]


def test_compute_breach_flags_no_passwords_skips_network_entirely(monkeypatch):
    calls = []
    monkeypatch.setattr(hibp, "check_passwords_breached", lambda pw: calls.append(pw) or [])

    breached, failed = compute_breach_flags([None, "", None])
    assert breached == [False, False, False]
    assert failed == [False, False, False]
    assert calls == [], "a batch with no real passwords must never call the network layer"


def test_compute_breach_flags_network_failure_degrades_to_unconfirmed_not_clean(monkeypatch):
    def raise_error(passwords):
        raise hibp.HibpError("offline")

    monkeypatch.setattr(hibp, "check_passwords_breached", raise_error)

    breached, failed = compute_breach_flags(["some-password", None, "another-password"])
    assert breached == [False, False, False], "a failed check must never claim 'breached'"
    assert failed == [True, False, True], "only items that actually had a password to check should be marked failed"
