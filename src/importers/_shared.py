"""Shared helpers for password manager importers.

Every importer returns the same account dict shape:

  {
    "name": str,
    "url": str | None,
    "has_totp": bool,
    "has_passkey": bool,
    "password_age_days": int | None,   # None means unknown, not zero
    "password_reused": bool,
  }

Passwords are only ever held in memory long enough to hash them for
reuse detection within a single parse() call — the plaintext, and even
the hash, are discarded before parse() returns. Nothing here persists
a secret value; only the derived structural facts above do.
"""

import datetime
import hashlib


def new_account(
    name,
    url=None,
    has_totp=False,
    has_passkey=False,
    password_age_days=None,
    password_reused=False,
):
    """Build an account dict with the shape every importer must return."""
    return {
        "name": name,
        "url": url,
        "has_totp": has_totp,
        "has_passkey": has_passkey,
        "password_age_days": password_age_days,
        "password_reused": password_reused,
    }


def days_since(when):
    """Return whole days between `when` and now, or None if unknown.

    Accepts an ISO 8601 string (with or without a trailing "Z") or a
    Unix timestamp (int/float). Returns None — not zero — when `when`
    is missing or unparseable, per honest degradation.
    """
    if when is None:
        return None
    try:
        if isinstance(when, (int, float)):
            moment = datetime.datetime.fromtimestamp(when, tz=datetime.timezone.utc)
        else:
            text = str(when)
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            moment = datetime.datetime.fromisoformat(text)
            if moment.tzinfo is None:
                moment = moment.replace(tzinfo=datetime.timezone.utc)
    except (ValueError, TypeError, OSError):
        return None

    now = datetime.datetime.now(datetime.timezone.utc)
    return max(0, (now - moment).days)


def compute_reuse_flags(passwords):
    """Given a list of password strings (or None) in item order, return
    a same-length list of booleans: True where that password's hash
    occurs more than once in the list.

    A missing password (None or empty) is never "reused" — it maps to
    False unconditionally. Hashes exist only for the duration of this
    call; the function returns booleans, nothing else.
    """
    hashes = [
        hashlib.sha256(p.encode("utf-8")).hexdigest() if p else None
        for p in passwords
    ]
    counts = {}
    for h in hashes:
        if h is not None:
            counts[h] = counts.get(h, 0) + 1
    return [h is not None and counts[h] > 1 for h in hashes]
