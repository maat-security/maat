"""Self-contained HTML posture report.

generate_html() takes an explicit graph argument rather than reaching
into graph.py's module-level singleton — same testability principle as
metrics.py and remediation.py, so this works on any nx.DiGraph
(including a hand-built one in a test) independent of app state.

The report holds score + breakdown + prioritized gaps + remediation
history, all already in consequence language (metrics.py) or
plain-language runbook steps (remediation.py) — nothing here computes
anything new. There is nothing to redact for secrets: graph.add_node()
already refuses to store secret-looking attributes, so the graph this
function reads from never had a password, TOTP seed, or recovery code
in it to begin with.

Self-contained means exactly that: one .html file, inline CSS only, no
external fonts/scripts/images, no network calls. It opens and reads
correctly offline, in any browser, indefinitely — the same "no
exceptions" local-first principle the rest of the app follows.
"""

import datetime
import html
from pathlib import Path

import networkx as nx

import metrics
import theme
from i18n import get_locale, t

COMPONENT_ORDER = ("concentration", "factor_resistance", "recovery_hygiene", "exposure_and_freshness")


def _component_labels() -> dict:
    """Built fresh on every call, not cached at import time, so the
    report reflects whichever locale is active when it's generated —
    same convention as ui/dashboard.py._component_labels()."""
    return {
        "concentration": t("Concentration"),
        "factor_resistance": t("Factor Resistance"),
        "recovery_hygiene": t("Recovery Hygiene"),
        "exposure_and_freshness": t("Exposure and Freshness"),
    }


def generate_html(g: nx.DiGraph, history: list = None) -> str:
    """Return the report as a single self-contained HTML string.

    history defaults to no history section — pass
    remediation.get_completed_history() explicitly to include it. Kept
    as an explicit argument rather than read from the store in here,
    so this function never requires a vault to be open to run (and
    stays testable against a hand-built graph with no store at all).
    """
    generated_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    score = metrics.compute_score(g)
    gaps = metrics.get_prioritized_gaps(g)

    return f"""<!DOCTYPE html>
<html lang="{html.escape(get_locale())}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(t("Maat"))} — {html.escape(t("Posture Report"))}</title>
<style>{_css()}</style>
</head>
<body>
<div class="page">
{_render_header(generated_at)}
{_render_score(score)}
{_render_gaps(gaps)}
{_render_history(history or [])}
{_render_footer()}
</div>
</body>
</html>
"""


def export_to_file(g: nx.DiGraph, filepath, history: list = None) -> None:
    """Render generate_html() and write it to filepath as UTF-8."""
    Path(filepath).write_text(generate_html(g, history), encoding="utf-8")


# --------------------------------------------------------------------------
# Rendering — each function returns a fragment of HTML; all user-provided
# text (display names built from import/questionnaire data) goes through
# html.escape() before it's ever interpolated into markup.
# --------------------------------------------------------------------------

def _render_header(generated_at: str) -> str:
    return f"""<header class="header">
  <div class="brand">🪶 {html.escape(t("Maat"))}</div>
  <div class="tagline">{html.escape(t("Your identity, in balance."))}</div>
  <div class="generated">{html.escape(t("Generated"))}: {html.escape(generated_at)}</div>
</header>"""


def _render_score(score: dict) -> str:
    overall = score["overall"]
    labels = _component_labels()

    rows = []
    for key in COMPONENT_ORDER:
        component = score["components"][key]
        rows.append(f"""    <div class="component-row">
      <div class="component-head">
        <span class="component-name">{html.escape(labels[key])}</span>
        <span class="component-score">{component['score']:.0f}/100</span>
      </div>
      <div class="bar-track"><div class="bar-fill" style="width:{max(0.0, min(100.0, component['score']))}%"></div></div>
    </div>""")

    return f"""<section class="card score-card">
  <div class="overall">{overall:.0f}<span class="overall-max">/100</span></div>
{chr(10).join(rows)}
</section>"""


def _render_gaps(gaps: list) -> str:
    title = html.escape(t("Prioritized Actions"))
    if not gaps:
        return f"""<section class="card">
  <h2>{title}</h2>
  <p class="muted">{html.escape(t("No urgent gaps found."))}</p>
</section>"""

    items = []
    for gap in gaps:
        items.append(
            f'    <li>{html.escape(gap["description"])}</li>'
        )
    return f"""<section class="card">
  <h2>{title}</h2>
  <ol class="gap-list">
{chr(10).join(items)}
  </ol>
</section>"""


def _render_history(history: list) -> str:
    if not history:
        return ""
    title = html.escape(t("Recently Completed"))
    items = []
    for record in history[::-1]:
        date_text = html.escape(str(record.get("completed_at", ""))[:10])
        description = html.escape(str(record.get("description", "")))
        items.append(f'    <li>✓ {description} <span class="muted">({date_text})</span></li>')
    return f"""<section class="card">
  <h2>{title}</h2>
  <ul class="history-list">
{chr(10).join(items)}
  </ul>
</section>"""


def _render_footer() -> str:
    return f"""<footer class="footer">
  <p>{html.escape(t(
        "This file was generated locally and contains no passwords, "
        "TOTP seeds, or recovery codes. It never leaves this device "
        "unless you send it yourself."
    ))}</p>
</footer>"""


def _css() -> str:
    colors = theme.COLORS["light"]
    return f"""
  :root {{
    --bg: {colors['bg']};
    --card-bg: {colors['card_bg']};
    --text-primary: {colors['text_primary']};
    --text-secondary: {colors['text_secondary']};
    --gold: {theme.GOLD};
    --alert: {theme.ALERT};
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: var(--bg);
    color: var(--text-primary);
    font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  }}
  .page {{ max-width: 720px; margin: 0 auto; padding: 32px 24px 48px; }}
  .header {{ text-align: center; margin-bottom: 24px; }}
  .brand {{ font-size: 28px; font-weight: 700; color: var(--gold); }}
  .tagline {{ color: var(--text-secondary); margin-top: 2px; }}
  .generated {{ color: var(--text-secondary); font-size: 12px; margin-top: 8px; }}
  .card {{
    background: var(--card-bg);
    border-radius: 10px;
    padding: 20px 24px;
    margin-bottom: 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  }}
  .score-card {{ text-align: center; }}
  .overall {{ font-size: 40px; font-weight: 700; color: var(--gold); }}
  .overall-max {{ font-size: 20px; color: var(--text-secondary); font-weight: 400; }}
  .component-row {{ text-align: left; margin-top: 14px; }}
  .component-head {{ display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 4px; }}
  .component-name {{ font-weight: 600; }}
  .component-score {{ color: var(--text-secondary); }}
  .bar-track {{ background: var(--bg); border-radius: 4px; height: 6px; overflow: hidden; }}
  .bar-fill {{ background: var(--gold); height: 100%; }}
  h2 {{ font-size: 16px; margin: 0 0 12px; }}
  .gap-list, .history-list {{ margin: 0; padding-left: 20px; }}
  .gap-list li, .history-list li {{ margin-bottom: 10px; line-height: 1.4; }}
  .muted {{ color: var(--text-secondary); font-size: 12px; }}
  .footer {{ text-align: center; color: var(--text-secondary); font-size: 12px; margin-top: 24px; }}
"""
