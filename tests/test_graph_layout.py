"""Tests for graph_layout.py's pure-Python force-directed layout."""

import graph
import graph_layout


def test_empty_graph_returns_empty_positions():
    assert graph_layout.compute_layout(graph.get_graph()) == {}


def test_single_node_is_centered():
    graph.add_node("a", "Identity", {})
    positions = graph_layout.compute_layout(graph.get_graph(), width=800, height=600)

    assert positions == {"a": (400, 300)}


def test_all_nodes_get_a_position_within_bounds():
    graph.add_node("a", "Identity", {})
    graph.add_node("b", "Identity", {})
    graph.add_node("c", "Device", {})
    graph.add_edge("a", "b", "AUTHENTICATES")
    graph.add_edge("c", "a", "RECOVERS")

    width, height = 800.0, 600.0
    positions = graph_layout.compute_layout(graph.get_graph(), width=width, height=height)

    assert set(positions.keys()) == {"a", "b", "c"}
    for x, y in positions.values():
        assert 0.0 <= x <= width
        assert 0.0 <= y <= height


def test_layout_is_deterministic_for_a_fixed_seed():
    graph.add_node("a", "Identity", {})
    graph.add_node("b", "Identity", {})
    graph.add_node("c", "Device", {})
    graph.add_edge("a", "b", "AUTHENTICATES")
    graph.add_edge("c", "a", "RECOVERS")

    first = graph_layout.compute_layout(graph.get_graph(), seed=7)
    second = graph_layout.compute_layout(graph.get_graph(), seed=7)

    assert first == second


def test_different_seeds_can_produce_different_layouts():
    graph.add_node("a", "Identity", {})
    graph.add_node("b", "Identity", {})
    graph.add_node("c", "Device", {})
    graph.add_edge("a", "b", "AUTHENTICATES")
    graph.add_edge("c", "a", "RECOVERS")

    first = graph_layout.compute_layout(graph.get_graph(), seed=1)
    second = graph_layout.compute_layout(graph.get_graph(), seed=2)

    assert first != second


def test_connected_nodes_end_up_closer_than_a_distant_unconnected_node():
    """Not a precise geometric guarantee (it's a force simulation, not
    an exact solver) — but a node with no edges to anything should not
    reliably land right on top of a tightly connected cluster."""
    graph.add_node("hub", "Identity", {})
    for i in range(5):
        node_id = f"leaf{i}"
        graph.add_node(node_id, "Identity", {})
        graph.add_edge("hub", node_id, "AUTHENTICATES")
    graph.add_node("isolated", "Identity", {})  # no edges at all

    positions = graph_layout.compute_layout(graph.get_graph(), width=800, height=600, iterations=300)

    def distance(a, b):
        (ax, ay), (bx, by) = positions[a], positions[b]
        return ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5

    avg_hub_to_leaf = sum(distance("hub", f"leaf{i}") for i in range(5)) / 5
    hub_to_isolated = distance("hub", "isolated")

    assert hub_to_isolated > avg_hub_to_leaf
