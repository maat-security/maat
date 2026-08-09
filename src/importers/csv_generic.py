"""Generic CSV importer — fallback for password managers without a
dedicated adapter.

Phase 0: stub only.
"""


def parse(filepath: str) -> list:
    """Parse a generic CSV export.

    Expected to return a list of dicts, one per account, each with keys
    such as: name, url, has_totp, has_passkey, password_age_days,
    password_reused. No password or secret values are ever extracted —
    only structural metadata used to build the graph.
    """
    return []
