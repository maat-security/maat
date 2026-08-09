"""Generic CSV importer — fallback for password managers without a
dedicated adapter.

Column names vary a lot between exporters, so this matches header
names case-insensitively against a handful of common aliases rather
than requiring one exact schema. Only structural metadata is
extracted: name, url, TOTP presence, password age, and password reuse
(detected by hashing in memory, never persisted). Passkeys aren't
represented in plain CSV exports, so has_passkey is always False here.
"""

import csv

from ._shared import compute_reuse_flags, days_since, new_account

NAME_COLUMNS = ("name", "title", "account", "item name")
URL_COLUMNS = ("url", "website", "login_uri", "site")
PASSWORD_COLUMNS = ("password", "login_password")
TOTP_COLUMNS = ("totp", "otp_secret", "otpauth", "one_time_password", "2fa_secret")
MODIFIED_COLUMNS = ("password_last_modified", "last_modified", "modified", "changed")


def _find_column(fieldnames, candidates):
    lowered = {name.lower(): name for name in fieldnames}
    for candidate in candidates:
        if candidate in lowered:
            return lowered[candidate]
    return None


def parse(filepath: str) -> list:
    """Parse a generic CSV export.

    Returns a list of account dicts (see _shared.new_account). Raises
    ValueError if filepath isn't readable, or has no recognizable name
    column.
    """
    try:
        with open(filepath, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            fieldnames = reader.fieldnames or []
    except OSError as exc:
        raise ValueError(f"Not a readable CSV file: {filepath!r}") from exc

    name_col = _find_column(fieldnames, NAME_COLUMNS)
    if name_col is None:
        raise ValueError(
            f"Couldn't find a name/title column in {filepath!r} — "
            f"saw columns: {fieldnames}"
        )

    url_col = _find_column(fieldnames, URL_COLUMNS)
    password_col = _find_column(fieldnames, PASSWORD_COLUMNS)
    totp_col = _find_column(fieldnames, TOTP_COLUMNS)
    modified_col = _find_column(fieldnames, MODIFIED_COLUMNS)

    accounts = []
    passwords = []

    for row in rows:
        name = (row.get(name_col) or "").strip() or "Untitled"
        url = (row.get(url_col) or "").strip() or None if url_col else None
        has_totp = bool(totp_col and (row.get(totp_col) or "").strip())
        age_source = row.get(modified_col) if modified_col else None

        accounts.append(
            new_account(
                name=name,
                url=url,
                has_totp=has_totp,
                has_passkey=False,
                password_age_days=days_since(age_source),
            )
        )
        passwords.append(row.get(password_col) if password_col else None)

    reuse_flags = compute_reuse_flags(passwords)
    for account, reused in zip(accounts, reuse_flags):
        account["password_reused"] = reused

    return accounts
