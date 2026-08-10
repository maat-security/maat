"""Tests for export.py's self-contained HTML report: content
correctness, HTML escaping of user-controlled text, "genuinely
self-contained" (no external references, no JS), and locale handling.
"""

import i18n
import export
import graph


def _sample_graph():
    graph.add_node("gmail", "Identity", {
        "display_name": "Gmail", "criticality": 5, "breached": True,
    })
    graph.add_node("gmail::factor", "Factor", {"kind": "password"})
    graph.add_edge("gmail::factor", "gmail", "AUTHENTICATES")
    return graph.get_graph()


def test_generate_html_includes_score_and_gaps():
    g = _sample_graph()
    html_out = export.generate_html(g)

    assert "<!DOCTYPE html>" in html_out
    assert "/100" in html_out
    assert "known data breach" in html_out


def test_generate_html_escapes_hostile_history_text():
    g = _sample_graph()
    history = [{"description": "Fixed <script>alert(1)</script> account", "completed_at": "2026-01-01"}]

    html_out = export.generate_html(g, history)

    assert "<script>alert(1)</script>" not in html_out
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html_out


def test_generate_html_has_no_external_references_or_js():
    html_out = export.generate_html(_sample_graph())

    assert "http://" not in html_out
    assert "https://" not in html_out
    assert "<script" not in html_out.lower()
    assert "<link " not in html_out.lower()


def test_generate_html_no_secret_shaped_strings():
    html_out = export.generate_html(_sample_graph())
    lowered = html_out.lower()
    for forbidden in ("password_hash", "totp_seed", "recovery_code", "private_key"):
        assert forbidden not in lowered


def test_render_gaps_shows_honest_empty_state_for_an_empty_list():
    # A hand-built empty gap list rather than trying to contrive a
    # graph with zero gaps — any minimal test graph tends to trip
    # cut_vertex trivially (its one non-leaf node is always an
    # articulation point in a small star-shaped graph).
    assert "No urgent gaps found." in export._render_gaps([])


def test_generate_html_no_history_omits_history_section():
    html_out = export.generate_html(_sample_graph(), history=None)
    assert "Recently Completed" not in html_out


def test_generate_html_respects_active_locale():
    try:
        i18n.set_locale("es")
        html_out = export.generate_html(_sample_graph())
        assert 'lang="es"' in html_out
        assert "Reporte de Postura" in html_out
    finally:
        i18n.set_locale("en")


def _strip_generated_timestamp(html_text: str) -> str:
    """generate_html() embeds datetime.now() — strip that one line
    before comparing two independently generated reports, so this test
    isn't flaky across a minute boundary."""
    return "\n".join(
        line for line in html_text.splitlines() if "class=\"generated\"" not in line
    )


def test_export_to_file_writes_matching_content(tmp_path):
    g = _sample_graph()
    out_path = tmp_path / "report.html"

    export.export_to_file(g, str(out_path))

    assert out_path.exists()
    written = _strip_generated_timestamp(out_path.read_text(encoding="utf-8"))
    fresh = _strip_generated_timestamp(export.generate_html(g))
    assert written == fresh
