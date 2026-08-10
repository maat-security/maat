"""KeePass XML export importer.

A "KeePass XML (2.x)" export (File → Export → KeePass XML (2.x)) is a
single XML file: Root -> nested Group elements -> Entry elements, each
holding String fields (Key/Value pairs) for Title, UserName, Password,
URL, Notes, and — since KeePass 2.54's built-in TOTP support — a "TOTP
Seed" field, or the older KeeTrayTOTP/TrayTOTP plugin convention of a
plain "otp" field. Only structural metadata is extracted: name, url,
TOTP presence, password age, and password reuse/breach status
(detected transiently in memory, never persisted) — same contract as
every other importer in this package.

KeePass has no native passkey concept, so has_passkey is always False
here, same as csv_generic.py's treatment of passkeys.

Entries under a "Recycle Bin" group (KeePass's own trash) are skipped,
same as onepassword.py skips TRASHED items.
"""

import xml.etree.ElementTree as ET

from ._shared import compute_breach_flags, compute_reuse_flags, days_since, new_account

RECYCLE_BIN_GROUP_NAME = "recycle bin"
TOTP_FIELD_KEYS = ("totp seed", "otp")


def parse(filepath: str) -> list:
    """Parse a KeePass XML (2.x) export file.

    Returns a list of account dicts (see _shared.new_account). Raises
    ValueError if filepath isn't a readable KeePass XML export.
    """
    try:
        tree = ET.parse(filepath)
    except (ET.ParseError, OSError) as exc:
        raise ValueError(f"Not a readable KeePass XML export: {filepath!r}") from exc

    root_element = tree.getroot()
    if root_element.tag != "KeePassFile":
        raise ValueError(f"Not a readable KeePass XML export: {filepath!r}")

    entries = []
    for root_group in root_element.findall("./Root/Group"):
        entries.extend(_iter_entries(root_group))

    accounts = []
    passwords = []

    for entry in entries:
        fields = _string_fields(entry)
        name = fields.get("title") or "Untitled"
        url = fields.get("url") or None
        has_totp = any(fields.get(key) for key in TOTP_FIELD_KEYS)
        last_modified = entry.findtext("./Times/LastModificationTime")

        accounts.append(
            new_account(
                name=name,
                url=url,
                has_totp=has_totp,
                has_passkey=False,
                password_age_days=days_since(last_modified),
            )
        )
        passwords.append(fields.get("password"))

    reuse_flags = compute_reuse_flags(passwords)
    for account, reused in zip(accounts, reuse_flags):
        account["password_reused"] = reused

    breached_flags, failed_flags = compute_breach_flags(passwords)
    for account, breached, failed in zip(accounts, breached_flags, failed_flags):
        account["breached"] = breached
        account["breach_check_failed"] = failed

    return accounts


def _iter_entries(group_element):
    """Yield every Entry element under group_element, recursing into
    nested Group elements — but never into a "Recycle Bin" group."""
    yield from group_element.findall("Entry")
    for subgroup in group_element.findall("Group"):
        name = (subgroup.findtext("Name") or "").strip().lower()
        if name == RECYCLE_BIN_GROUP_NAME:
            continue
        yield from _iter_entries(subgroup)


def _string_fields(entry_element) -> dict:
    """Return {key.lower(): value} for every String field on this entry."""
    fields = {}
    for string_element in entry_element.findall("String"):
        key = string_element.findtext("Key")
        value_element = string_element.find("Value")
        value = value_element.text if value_element is not None else None
        if key:
            fields[key.strip().lower()] = value
    return fields
