"""Have I Been Pwned integration — Pwned Passwords k-anonymity check.

This is the one outbound network call the local-first core of the app
makes on its own (see README's "Design Principle: Local-First, No
Exceptions"). Only the first 5 hex characters of a password's SHA-1
hash — the "prefix" — are ever sent to HIBP's range endpoint; the full
hash and the plaintext password never leave this device. HIBP's own
documentation calls this k-anonymity, and the README already commits
to it by name.

check_password_breached() does the matching locally against whatever
candidate suffixes the range endpoint returns for that prefix. A
network failure raises HibpError rather than returning False — "the
API was unreachable" and "this password is not in any known breach"
are different claims, and this module never collapses the first into
the second (honest degradation, per design principle 7 — see
graph.py/metrics.py for the same principle elsewhere in this codebase).
"""

import hashlib

import requests

RANGE_API_URL = "https://api.pwnedpasswords.com/range/{prefix}"
REQUEST_TIMEOUT_SECONDS = 5
# Identifies the app to HIBP's API per its terms of use — required by
# the range endpoint, no API key needed for it.
USER_AGENT = "Maat-Security-Posture-Tool"


class HibpError(Exception):
    """Raised when the HIBP range endpoint can't be reached or returns
    something unparseable. Callers must treat this as "unknown", never
    silently treat it as "not breached"."""


def check_password_breached(password: str) -> bool:
    """Return True if this password's hash appears in the Pwned
    Passwords dataset, False if the range lookup completed and found
    no match. Raises HibpError if the lookup itself failed.

    An empty/missing password is never "breached" — returns False
    without making a network call, same convention as
    importers/_shared.py's compute_reuse_flags().
    """
    if not password:
        return False

    digest = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
    prefix, suffix = digest[:5], digest[5:]

    try:
        response = requests.get(
            RANGE_API_URL.format(prefix=prefix),
            headers={"User-Agent": USER_AGENT, "Add-Padding": "true"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HibpError(f"Could not reach Have I Been Pwned: {exc}") from exc

    for line in response.text.splitlines():
        candidate_suffix, _, _ = line.partition(":")
        if candidate_suffix.strip().upper() == suffix:
            return True
    return False


def check_passwords_breached(passwords: list) -> list:
    """Given a list of password strings (or None/empty) in item order,
    return a same-length list of booleans from check_password_breached().

    One request per non-empty password, in order — fine at the scale
    of one person's account inventory (tens to low hundreds, per
    graph.py's own scale note), not tuned for larger batches. Raises
    HibpError on the first failed lookup; callers decide how to
    degrade a partially-checked batch (see
    importers/_shared.py.compute_breach_flags()).
    """
    return [check_password_breached(password) for password in passwords]
