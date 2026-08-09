"""Posture scoring and consequence-language translation.

Scoring weights per the product spec: Concentration 40%, Factor
resistance 25%, Recovery hygiene 25%, Exposure and freshness 10%.

The UI must never display a raw metric name or number to the user —
only the output of translate_to_consequences().

Phase 0: signatures only.
"""

import networkx as nx


def compute_score(graph: nx.DiGraph) -> dict:
    """Compute the 0-100 posture score with its component breakdown.

    Returns a dict with the overall score and the weighted contribution
    of each component (concentration, factor_resistance,
    recovery_hygiene, exposure_and_freshness). The raw number is never
    shown to the user without this breakdown.
    """
    pass


def get_prioritized_gaps(graph: nx.DiGraph) -> list:
    """Return remediation actions ordered by blast-radius reduction."""
    pass


def translate_to_consequences(metric_name: str, value, affected_nodes: list) -> str:
    """Translate an internal metric into consequence language.

    The UI must never display metric_name or value directly to the
    user — only the string this function returns, e.g. "If you lose
    access to X, these N accounts are exposed: [list]".
    """
    pass
