"""Tests for remediation.py: provider detection, runbook lookup,
before/after simulation, and all six _apply_fix mutations (through
mark_gap_resolved(), which is the only public entry point to them)."""

import pytest

import graph
import metrics
import remediation
import store


def test_detect_provider_matches_known_domains():
    assert remediation.detect_provider("https://myaccount.google.com/security") == "google"
    assert remediation.detect_provider("github.com/settings") == "github"
    assert remediation.detect_provider("https://outlook.com") == "microsoft"
    assert remediation.detect_provider("icloud.com") == "apple"


def test_detect_provider_unknown_or_missing_is_generic_never_a_guess():
    assert remediation.detect_provider("https://some-random-bank.example.com") == "generic"
    assert remediation.detect_provider(None) == "generic"
    assert remediation.detect_provider("") == "generic"


def test_get_runbook_uses_provider_specific_steps_when_url_matches():
    graph.add_node("gh", "Identity", {"url": "https://github.com"})
    gap = {"kind": "phishing_vulnerable", "node": "gh", "exposed_identities": ["gh"], "description": "x"}

    runbook = remediation.get_runbook(graph.get_graph(), gap)
    assert runbook["deep_link"] == "https://github.com/settings/security"
    assert any("passkey" in step.lower() for step in runbook["steps"])


def test_get_runbook_falls_back_to_generic_for_unrecognized_provider():
    graph.add_node("bank", "Identity", {"url": "https://some-random-bank.example.com"})
    gap = {"kind": "phishing_vulnerable", "node": "bank", "exposed_identities": ["bank"], "description": "x"}

    runbook = remediation.get_runbook(graph.get_graph(), gap)
    assert runbook["deep_link"] is None
    assert runbook["steps"] == remediation.GENERIC_RUNBOOKS["phishing_vulnerable"]["steps"]


def test_get_runbook_includes_sequence_warning_only_when_defined():
    graph.add_node("bank", "Identity", {})
    asymmetry_gap = {"kind": "recovery_asymmetry", "node": "bank", "exposed_identities": ["bank"], "description": "x"}
    orphaned_gap = {"kind": "orphaned_factor", "node": "bank", "exposed_identities": ["bank"], "description": "x"}

    assert remediation.get_runbook(graph.get_graph(), asymmetry_gap)["sequence_warning"] is not None
    assert remediation.get_runbook(graph.get_graph(), orphaned_gap)["sequence_warning"] is None


def test_get_runbook_has_steps_for_breached_kind():
    graph.add_node("gmail", "Identity", {"url": None})
    gap = {"kind": "breached", "node": "gmail", "exposed_identities": ["gmail"], "description": "x"}

    runbook = remediation.get_runbook(graph.get_graph(), gap)
    assert runbook["steps"], "the 'breached' kind must have a non-empty runbook"
    assert "password" in runbook["steps"][0].lower()


def test_simulate_fix_never_mutates_the_live_graph():
    graph.add_node("email", "Identity", {})
    graph.add_node("bank", "Identity", {})
    graph.add_node("phone", "Device", {})
    graph.add_edge("phone", "email", "AUTHENTICATES")
    graph.add_edge("phone", "bank", "RECOVERS")
    gap = {"kind": "cut_vertex", "node": "phone", "exposed_identities": ["email", "bank"], "description": "x"}

    before_edges = graph.get_graph().number_of_edges()
    simulation = remediation.simulate_fix(graph.get_graph(), gap)
    after_edges = graph.get_graph().number_of_edges()

    assert after_edges == before_edges, "simulate_fix must operate on a copy, never the live graph"
    assert simulation["after_exposed"] <= simulation["before_exposed"]


def _setup_phishing_vulnerable():
    graph.add_node("gmail", "Identity", {"criticality": 5})
    graph.add_node("gmail::factor", "Factor", {"kind": "password"})
    graph.add_edge("gmail::factor", "gmail", "AUTHENTICATES")
    return "gmail"


def _setup_orphaned_factor():
    graph.add_node("github", "Identity", {"criticality": 5})
    graph.add_node("github::factor", "Factor", {"kind": "totp"})
    graph.add_edge("github::factor", "github", "AUTHENTICATES")
    return "github"


def _setup_breached():
    graph.add_node("gmail", "Identity", {"breached": True})
    return "gmail"


@pytest.mark.parametrize("kind,setup", [
    ("phishing_vulnerable", _setup_phishing_vulnerable),
    ("orphaned_factor", _setup_orphaned_factor),
    ("breached", _setup_breached),
])
def test_mark_gap_resolved_applies_fix_and_records_history(isolated_store, kind, setup):
    store.init_store("a-throwaway-test-passphrase")
    node_id = setup()

    gap = {"kind": kind, "node": node_id, "exposed_identities": [node_id], "description": f"fixing {kind}"}
    record = remediation.mark_gap_resolved(graph.get_graph(), gap)

    assert record["kind"] == kind
    assert record["completed_at"]
    history = remediation.get_completed_history()
    assert len(history) == 1
    assert history[0]["kind"] == kind


def test_apply_phishing_fix_upgrades_weakest_factor_to_passkey():
    graph.add_node("gmail", "Identity", {"criticality": 5})
    graph.add_node("gmail::factor", "Factor", {"kind": "password"})
    graph.add_edge("gmail::factor", "gmail", "AUTHENTICATES")
    gap = {"kind": "phishing_vulnerable", "node": "gmail", "exposed_identities": ["gmail"], "description": "x"}

    remediation._apply_fix(graph.get_graph(), gap)
    assert graph.get_graph().nodes["gmail::factor"]["kind"] == "passkey"


def test_apply_recovery_asymmetry_fix_removes_weaker_recovery_edge():
    graph.add_node("bank", "Identity", {"criticality": 5})
    graph.add_node("bank::factor", "Factor", {"kind": "passkey"})
    graph.add_edge("bank::factor", "bank", "AUTHENTICATES")
    graph.add_node("sms_channel", "RecoveryChannel", {})
    graph.add_edge("sms_channel", "bank", "RECOVERS")
    gap = {"kind": "recovery_asymmetry", "node": "bank", "exposed_identities": ["bank"], "description": "x"}

    remediation._apply_fix(graph.get_graph(), gap)
    assert not graph.get_graph().has_edge("sms_channel", "bank")


def test_apply_cycle_fix_breaks_the_cycle():
    graph.add_node("email", "Identity", {})
    graph.add_node("phone_number", "Identity", {})
    graph.add_edge("email", "phone_number", "RECOVERS")
    graph.add_edge("phone_number", "email", "RECOVERS")
    gap = {"kind": "cycle", "node": ("email", "phone_number"), "exposed_identities": ["email", "phone_number"], "description": "x"}

    remediation._apply_fix(graph.get_graph(), gap)
    assert metrics._cycles(graph.get_graph()) == []


def test_apply_orphaned_factor_fix_adds_a_recovery_channel():
    graph.add_node("github", "Identity", {"criticality": 5})
    graph.add_node("github::factor", "Factor", {"kind": "totp"})
    graph.add_edge("github::factor", "github", "AUTHENTICATES")
    gap = {"kind": "orphaned_factor", "node": "github", "exposed_identities": ["github"], "description": "x"}

    remediation._apply_fix(graph.get_graph(), gap)
    recovery_nodes = [u for u, _, d in graph.get_graph().in_edges("github", data=True) if d.get("type") == "RECOVERS"]
    assert recovery_nodes, "orphaned_factor fix should add at least one recovery path"


def test_apply_cut_vertex_fix_adds_a_parallel_backup_node():
    graph.add_node("phone", "Device", {})
    graph.add_node("email", "Identity", {})
    graph.add_edge("phone", "email", "AUTHENTICATES")
    gap = {"kind": "cut_vertex", "node": "phone", "exposed_identities": ["email"], "description": "x"}

    remediation._apply_fix(graph.get_graph(), gap)
    assert "phone::backup" in graph.get_graph()
    assert graph.get_graph().has_edge("phone::backup", "email")


def test_apply_breached_fix_clears_the_flag():
    graph.add_node("gmail", "Identity", {"breached": True})
    gap = {"kind": "breached", "node": "gmail", "exposed_identities": ["gmail"], "description": "x"}

    remediation._apply_fix(graph.get_graph(), gap)
    assert graph.get_graph().nodes["gmail"]["breached"] is False
