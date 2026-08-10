"""Tests for importers/keepass.py: KeePass XML (2.x) export parsing —
Recycle Bin skip, nested-group recursion, and both TOTP field
conventions (built-in "TOTP Seed" and the legacy "otp" plugin field).
"""

import pytest

from importers import keepass

XML_TEMPLATE = """<?xml version="1.0" encoding="utf-8" standalone="yes"?>
<KeePassFile>
  <Meta><Generator>KeePass</Generator></Meta>
  <Root>
    <Group>
      <Name>Root</Name>
      {entries}
    </Group>
  </Root>
</KeePassFile>
"""


def _entry(title, url=None, password=None, totp_seed=None, otp=None, last_modified="2025-01-01T00:00:00Z"):
    fields = [f"<String><Key>Title</Key><Value>{title}</Value></String>"]
    if url is not None:
        fields.append(f"<String><Key>URL</Key><Value>{url}</Value></String>")
    if password is not None:
        fields.append(f"<String><Key>Password</Key><Value>{password}</Value></String>")
    if totp_seed is not None:
        fields.append(f"<String><Key>TOTP Seed</Key><Value>{totp_seed}</Value></String>")
    if otp is not None:
        fields.append(f"<String><Key>otp</Key><Value>{otp}</Value></String>")
    times = f"<Times><LastModificationTime>{last_modified}</LastModificationTime></Times>" if last_modified else ""
    return f"<Entry>{''.join(fields)}{times}</Entry>"


def _write_xml(tmp_path, entries_xml, extra_groups_xml=""):
    path = tmp_path / "export.xml"
    path.write_text(XML_TEMPLATE.format(entries=entries_xml + extra_groups_xml), encoding="utf-8")
    return str(path)


def test_parse_extracts_basic_fields(tmp_path, no_network_hibp):
    path = _write_xml(tmp_path, _entry("Gmail", url="https://gmail.com", password="pw1"))
    accounts = keepass.parse(path)

    assert len(accounts) == 1
    assert accounts[0]["name"] == "Gmail"
    assert accounts[0]["url"] == "https://gmail.com"
    assert accounts[0]["has_passkey"] is False, "KeePass has no native passkey concept"


def test_parse_detects_totp_via_built_in_seed_field(tmp_path, no_network_hibp):
    path = _write_xml(tmp_path, _entry("GitHub", password="pw1", totp_seed="JBSWY3DPEHPK3PXP"))
    accounts = keepass.parse(path)

    assert accounts[0]["has_totp"] is True


def test_parse_detects_totp_via_legacy_otp_plugin_field(tmp_path, no_network_hibp):
    path = _write_xml(tmp_path, _entry("Legacy", password="pw1", otp="otpauth://totp/x?secret=ABC"))
    accounts = keepass.parse(path)

    assert accounts[0]["has_totp"] is True


def test_parse_no_totp_fields_is_false(tmp_path, no_network_hibp):
    path = _write_xml(tmp_path, _entry("Plain", password="pw1"))
    accounts = keepass.parse(path)

    assert accounts[0]["has_totp"] is False


def test_parse_recurses_into_nested_groups(tmp_path, no_network_hibp):
    nested = """
    <Group>
      <Name>Work</Name>
      <Group>
        <Name>Deeply Nested</Name>
        {entry}
      </Group>
    </Group>
    """.format(entry=_entry("Nested Account", password="pw1"))
    path = _write_xml(tmp_path, "", extra_groups_xml=nested)

    accounts = keepass.parse(path)
    assert [a["name"] for a in accounts] == ["Nested Account"]


def test_parse_skips_recycle_bin_entries(tmp_path, no_network_hibp):
    recycle_bin = """
    <Group>
      <Name>Recycle Bin</Name>
      {entry}
    </Group>
    """.format(entry=_entry("Deleted Account", password="pw1"))
    path = _write_xml(
        tmp_path,
        _entry("Active Account", password="pw2"),
        extra_groups_xml=recycle_bin,
    )

    accounts = keepass.parse(path)
    names = [a["name"] for a in accounts]
    assert "Active Account" in names
    assert "Deleted Account" not in names


def test_parse_recycle_bin_match_is_case_insensitive(tmp_path, no_network_hibp):
    recycle_bin = """
    <Group>
      <Name>RECYCLE BIN</Name>
      {entry}
    </Group>
    """.format(entry=_entry("Deleted Account", password="pw1"))
    path = _write_xml(tmp_path, "", extra_groups_xml=recycle_bin)

    accounts = keepass.parse(path)
    assert accounts == []


def test_parse_detects_password_reuse(tmp_path, no_network_hibp):
    path = _write_xml(
        tmp_path,
        _entry("A", password="shared") + _entry("B", password="shared") + _entry("C", password="unique"),
    )
    accounts = keepass.parse(path)
    by_name = {a["name"]: a for a in accounts}

    assert by_name["A"]["password_reused"] is True
    assert by_name["C"]["password_reused"] is False


def test_parse_missing_title_falls_back_to_untitled(tmp_path, no_network_hibp):
    entry_without_title = "<Entry><String><Key>Password</Key><Value>pw1</Value></String></Entry>"
    path = _write_xml(tmp_path, entry_without_title)

    accounts = keepass.parse(path)
    assert accounts[0]["name"] == "Untitled"


def test_parse_raises_value_error_for_non_keepass_xml(tmp_path, no_network_hibp):
    path = tmp_path / "not_keepass.xml"
    path.write_text("<SomeOtherFormat><Foo>bar</Foo></SomeOtherFormat>", encoding="utf-8")

    with pytest.raises(ValueError):
        keepass.parse(str(path))


def test_parse_raises_value_error_for_unparseable_xml(tmp_path, no_network_hibp):
    path = tmp_path / "garbage.xml"
    path.write_text("this is not xml at all <<<", encoding="utf-8")

    with pytest.raises(ValueError):
        keepass.parse(str(path))


def test_parse_runs_breach_check(tmp_path, monkeypatch):
    import hibp

    def fake_check(passwords):
        return [p == "known-breached" for p in passwords]

    monkeypatch.setattr(hibp, "check_passwords_breached", fake_check)

    path = _write_xml(tmp_path, _entry("Gmail", password="known-breached"))
    accounts = keepass.parse(path)

    assert accounts[0]["breached"] is True
