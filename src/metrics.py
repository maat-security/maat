"""Posture scoring and consequence-language translation.

Scoring weights per the product spec:
  Concentration           40%  - how much falls if the single most
                                  critical node is compromised or lost
  Factor resistance       25%  - phishing-resistant coverage on
                                  critical identities
  Recovery hygiene        25%  - auth/recovery asymmetry and cycles
  Exposure and freshness  10%  - known breaches, stale or unknown data

The UI must never display a raw metric name or number to the user —
only the output of translate_to_consequences(). Every function here
takes an explicit graph argument rather than reaching into graph.py's
module-level singleton, so this module works on any nx.DiGraph
(including a hand-built one in a test) independent of app state.

translate_to_consequences() returns English text only for now — it is
not yet wired into i18n.py's translation layer, since the strings it
produces are built from live node ids and counts, not the static
strings main.py's UI uses as t() lookup keys. That wiring is future
work, not a Phase 1 gap.
"""

import networkx as nx

import graph as graph_module

WEIGHT_CONCENTRATION = 0.40
WEIGHT_FACTOR_RESISTANCE = 0.25
WEIGHT_RECOVERY_HYGIENE = 0.25
WEIGHT_EXPOSURE_FRESHNESS = 0.10

# Identities below this criticality are still tracked (to catch edges
# into critical nodes) but excluded from most scoring components, per
# the product's modeling threshold decision (PRD 14.4).
CRITICALITY_THRESHOLD = 3

STALE_AFTER_DAYS = 90


# --------------------------------------------------------------------------
# Graph queries — local to this module so it never depends on graph.py's
# singleton state, only on whatever graph is passed in.
# --------------------------------------------------------------------------

def _identities(graph: nx.DiGraph) -> list:
    return [n for n, d in graph.nodes(data=True) if d.get("type") == "Identity"]


def _critical_identities(graph: nx.DiGraph) -> list:
    return [
        n for n in _identities(graph)
        if graph.nodes[n].get("criticality", graph_module.DEFAULT_CRITICALITY)
        >= CRITICALITY_THRESHOLD
    ]


def _authenticating_factors(graph: nx.DiGraph, identity: str) -> list:
    """Factor nodes with an AUTHENTICATES edge into identity."""
    return [
        u for u, _, d in graph.in_edges(identity, data=True)
        if d.get("type") == "AUTHENTICATES" and graph.nodes[u].get("type") == "Factor"
    ]


def _recovery_nodes(graph: nx.DiGraph, identity: str) -> list:
    """Nodes with a RECOVERS edge into identity, of any node type."""
    return [u for u, _, d in graph.in_edges(identity, data=True) if d.get("type") == "RECOVERS"]


def _strongest_resistance(graph: nx.DiGraph, factor_nodes: list) -> int:
    ranks = [
        graph_module.factor_resistance_rank(graph.nodes[f].get("kind", ""))
        for f in factor_nodes
    ]
    return max(ranks) if ranks else 0


def _is_phishing_resistant(graph: nx.DiGraph, factor_node: str) -> bool:
    return graph.nodes[factor_node].get("kind") in graph_module.PHISHING_RESISTANT_KINDS


def _cut_vertices(graph: nx.DiGraph) -> list:
    return sorted(nx.articulation_points(graph.to_undirected()))


def _cycles(graph: nx.DiGraph) -> list:
    return [list(c) for c in nx.simple_cycles(graph) if len(c) > 1]


def _orphaned_identities(graph: nx.DiGraph) -> list:
    """Identities with exactly one authenticating factor and no recovery
    path — lose that factor's device and access is gone for good."""
    orphaned = []
    for identity in _identities(graph):
        if len(_authenticating_factors(graph, identity)) == 1 and not _recovery_nodes(graph, identity):
            orphaned.append(identity)
    return orphaned


def _is_stale(last_verified) -> bool:
    """A node with no last_verified, or one older than STALE_AFTER_DAYS,
    is treated as stale — honest degradation, per design principle 7."""
    if not last_verified:
        return True
    import datetime

    try:
        verified_at = datetime.datetime.fromisoformat(last_verified)
    except (TypeError, ValueError):
        return True

    now = datetime.datetime.now(verified_at.tzinfo)
    return (now - verified_at).days > STALE_AFTER_DAYS


# --------------------------------------------------------------------------
# Score components
# --------------------------------------------------------------------------

def worst_case_exposure(graph: nx.DiGraph) -> int:
    """Return how many identities the single worst node in the graph
    would expose — the same figure the concentration component and
    get_prioritized_gaps() are built on. Used by remediation.py to show
    a before/after simulation without duplicating this computation.
    """
    _, detail = _compute_concentration(graph)
    return len(detail["exposed_identities"])


def _compute_concentration(graph: nx.DiGraph) -> tuple:
    """(score_0_100, detail) — how much falls if the single worst node
    in the whole graph (any node type) is compromised or lost."""
    identities = _identities(graph)
    if not identities:
        return 100.0, {"worst_node": None, "exposed_identities": []}

    worst_node = None
    worst_exposed = []
    for node in graph.nodes:
        exposed = [d for d in nx.descendants(graph, node) if d in identities]
        if len(exposed) > len(worst_exposed):
            worst_exposed = exposed
            worst_node = node

    fraction = len(worst_exposed) / len(identities)
    score = (1 - fraction) * 100
    return score, {"worst_node": worst_node, "exposed_identities": worst_exposed}


def _compute_factor_resistance(graph: nx.DiGraph) -> tuple:
    """(score_0_100, detail) — phishing-resistant coverage on critical
    identities. No critical identities yet is full marks, not a penalty
    — there is nothing to protect yet, which is not the same as failing
    to protect something."""
    critical = _critical_identities(graph)
    if not critical:
        return 100.0, {"vulnerable_identities": []}

    vulnerable = [
        identity for identity in critical
        if not any(
            _is_phishing_resistant(graph, f) for f in _authenticating_factors(graph, identity)
        )
    ]
    fraction_resistant = 1 - (len(vulnerable) / len(critical))
    return fraction_resistant * 100, {"vulnerable_identities": vulnerable}


def _compute_recovery_hygiene(graph: nx.DiGraph) -> tuple:
    """(score_0_100, detail) — critical identities whose recovery path is
    weaker than their primary factor, plus mutual-recovery cycles."""
    critical = _critical_identities(graph)

    asymmetric = []
    for identity in critical:
        auth_rank = _strongest_resistance(graph, _authenticating_factors(graph, identity))
        recovery_nodes = _recovery_nodes(graph, identity)
        recovery_factor_nodes = [r for r in recovery_nodes if graph.nodes[r].get("type") == "Factor"]
        recovery_rank = _strongest_resistance(graph, recovery_factor_nodes)
        # A recovery path through a non-Factor node (e.g. a bare SMS
        # RecoveryChannel with no modeled factor) is weak by default.
        if recovery_nodes and auth_rank > recovery_rank:
            asymmetric.append(identity)

    cycles = _cycles(graph)

    base = (1 - len(asymmetric) / len(critical)) * 100 if critical else 100.0
    cycle_penalty = min(50.0, 10.0 * len(cycles))
    score = max(0.0, base - cycle_penalty)
    return score, {"asymmetric_identities": asymmetric, "cycles": cycles}


def _compute_exposure_freshness(graph: nx.DiGraph) -> tuple:
    """(score_0_100, detail) — known breaches and stale/unknown data.
    Breaches are weighted more heavily than staleness: a breach is a
    confirmed exposure, staleness is only reduced confidence."""
    identities = _identities(graph)
    if not identities:
        return 100.0, {"breached_identities": [], "stale_identities": []}

    breached = [n for n in identities if graph.nodes[n].get("breached")]
    stale = [n for n in identities if _is_stale(graph.nodes[n].get("last_verified"))]

    breach_fraction = len(breached) / len(identities)
    stale_fraction = len(stale) / len(identities)

    score = max(0.0, 100.0 - (breach_fraction * 70) - (stale_fraction * 30))
    return score, {"breached_identities": breached, "stale_identities": stale}


def compute_score(graph: nx.DiGraph) -> dict:
    """Compute the 0-100 posture score with its component breakdown.

    Returns a dict with the overall score and the weighted contribution
    of each component (concentration, factor_resistance,
    recovery_hygiene, exposure_and_freshness). The raw number is never
    shown to the user without this breakdown.
    """
    concentration_score, concentration_detail = _compute_concentration(graph)
    factor_resistance_score, factor_resistance_detail = _compute_factor_resistance(graph)
    recovery_hygiene_score, recovery_hygiene_detail = _compute_recovery_hygiene(graph)
    exposure_freshness_score, exposure_freshness_detail = _compute_exposure_freshness(graph)

    overall = (
        concentration_score * WEIGHT_CONCENTRATION
        + factor_resistance_score * WEIGHT_FACTOR_RESISTANCE
        + recovery_hygiene_score * WEIGHT_RECOVERY_HYGIENE
        + exposure_freshness_score * WEIGHT_EXPOSURE_FRESHNESS
    )

    return {
        "overall": round(overall, 1),
        "components": {
            "concentration": {
                "score": round(concentration_score, 1),
                "weight": WEIGHT_CONCENTRATION,
                "detail": concentration_detail,
            },
            "factor_resistance": {
                "score": round(factor_resistance_score, 1),
                "weight": WEIGHT_FACTOR_RESISTANCE,
                "detail": factor_resistance_detail,
            },
            "recovery_hygiene": {
                "score": round(recovery_hygiene_score, 1),
                "weight": WEIGHT_RECOVERY_HYGIENE,
                "detail": recovery_hygiene_detail,
            },
            "exposure_and_freshness": {
                "score": round(exposure_freshness_score, 1),
                "weight": WEIGHT_EXPOSURE_FRESHNESS,
                "detail": exposure_freshness_detail,
            },
        },
    }


def get_prioritized_gaps(graph: nx.DiGraph) -> list:
    """Return remediation actions ordered by blast-radius reduction.

    Each gap is a dict: {kind, node, exposed_identities, description}.
    exposed_identities is what fixing this gap would protect — the
    basis for the ordering. description is already in consequence
    language (see translate_to_consequences()).
    """
    identities = _identities(graph)
    gaps = []

    for node in _cut_vertices(graph):
        exposed = [d for d in nx.descendants(graph, node) if d in identities]
        gaps.append({
            "kind": "cut_vertex",
            "node": node,
            "exposed_identities": exposed,
            "description": translate_to_consequences("cut_vertex", node, exposed),
        })

    _, factor_detail = _compute_factor_resistance(graph)
    for identity in factor_detail["vulnerable_identities"]:
        gaps.append({
            "kind": "phishing_vulnerable",
            "node": identity,
            "exposed_identities": [identity],
            "description": translate_to_consequences("phishing_vulnerable", identity, [identity]),
        })

    _, hygiene_detail = _compute_recovery_hygiene(graph)
    for identity in hygiene_detail["asymmetric_identities"]:
        gaps.append({
            "kind": "recovery_asymmetry",
            "node": identity,
            "exposed_identities": [identity],
            "description": translate_to_consequences("recovery_asymmetry", identity, [identity]),
        })

    for cycle in hygiene_detail["cycles"]:
        exposed = [n for n in cycle if n in identities]
        gaps.append({
            "kind": "cycle",
            "node": tuple(cycle),
            "exposed_identities": exposed,
            "description": translate_to_consequences("cycle", cycle, exposed),
        })

    for identity in _orphaned_identities(graph):
        gaps.append({
            "kind": "orphaned_factor",
            "node": identity,
            "exposed_identities": [identity],
            "description": translate_to_consequences("orphaned_factor", identity, [identity]),
        })

    gaps.sort(key=lambda g: len(g["exposed_identities"]), reverse=True)
    return gaps


def translate_to_consequences(metric_name: str, value, affected_nodes: list) -> str:
    """Translate an internal metric into consequence language.

    The UI must never display metric_name or value directly to the
    user — only the string this function returns, e.g. "If you lose
    access to X, these N accounts are exposed: [list]".
    """
    affected_nodes = affected_nodes or []
    count = len(affected_nodes)
    plural = "s" if count != 1 else ""

    if metric_name == "blast_radius":
        if count == 0:
            return f"If you lose access to {value}, nothing else is exposed."
        return (
            f"If you lose access to {value}, these {count} account{plural} "
            f"are exposed: {', '.join(str(n) for n in affected_nodes)}."
        )

    if metric_name == "cut_vertex":
        return f"{value} is the single most critical failure point in your identity."

    if metric_name == "phishing_vulnerable":
        return f"{value} is vulnerable to phishing — it has no phishing-resistant factor."

    if metric_name == "recovery_asymmetry":
        return (
            f"{value} has a strong sign-in factor, but a weaker recovery path. "
            "In practice, its security is only as strong as that recovery path."
        )

    if metric_name == "cycle":
        chain = value if isinstance(value, (list, tuple)) else [value]
        return (
            f"{' and '.join(str(n) for n in chain)} protect each other. "
            "If you lose one, you lose both."
        )

    if metric_name == "orphaned_factor":
        return (
            f"{value} has no backup. If you lose the device it depends on, "
            "you lose access permanently."
        )

    # Honest degradation: an unrecognized metric name is still reported,
    # not silently dropped.
    return f"{metric_name}: {value} (affects {count} account{plural})."
