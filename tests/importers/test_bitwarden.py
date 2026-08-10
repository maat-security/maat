"""Tests for importers/bitwarden.py: Bitwarden JSON export parsing."""

import json

import pytest

from importers import bitwarden

LOGIN_TYPE = bitwarden.LOGIN_ITEM_TYPE
NOTE_TYPE = 2  # anything other than LOGIN_ITEM_TYPE


def _export(items, encrypted=False):
    return {"encrypted": encrypted, "items": items}


def _login_item(name, url=None, password=None, has_totp=False, has_passkey=False, item_type=LOGIN_TYPE):
    return {
        "type": item_type,
        "name": name,
        "login": {
            "uris": [{"uri": url}] if url else [],
            "password": password,
            "totp": "JBSWY3DPEHPK3PXP" if has_totp else None,
            "fido2Credentials": [{"credentialId": "abc"}] if has_passkey else [],
        },
        "revisionDate": "2025-01-01T00:00:00Z",
    }


def _write_export(tmp_path, export_dict):
    path = tmp_path / "bitwarden.json"
    path.write_text(json.dumps(export_dict), encoding="utf-8")
    return str(path)


def test_parse_extracts_basic_fields(tmp_path, no_network_hibp):
    path = _write_export(tmp_path, _export([_login_item("Gmail", url="https://gmail.com", password="pw1")]))
    accounts = bitwarden.parse(path)

    assert len(accounts) == 1
    assert accounts[0]["name"] == "Gmail"
    assert accounts[0]["url"] == "https://gmail.com"


def test_parse_detects_totp_and_passkey(tmp_path, no_network_hibp):
    path = _write_export(tmp_path, _export([_login_item("GitHub", password="pw1", has_totp=True, has_passkey=True)]))
    accounts = bitwarden.parse(path)

    assert accounts[0]["has_totp"] is True
    assert accounts[0]["has_passkey"] is True


def test_parse_skips_non_login_items(tmp_path, no_network_hibp):
    path = _write_export(tmp_path, _export([
        _login_item("Login Item", password="pw1"),
        _login_item("Secure Note", item_type=NOTE_TYPE),
    ]))
    accounts = bitwarden.parse(path)

    names = [a["name"] for a in accounts]
    assert "Login Item" in names
    assert "Secure Note" not in names


def test_parse_rejects_encrypted_export_with_clear_error(tmp_path, no_network_hibp):
    path = _write_export(tmp_path, _export([], encrypted=True))

    with pytest.raises(ValueError, match="encrypted"):
        bitwarden.parse(path)


def test_parse_detects_password_reuse(tmp_path, no_network_hibp):
    path = _write_export(tmp_path, _export([
        _login_item("A", password="shared"),
        _login_item("B", password="shared"),
        _login_item("C", password="unique"),
    ]))
    accounts = bitwarden.parse(path)
    by_name = {a["name"]: a for a in accounts}

    assert by_name["A"]["password_reused"] is True
    assert by_name["B"]["password_reused"] is True
    assert by_name["C"]["password_reused"] is False


def test_parse_raises_value_error_for_unreadable_file(tmp_path, no_network_hibp):
    bad_path = tmp_path / "bad.json"
    bad_path.write_text("not valid json {{{")

    with pytest.raises(ValueError):
        bitwarden.parse(str(bad_path))
