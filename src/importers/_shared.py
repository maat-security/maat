"""Shared helpers for password manager importers.

Every importer returns the same account dict shape:

  {
    "name": str,
    "url": str | None,
    "has_totp": bool,
    "has_passkey": bool,
    "password_age_days": int | None,   # None means unknown, not zero
    "password_reused": bool,
    "breached": bool,                  # confirmed via Have I Been Pwned
    "breach_check_failed": bool,       # True if that check couldn't run
  }

Passwords are only ever held in memory long enough to hash them for
reuse detection and the Have I Been Pwned lookup within a single
parse() call — the plaintext, and even the hashes, are discarded
before parse() returns. Nothing here persists a secret value; only the
derived structural facts above do.
"""

import datetime
import hashlib

import hibp


def new_account(
    name,
    url=None,
    has_totp=False,
    has_passkey=False,
    password_age_days=None,
    password_reused=False,
    breached=False,
    breach_check_failed=False,
):
    """Build an account dict with the shape every importer must return."""
    return {
        "name": name,
        "url": url,
        "has_totp": has_totp,
        "has_passkey": has_passkey,
        "password_age_days": password_age_days,
        "password_reused": password_reused,
        "breached": breached,
        "breach_check_failed": breach_check_failed,
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


def compute_breach_flags(passwords):
    """Given a list of password strings (or None) in item order, return
    (breached_flags, failed_flags) — two same-length lists of booleans.

    breached_flags[i] is True only when Have I Been Pwned's k-anonymity
    range check actually confirmed that password's hash is breached.
    failed_flags[i] is True when that item had a password but the
    check couldn't complete (e.g. no network) — a missing password is
    never "failed", same as it's never "breached": there was nothing
    to check.

    A failure partway through degrades the *whole batch* to
    unconfirmed (breached=False, failed=True for every item that had a
    password) rather than raising and losing an otherwise-successful
    import — see hibp.py for why "couldn't check" and "confirmed clean"
    are kept as distinct claims here rather than collapsed into one.
    """
    had_password = [bool(p) for p in passwords]
    if not any(had_password):
        return [False] * len(passwords), [False] * len(passwords)

    try:
        breached = hibp.check_passwords_breached(passwords)
        return breached, [False] * len(passwords)
    except hibp.HibpError:
        return [False] * len(passwords), had_password
