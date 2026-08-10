"""Tests for graph.py: node/edge validation, blast radius, cut
vertices, cycle detection, and the secret-attribute guard."""

import pytest

import graph


def test_add_node_rejects_unknown_type():
    with pytest.raises(ValueError):
        graph.add_node("x", "NotARealType", {})


def test_add_node_rejects_secret_looking_attributes():
    with pytest.raises(ValueError):
        graph.add_node("x", "Identity", {"password": "hunter2"})
    with pytest.raises(ValueError):
        graph.add_node("x", "Factor", {"totp_seed": "JBSWY3DPEHPK3PXP"})
    assert "x" not in graph.get_graph(), "a rejected add_node call must not partially add the node"


def test_add_node_defaults_confidence_and_last_verified():
    graph.add_node("gmail", "Identity", {})
    node = graph.get_graph().nodes["gmail"]
    assert node["confidence"] == "unknown"
    assert node["last_verified"] is None


def test_add_node_is_idempotent_update_not_error():
    graph.add_node("gmail", "Identity", {"criticality": 3})
    graph.add_node("gmail", "Identity", {"criticality": 5})
    assert graph.get_graph().nodes["gmail"]["criticality"] == 5


def test_add_edge_rejects_unknown_edge_type_and_missing_nodes():
    graph.add_node("a", "Identity", {})
    graph.add_node("b", "Identity", {})
    with pytest.raises(ValueError):
        graph.add_edge("a", "b", "NOT_A_REAL_EDGE_TYPE")
    with pytest.raises(ValueError):
        graph.add_edge("a", "missing", "AUTHENTICATES")
    with pytest.raises(ValueError):
        graph.add_edge("missing", "a", "AUTHENTICATES")


def test_make_node_id_slugifies_and_disambiguates_collisions():
    id1 = graph.make_node_id("Gmail")
    graph.add_node(id1, "Identity", {"display_name": "Gmail"})

    # Same display name -> same id, not a new suffix.
    assert graph.make_node_id("Gmail") == id1

    # Different display name that slugifies the same way -> disambiguated.
    id2 = graph.make_node_id("gmail!!!")
    assert id2 != id1
    graph.add_node(id2, "Identity", {"display_name": "gmail!!!"})
    assert id2 == f"{id1}-2"


def test_get_blast_radius_is_descendants_only():
    graph.add_node("phone", "Device", {})
    graph.add_node("email", "Identity", {})
    graph.add_node("bank", "Identity", {})
    graph.add_edge("phone", "email", "RECOVERS")
    graph.add_edge("email", "bank", "RECOVERS")

    assert graph.get_blast_radius("phone") == ["bank", "email"]
    assert graph.get_blast_radius("bank") == []


def test_get_blast_radius_raises_for_unknown_node():
    with pytest.raises(ValueError):
        graph.get_blast_radius("does-not-exist")


def test_get_cut_vertices_finds_the_single_bridge():
    # phone -> email -> bank, and phone -> github (two branches hanging
    # off phone). Removing "phone" disconnects email/bank from github.
    for node_id in ("phone", "email", "bank", "github"):
        graph.add_node(node_id, "Identity" if node_id != "phone" else "Device", {})
    graph.add_edge("phone", "email", "AUTHENTICATES")
    graph.add_edge("email", "bank", "RECOVERS")
    graph.add_edge("phone", "github", "AUTHENTICATES")

    assert "phone" in graph.get_cut_vertices()
    assert "bank" not in graph.get_cut_vertices()


def test_get_cycles_finds_mutual_recovery():
    graph.add_node("email", "Identity", {})
    graph.add_node("phone_number", "Identity", {})
    graph.add_edge("email", "phone_number", "RECOVERS")
    graph.add_edge("phone_number", "email", "RECOVERS")

    cycles = graph.get_cycles()
    assert len(cycles) == 1
    assert set(cycles[0]) == {"email", "phone_number"}


def test_get_cycles_empty_when_acyclic():
    graph.add_node("a", "Identity", {})
    graph.add_node("b", "Identity", {})
    graph.add_edge("a", "b", "RECOVERS")
    assert graph.get_cycles() == []


def test_default_criticality_known_and_unknown_categories():
    assert graph.default_criticality("financial") == 5
    assert graph.default_criticality("streaming") == 1
    assert graph.default_criticality("some-unlisted-category") == graph.DEFAULT_CRITICALITY


def test_factor_resistance_rank_phishing_resistant_kinds_rank_highest():
    assert graph.factor_resistance_rank("passkey") == graph.factor_resistance_rank("hardware_key")
    assert graph.factor_resistance_rank("passkey") > graph.factor_resistance_rank("totp")
    assert graph.factor_resistance_rank("totp") > graph.factor_resistance_rank("password")
    assert graph.factor_resistance_rank("some-unknown-kind") == 0


def test_reset_graph_clears_everything():
    graph.add_node("x", "Identity", {})
    graph.reset_graph()
    assert graph.get_graph().number_of_nodes() == 0
