"""Directed dependency graph for a user's digital identity.

Node types: Identity, Factor, Device, RecoveryChannel, Store, Provider, Person.
Edge types: AUTHENTICATES, RECOVERS, STORES, HOSTS, UNLOCKS, DELEGATES.

Semantics are uniform across edge types: source -> target means
controlling source enables taking control of target.

Phase 0: signatures only. The graph structure and analysis functions
are implemented in a later phase.
"""

import networkx as nx

_graph = nx.DiGraph()


def add_node(node_id: str, node_type: str, attributes: dict) -> None:
    """Add a node to the graph.

    node_type must be one of: Identity, Factor, Device, RecoveryChannel,
    Store, Provider, Person. attributes carries type-specific fields such
    as criticality, resistance, confidence, and last_verified — never
    secret values (passwords, TOTP seeds, recovery codes).
    """
    pass


def add_edge(source: str, target: str, edge_type: str) -> None:
    """Add a directed edge from source to target.

    edge_type must be one of: AUTHENTICATES, RECOVERS, STORES, HOSTS,
    UNLOCKS, DELEGATES.
    """
    pass


def get_blast_radius(node_id: str) -> list:
    """Return the nodes that become reachable — and therefore exposed —
    if node_id is compromised or lost."""
    pass


def get_cut_vertices() -> list:
    """Return nodes whose loss disconnects the graph, i.e. single
    points of failure in the user's identity."""
    pass


def get_cycles() -> list:
    """Return cycles in the graph, e.g. an email and a phone that each
    recover the other."""
    pass


def get_graph() -> nx.DiGraph:
    """Return the underlying NetworkX graph object."""
    return _graph
