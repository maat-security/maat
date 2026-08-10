"""1Password (1PUX export) importer.

A .1pux file is a ZIP archive containing export.data — one JSON blob
structured as accounts -> vaults -> items. Only structural metadata is
extracted: name, url, TOTP/passkey presence, password age, and
password reuse (detected by hashing in memory, never persisted).
Password and TOTP values are read only transiently, to detect presence
and reuse — never included in parse()'s return value.
"""

import json
import zipfile

from ._shared import compute_breach_flags, compute_reuse_flags, days_since, new_account


def parse(filepath: str) -> list:
    """Parse a 1Password 1PUX export file.

    Returns a list of account dicts (see _shared.new_account). Raises
    ValueError if filepath isn't a readable 1PUX archive.
    """
    try:
        with zipfile.ZipFile(filepath) as archive:
            with archive.open("export.data") as data_file:
                export = json.load(data_file)
    except (zipfile.BadZipFile, KeyError, json.JSONDecodeError, OSError) as exc:
        raise ValueError(f"Not a readable 1Password 1PUX export: {filepath!r}") from exc

    items = []
    for account in export.get("accounts", []) or []:
        for vault in account.get("vaults", []) or []:
            items.extend(vault.get("items", []) or [])

    accounts = []
    passwords = []

    for item in items:
        if item.get("state") == "TRASHED" or item.get("trashed"):
            continue

        overview = item.get("overview") or {}
        details = item.get("details") or {}

        name = overview.get("title") or "Untitled"
        url = overview.get("url")
        if not url:
            urls = overview.get("urls") or []
            if urls:
                url = urls[0].get("url")

        has_passkey = bool(details.get("passkeys"))
        has_totp = _has_totp_field(details)

        password_history = details.get("passwordHistory") or []
        last_changed = max(
            (entry.get("time") for entry in password_history if entry.get("time")),
            default=None,
        )
        age_source = last_changed or item.get("updatedAt") or item.get("createdAt")

        accounts.append(
            new_account(
                name=name,
                url=url,
                has_totp=has_totp,
                has_passkey=has_passkey,
                password_age_days=days_since(age_source),
            )
        )
        passwords.append(_extract_password(details))

    reuse_flags = compute_reuse_flags(passwords)
    for account, reused in zip(accounts, reuse_flags):
        account["password_reused"] = reused

    breached_flags, failed_flags = compute_breach_flags(passwords)
    for account, breached, failed in zip(accounts, breached_flags, failed_flags):
        account["breached"] = breached
        account["breach_check_failed"] = failed

    return accounts


def _has_totp_field(details: dict) -> bool:
    for field in details.get("loginFields") or []:
        if str(field.get("designation", "")).lower() == "totp":
            return True
    for section in details.get("sections") or []:
        for field in section.get("fields") or []:
            field_type = str(field.get("fieldType", "")).upper()
            field_name = str(field.get("name", "")).upper()
            if "TOTP" in field_type or "TOTP" in field_name:
                return True
    return False


def _extract_password(details: dict):
    """Read the current password value transiently, for reuse detection
    only. Never included in parse()'s return value."""
    for field in details.get("loginFields") or []:
        if str(field.get("designation", "")).lower() == "password":
            return field.get("value")
    return None
