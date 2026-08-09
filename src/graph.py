"""Directed dependency graph for a user's digital identity.

Node types: Identity, Factor, Device, RecoveryChannel, Store, Provider, Person.
Edge types: AUTHENTICATES, RECOVERS, STORES, HOSTS, UNLOCKS, DELEGATES.

Semantics are uniform across edge types: source -> target means
controlling source enables taking control of target. Blast radius, cut
vertices, and cycles are all computed against that reachability
structure.

Node attribute conventions (not enforced beyond the checks in
add_node(), but relied on by metrics.py):

  All nodes:
    confidence     "unknown" | "declared" | "verified" (default: "unknown")
    last_verified  ISO 8601 date string, or None (default: None)

  Identity nodes additionally carry:
    criticality  int 1-5 — see default_criticality() for category defaults
    category     free-text category, used only to pick a criticality default
    breached     bool, set by the Have I Been Pwned integration

  Factor nodes additionally carry:
    kind  one of FACTOR_RESISTANCE's keys (password, sms, push, totp,
          biometric, passkey, hardware_key) — drives resistance ranking

Never store secret values (passwords, TOTP seeds, recovery codes) as
attributes — add_node() refuses any attribute key that looks like one.
"""

import re

import networkx as nx

NODE_TYPES = {
    "Identity", "Factor", "Device", "RecoveryChannel", "Store", "Provider", "Person",
}

EDGE_TYPES = {"AUTHENTICATES", "RECOVERS", "STORES", "HOSTS", "UNLOCKS", "DELEGATES"}

# Resistance ranking for Factor.kind, low to high. Only "passkey" and
# "hardware_key" are phishing-resistant (WebAuthn) — TOTP is still
# phishable via real-time relay, which is why it ranks below them.
FACTOR_RESISTANCE = {
    "password": 0,
    "sms": 1,
    "push": 2,
    "totp": 3,
    "biometric": 3,
    "passkey": 4,
    "hardware_key": 4,
}
PHISHING_RESISTANT_KINDS = frozenset({"passkey", "hardware_key"})

CRITICALITY_DEFAULTS = {
    "financial": 5,
    "primary_email": 5,
    "health": 4,
    "social": 3,
    "streaming": 1,
}
DEFAULT_CRITICALITY = 3

# Attribute keys that would mean a secret value is being stored — refused
# outright, per the "never store secrets" design principle.
_FORBIDDEN_ATTRIBUTE_KEYS = frozenset({
    "password", "secret", "totp_seed", "seed", "recovery_code", "recovery_codes",
    "private_key", "token",
})

_graph = nx.DiGraph()


def default_criticality(category: str) -> int:
    """Return the default criticality (1-5) for an identity category.

    Falls back to DEFAULT_CRITICALITY for anything not in
    CRITICALITY_DEFAULTS — an unrecognized category is a legitimate
    input, not an error.
    """
    return CRITICALITY_DEFAULTS.get(category, DEFAULT_CRITICALITY)


def factor_resistance_rank(kind: str) -> int:
    """Return the phishing-resistance rank for a Factor.kind value.

    Unknown kinds rank at 0 (treated as no better than a password) —
    honest degradation, per design principle 7.
    """
    return FACTOR_RESISTANCE.get(kind, 0)


def make_node_id(display_name: str) -> str:
    """Derive a graph node id from a free-text display name.

    Lowercases and collapses non-alphanumerics to hyphens. If the
    resulting id already belongs to a node with a *different*
    display_name, appends a numeric suffix instead of colliding with
    it — two distinct accounts that happen to slugify the same way
    (e.g. two accounts both named "Bank") stay distinct nodes.
    """
    base = re.sub(r"[^a-z0-9]+", "-", display_name.strip().lower()).strip("-") or "account"
    candidate = base
    suffix = 2
    while candidate in _graph.nodes and _graph.nodes[candidate].get("display_name") != display_name:
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def add_node(node_id: str, node_type: str, attributes: dict) -> None:
    """Add a node to the graph.

    node_type must be one of NODE_TYPES. attributes carries type-specific
    fields such as criticality, kind, confidence, and last_verified —
    never secret values. Re-adding an existing node_id updates its
    attributes rather than erroring.
    """
    if node_type not in NODE_TYPES:
        raise ValueError(f"Unknown node type: {node_type!r}")

    attributes = dict(attributes or {})
    forbidden = _FORBIDDEN_ATTRIBUTE_KEYS.intersection(attributes)
    if forbidden:
        raise ValueError(
            f"Refusing to store secret-looking attribute(s) {sorted(forbidden)} "
            f"on node {node_id!r} — the graph records existence and "
            "relationships, never secret values."
        )

    attributes.setdefault("confidence", "unknown")
    attributes.setdefault("last_verified", None)
    _graph.add_node(node_id, type=node_type, **attributes)


def add_edge(source: str, target: str, edge_type: str) -> None:
    """Add a directed edge from source to target.

    edge_type must be one of EDGE_TYPES. Both source and target must
    already exist as nodes — semantics depend on both ends having a
    declared type.
    """
    if edge_type not in EDGE_TYPES:
        raise ValueError(f"Unknown edge type: {edge_type!r}")
    if source not in _graph:
        raise ValueError(f"Unknown source node: {source!r}")
    if target not in _graph:
        raise ValueError(f"Unknown target node: {target!r}")
    _graph.add_edge(source, target, type=edge_type)


def get_blast_radius(node_id: str) -> list:
    """Return the nodes that become reachable — and therefore exposed —
    if node_id is compromised or lost.

    This is every node downstream of node_id in the control graph:
    controlling node_id transitively enables controlling all of them.
    """
    if node_id not in _graph:
        raise ValueError(f"Unknown node: {node_id!r}")
    return sorted(nx.descendants(_graph, node_id))


def get_cut_vertices() -> list:
    """Return nodes whose removal disconnects the graph, i.e. single
    points of failure in the user's identity.

    Computed as articulation points of the underlying undirected graph
    — the standard graph-theoretic notion of a cut vertex. Direction is
    dropped deliberately: a device that is the *only* link between two
    otherwise-separate clusters of accounts is a structural single
    point of failure regardless of which way the control edges point.
    """
    return sorted(nx.articulation_points(_graph.to_undirected()))


def get_cycles() -> list:
    """Return cycles in the graph, e.g. an email and a phone that each
    recover the other.

    Each cycle is a list of node ids in the order they appear. Uses
    simple_cycles(), which is fine at the scale of one person's identity
    graph (tens to low hundreds of nodes) but would not scale further.
    """
    return [list(cycle) for cycle in nx.simple_cycles(_graph)]


def get_graph() -> nx.DiGraph:
    """Return the underlying NetworkX graph object."""
    return _graph


def reset_graph() -> None:
    """Clear all nodes and edges.

    Not part of the original product surface — useful for tests and for
    starting a fresh session without restarting the process.
    """
    global _graph
    _graph = nx.DiGraph()
