"""Tests for importers/csv_generic.py: generic CSV export parsing with
case-insensitive column-name matching."""

import pytest

from importers import csv_generic


def _write_csv(tmp_path, header, rows):
    path = tmp_path / "export.csv"
    lines = [",".join(header)]
    lines.extend(",".join(row) for row in rows)
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


def test_parse_extracts_basic_fields(tmp_path, no_network_hibp):
    path = _write_csv(
        tmp_path,
        ["name", "url", "password", "totp", "last_modified"],
        [["Gmail", "https://gmail.com", "pw1", "", ""]],
    )
    accounts = csv_generic.parse(path)

    assert len(accounts) == 1
    assert accounts[0]["name"] == "Gmail"
    assert accounts[0]["url"] == "https://gmail.com"
    assert accounts[0]["has_totp"] is False
    assert accounts[0]["has_passkey"] is False, "CSV never represents passkeys"


def test_parse_column_matching_is_case_insensitive_with_aliases(tmp_path, no_network_hibp):
    path = _write_csv(
        tmp_path,
        ["Title", "Website", "Login_Password", "OTP_Secret", "Changed"],
        [["GitHub", "https://github.com", "pw1", "seed", ""]],
    )
    accounts = csv_generic.parse(path)

    assert accounts[0]["name"] == "GitHub"
    assert accounts[0]["url"] == "https://github.com"
    assert accounts[0]["has_totp"] is True


def test_parse_missing_name_falls_back_to_untitled(tmp_path, no_network_hibp):
    path = _write_csv(tmp_path, ["name", "password"], [["", "pw1"]])
    accounts = csv_generic.parse(path)

    assert accounts[0]["name"] == "Untitled"


def test_parse_raises_value_error_when_no_name_column(tmp_path, no_network_hibp):
    path = _write_csv(tmp_path, ["foo", "bar"], [["1", "2"]])

    with pytest.raises(ValueError, match="name/title"):
        csv_generic.parse(path)


def test_parse_detects_password_reuse(tmp_path, no_network_hibp):
    path = _write_csv(
        tmp_path,
        ["name", "password"],
        [["A", "shared"], ["B", "shared"], ["C", "unique"]],
    )
    accounts = csv_generic.parse(path)
    by_name = {a["name"]: a for a in accounts}

    assert by_name["A"]["password_reused"] is True
    assert by_name["C"]["password_reused"] is False


def test_parse_raises_value_error_for_unreadable_file(tmp_path, no_network_hibp):
    with pytest.raises(ValueError):
        csv_generic.parse(str(tmp_path / "does_not_exist.csv"))
