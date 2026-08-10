"""Tests for metrics.py's four score components against known
scenarios, get_prioritized_gaps() ordering, and
translate_to_consequences()'s consequence-language output."""

import graph
import metrics


def _add_identity(node_id, criticality=5, **extra):
    graph.add_node(node_id, "Identity", {"criticality": criticality, **extra})


def _add_factor(identity_id, kind, factor_id=None):
    factor_id = factor_id or f"{identity_id}::factor"
    graph.add_node(factor_id, "Factor", {"kind": kind})
    graph.add_edge(factor_id, identity_id, "AUTHENTICATES")
    return factor_id


def test_compute_score_on_empty_graph_is_full_marks_not_a_penalty():
    score = metrics.compute_score(graph.get_graph())
    assert score["overall"] == 100.0
    for component in score["components"].values():
        assert component["score"] == 100.0


def test_concentration_drops_when_one_node_exposes_everything():
    _add_identity("email")
    _add_identity("bank")
    phone_factor = _add_factor("email", "sms", factor_id="phone")
    graph.add_edge("phone", "bank", "RECOVERS")

    score = metrics.compute_score(graph.get_graph())
    assert score["components"]["concentration"]["score"] < 100.0
    assert "phone" == score["components"]["concentration"]["detail"]["worst_node"]


def test_factor_resistance_full_marks_with_passkey_on_critical_identity():
    _add_identity("email", criticality=5)
    _add_factor("email", "passkey")

    score = metrics.compute_score(graph.get_graph())
    assert score["components"]["factor_resistance"]["score"] == 100.0


def test_factor_resistance_penalized_for_password_only_critical_identity():
    _add_identity("email", criticality=5)
    _add_factor("email", "password")

    score = metrics.compute_score(graph.get_graph())
    assert score["components"]["factor_resistance"]["score"] < 100.0
    assert "email" in score["components"]["factor_resistance"]["detail"]["vulnerable_identities"]


def test_factor_resistance_no_critical_identities_is_full_marks_not_a_penalty():
    _add_identity("streaming", criticality=1)
    _add_factor("streaming", "password")

    score = metrics.compute_score(graph.get_graph())
    assert score["components"]["factor_resistance"]["score"] == 100.0


def test_recovery_hygiene_penalizes_asymmetric_recovery():
    _add_identity("bank", criticality=5)
    _add_factor("bank", "passkey")
    graph.add_node("sms_channel", "RecoveryChannel", {})
    graph.add_edge("sms_channel", "bank", "RECOVERS")

    score = metrics.compute_score(graph.get_graph())
    assert score["components"]["recovery_hygiene"]["score"] < 100.0
    assert "bank" in score["components"]["recovery_hygiene"]["detail"]["asymmetric_identities"]


def test_recovery_hygiene_no_penalty_when_recovery_is_as_strong():
    _add_identity("bank", criticality=5)
    _add_factor("bank", "passkey")
    _add_factor("bank", "hardware_key", factor_id="backup_key")
    graph.add_edge("backup_key", "bank", "RECOVERS")

    score = metrics.compute_score(graph.get_graph())
    assert score["components"]["recovery_hygiene"]["score"] == 100.0


def test_recovery_hygiene_penalizes_cycles():
    _add_identity("email")
    _add_identity("phone_number")
    graph.add_edge("email", "phone_number", "RECOVERS")
    graph.add_edge("phone_number", "email", "RECOVERS")

    score = metrics.compute_score(graph.get_graph())
    assert score["components"]["recovery_hygiene"]["score"] <= 90.0
    assert len(score["components"]["recovery_hygiene"]["detail"]["cycles"]) == 1


def test_exposure_freshness_penalizes_breach_more_than_staleness():
    _add_identity("breached_account", breached=True, last_verified="2026-01-01T00:00:00+00:00")
    breach_only_score = metrics.compute_score(graph.get_graph())["components"]["exposure_and_freshness"]["score"]
    graph.reset_graph()

    _add_identity("stale_account", breached=False, last_verified=None)
    stale_only_score = metrics.compute_score(graph.get_graph())["components"]["exposure_and_freshness"]["score"]

    assert breach_only_score < stale_only_score < 100.0


def test_get_prioritized_gaps_includes_breached_kind():
    _add_identity("gmail", breached=True)
    _add_factor("gmail", "passkey")  # avoid also tripping phishing_vulnerable/orphaned_factor
    graph.add_node("backup", "RecoveryChannel", {"kind": "hardware_key"})
    graph.add_edge("backup", "gmail", "RECOVERS")

    gaps = metrics.get_prioritized_gaps(graph.get_graph())
    breach_gaps = [g for g in gaps if g["kind"] == "breached"]
    assert len(breach_gaps) == 1
    assert breach_gaps[0]["node"] == "gmail"
    assert "gmail" in breach_gaps[0]["description"]


def test_get_prioritized_gaps_sorted_by_exposure_descending():
    _add_identity("email")
    _add_identity("bank")
    _add_identity("shop")
    _add_factor("email", "sms", factor_id="phone")
    graph.add_edge("phone", "bank", "RECOVERS")
    graph.add_edge("phone", "shop", "RECOVERS")
    _add_factor("bank", "password")  # phishing_vulnerable gap, exposes only "bank"

    gaps = metrics.get_prioritized_gaps(graph.get_graph())
    exposure_counts = [len(g["exposed_identities"]) for g in gaps]
    assert exposure_counts == sorted(exposure_counts, reverse=True)


def test_translate_to_consequences_known_kinds():
    assert "nothing else is exposed" in metrics.translate_to_consequences("blast_radius", "phone", [])
    assert "exposed" in metrics.translate_to_consequences("blast_radius", "phone", ["email", "bank"])
    assert "single most critical" in metrics.translate_to_consequences("cut_vertex", "phone", [])
    assert "phishing" in metrics.translate_to_consequences("phishing_vulnerable", "gmail", ["gmail"])
    assert "weaker recovery path" in metrics.translate_to_consequences("recovery_asymmetry", "bank", ["bank"])
    assert "lose both" in metrics.translate_to_consequences("cycle", ["email", "phone"], ["email", "phone"])
    assert "no backup" in metrics.translate_to_consequences("orphaned_factor", "github", ["github"])
    assert "known data breach" in metrics.translate_to_consequences("breached", "gmail", ["gmail"])


def test_translate_to_consequences_unrecognized_kind_degrades_honestly():
    result = metrics.translate_to_consequences("some_future_metric", "x", ["a", "b"])
    assert "some_future_metric" in result
    assert "2 account" in result
