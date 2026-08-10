"""Bitwarden (JSON export) importer.

Only structural metadata is extracted from an unencrypted Bitwarden
JSON export: name, url, TOTP/passkey presence, password age, and
password reuse (detected by hashing in memory, never persisted).
"""

import json

from ._shared import compute_breach_flags, compute_reuse_flags, days_since, new_account

LOGIN_ITEM_TYPE = 1


def parse(filepath: str) -> list:
    """Parse a Bitwarden JSON export file.

    Returns a list of account dicts (see _shared.new_account). Raises
    ValueError if filepath isn't a readable Bitwarden export, or if the
    export is password-protected/encrypted — Maat only reads
    unencrypted exports and never asks for Bitwarden credentials.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            export = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Not a readable Bitwarden JSON export: {filepath!r}") from exc

    if export.get("encrypted"):
        raise ValueError(
            "This Bitwarden export is encrypted. Re-export from Bitwarden "
            "with the password-protected / encrypted option turned off."
        )

    accounts = []
    passwords = []

    for item in export.get("items") or []:
        if item.get("type") != LOGIN_ITEM_TYPE:
            continue

        login = item.get("login") or {}
        uris = login.get("uris") or []
        url = uris[0].get("uri") if uris else None

        has_passkey = bool(login.get("fido2Credentials") or login.get("passkeys"))
        has_totp = bool(login.get("totp"))

        age_source = login.get("passwordRevisionDate") or item.get("revisionDate")

        accounts.append(
            new_account(
                name=item.get("name") or "Untitled",
                url=url,
                has_totp=has_totp,
                has_passkey=has_passkey,
                password_age_days=days_since(age_source),
            )
        )
        passwords.append(login.get("password"))

    reuse_flags = compute_reuse_flags(passwords)
    for account, reused in zip(accounts, reuse_flags):
        account["password_reused"] = reused

    breached_flags, failed_flags = compute_breach_flags(passwords)
    for account, breached, failed in zip(accounts, breached_flags, failed_flags):
        account["breached"] = breached
        account["breach_check_failed"] = failed

    return accounts
