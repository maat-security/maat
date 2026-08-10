"""Tests for importers/onepassword.py: 1Password 1PUX export parsing."""

import json
import zipfile

import pytest

from importers import onepassword


def _make_1pux(tmp_path, items):
    """Build a minimal .1pux (zip containing export.data) fixture."""
    export_data = {
        "accounts": [{
            "vaults": [{
                "items": items,
            }],
        }],
    }
    path = tmp_path / "export.1pux"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("export.data", json.dumps(export_data))
    return str(path)


def _item(title, url=None, password=None, has_totp=False, has_passkey=False, trashed=False):
    login_fields = []
    if password is not None:
        login_fields.append({"designation": "password", "value": password})
    if has_totp:
        login_fields.append({"designation": "totp", "value": "JBSWY3DPEHPK3PXP"})

    return {
        "state": "TRASHED" if trashed else "ACTIVE",
        "overview": {"title": title, "url": url},
        "details": {
            "loginFields": login_fields,
            "passkeys": [{"credentialId": "abc"}] if has_passkey else [],
        },
        "updatedAt": "2025-01-01T00:00:00Z",
    }


def test_parse_extracts_basic_fields(tmp_path, no_network_hibp):
    path = _make_1pux(tmp_path, [_item("Gmail", url="https://gmail.com", password="pw1")])
    accounts = onepassword.parse(path)

    assert len(accounts) == 1
    assert accounts[0]["name"] == "Gmail"
    assert accounts[0]["url"] == "https://gmail.com"
    assert accounts[0]["has_totp"] is False
    assert accounts[0]["has_passkey"] is False


def test_parse_detects_totp_and_passkey(tmp_path, no_network_hibp):
    path = _make_1pux(tmp_path, [_item("GitHub", password="pw1", has_totp=True, has_passkey=True)])
    accounts = onepassword.parse(path)

    assert accounts[0]["has_totp"] is True
    assert accounts[0]["has_passkey"] is True


def test_parse_skips_trashed_items(tmp_path, no_network_hibp):
    path = _make_1pux(tmp_path, [
        _item("Active Account", password="pw1"),
        _item("Deleted Account", password="pw2", trashed=True),
    ])
    accounts = onepassword.parse(path)

    names = [a["name"] for a in accounts]
    assert "Active Account" in names
    assert "Deleted Account" not in names


def test_parse_detects_password_reuse(tmp_path, no_network_hibp):
    path = _make_1pux(tmp_path, [
        _item("Account A", password="shared-password"),
        _item("Account B", password="shared-password"),
        _item("Account C", password="unique-password"),
    ])
    accounts = onepassword.parse(path)
    by_name = {a["name"]: a for a in accounts}

    assert by_name["Account A"]["password_reused"] is True
    assert by_name["Account B"]["password_reused"] is True
    assert by_name["Account C"]["password_reused"] is False


def test_parse_never_returns_password_value(tmp_path, no_network_hibp):
    path = _make_1pux(tmp_path, [_item("Gmail", password="super-secret-value")])
    accounts = onepassword.parse(path)

    assert "password" not in accounts[0]
    assert "super-secret-value" not in str(accounts[0])


def test_parse_runs_breach_check(tmp_path, monkeypatch):
    def fake_check(passwords):
        return [p == "known-breached" for p in passwords]

    import hibp
    monkeypatch.setattr(hibp, "check_passwords_breached", fake_check)

    path = _make_1pux(tmp_path, [_item("Gmail", password="known-breached")])
    accounts = onepassword.parse(path)

    assert accounts[0]["breached"] is True
    assert accounts[0]["breach_check_failed"] is False


def test_parse_raises_value_error_for_non_1pux_file(tmp_path, no_network_hibp):
    bad_path = tmp_path / "not_a_1pux.1pux"
    bad_path.write_text("not a zip file at all")

    with pytest.raises(ValueError):
        onepassword.parse(str(bad_path))
