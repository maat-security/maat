"""Dashboard frame: posture score, prioritized actions, alerts.

Renders metrics.compute_score() and metrics.get_prioritized_gaps() —
both already in consequence language — over the current graph. Shows
an empty-state message instead of a zero score when there's no data
yet: "no data" and "bad posture" are not the same thing.
"""

import sys
from pathlib import Path

import customtkinter as ctk

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import graph  # noqa: E402
import metrics  # noqa: E402
import remediation  # noqa: E402
import store  # noqa: E402
import theme  # noqa: E402
from i18n import t  # noqa: E402

COMPONENT_ORDER = ("concentration", "factor_resistance", "recovery_hygiene", "exposure_and_freshness")


def _component_labels() -> dict:
    """Built fresh on every call (not cached at import time) so a
    language switch made earlier in the session is respected here."""
    return {
        "concentration": (
            t("Concentration"),
            t("How much falls if your single riskiest point is compromised"),
        ),
        "factor_resistance": (
            t("Factor Resistance"),
            t("How well your critical accounts resist phishing"),
        ),
        "recovery_hygiene": (
            t("Recovery Hygiene"),
            t("Whether your backdoors are weaker than your front doors"),
        ),
        "exposure_and_freshness": (
            t("Exposure and Freshness"),
            t("Whether there are known breaches or stale data"),
        ),
    }


class DashboardFrame(ctk.CTkFrame):
    """The main posture screen: score breakdown + prioritized gaps."""

    def __init__(self, master, on_add_data, on_view_remediation=None):
        colors = theme.current()
        super().__init__(master, fg_color=colors["bg"])
        self._on_add_data = on_add_data
        self._on_view_remediation = on_view_remediation
        self._build(colors)

    def _build(self, colors: dict) -> None:
        current_graph = graph.get_graph()

        ctk.CTkLabel(
            self,
            text=t("Maat"),
            text_color=theme.GOLD,
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(pady=(20, 2))

        ctk.CTkLabel(
            self,
            text=t("Your identity, in balance."),
            text_color=colors["text_secondary"],
        ).pack(pady=(0, 12))

        if current_graph.number_of_nodes() == 0:
            self._build_empty_state(colors)
        else:
            score = metrics.compute_score(current_graph)
            gaps = metrics.get_prioritized_gaps(current_graph)
            self._build_score_section(colors, score)
            self._build_gaps_section(colors, gaps)
            self._build_history_section(colors)

        ctk.CTkButton(
            self,
            text=t("Add More Data"),
            fg_color=theme.GOLD,
            text_color="#1A1A1A",
            hover_color=theme.GOLD_HOVER,
            command=self._on_add_data,
            width=200,
        ).pack(pady=(4, 12))

        StatusBarFrame(self).pack(side="bottom", fill="x")

    def _build_empty_state(self, colors: dict) -> None:
        ctk.CTkLabel(
            self,
            text=t("Your graph is empty. Add a few accounts to see your first result."),
            text_color=colors["text_primary"],
            wraplength=520,
            justify="center",
        ).pack(pady=60, padx=40, expand=True)

    def _build_score_section(self, colors: dict, score: dict) -> None:
        card = ctk.CTkFrame(self, fg_color=colors["card_bg"], corner_radius=10)
        card.pack(padx=30, pady=(0, 12), fill="x")

        ctk.CTkLabel(
            card,
            text=f"{score['overall']:.0f}/100",
            text_color=theme.GOLD,
            font=ctk.CTkFont(size=32, weight="bold"),
        ).pack(pady=(16, 4))

        labels = _component_labels()
        for key in COMPONENT_ORDER:
            component = score["components"][key]
            name, blurb = labels[key]
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=4)

            ctk.CTkLabel(
                row,
                text=f"{name}: {component['score']:.0f}/100",
                text_color=colors["text_primary"],
                font=ctk.CTkFont(size=13, weight="bold"),
                anchor="w",
            ).pack(fill="x")
            ctk.CTkLabel(
                row,
                text=blurb,
                text_color=colors["text_secondary"],
                font=ctk.CTkFont(size=11),
                anchor="w",
            ).pack(fill="x")

        ctk.CTkLabel(card, text="", height=1).pack(pady=(0, 8))

    def _build_gaps_section(self, colors: dict, gaps: list) -> None:
        container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        container.pack(padx=30, pady=(0, 8), fill="both", expand=True)

        if not gaps:
            ctk.CTkLabel(
                container, text=t("No urgent gaps found."), text_color=colors["text_secondary"],
            ).pack(pady=20)
            return

        for gap in gaps:
            row = ctk.CTkFrame(
                container,
                fg_color=colors["card_bg"],
                border_color=theme.GOLD,
                border_width=1,
                corner_radius=8,
            )
            row.pack(fill="x", pady=4)

            inner = ctk.CTkFrame(row, fg_color="transparent")
            inner.pack(fill="x", padx=14, pady=10)

            ctk.CTkLabel(
                inner,
                text=gap["description"],
                text_color=colors["text_primary"],
                wraplength=440,
                justify="left",
                anchor="w",
            ).pack(side="left", fill="x", expand=True)

            if self._on_view_remediation is not None:
                ctk.CTkButton(
                    inner,
                    text=t("Fix This"),
                    fg_color=theme.GOLD,
                    text_color="#1A1A1A",
                    hover_color=theme.GOLD_HOVER,
                    width=90,
                    command=lambda g=gap: self._on_view_remediation(g),
                ).pack(side="right", padx=(10, 0))

    def _build_history_section(self, colors: dict) -> None:
        history = remediation.get_completed_history()
        if not history:
            return

        ctk.CTkLabel(
            self,
            text=t("Recently Completed"),
            text_color=colors["text_secondary"],
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(pady=(4, 2), padx=30, anchor="w")

        for record in history[-3:][::-1]:
            date_text = record.get("completed_at", "")[:10]
            ctk.CTkLabel(
                self,
                text=f"✓ {record.get('description', '')}  ({date_text})",
                text_color=colors["text_secondary"],
                font=ctk.CTkFont(size=11),
                wraplength=560,
                justify="left",
                anchor="w",
            ).pack(padx=30, anchor="w")


class StatusBarFrame(ctk.CTkFrame):
    """Bottom status bar: vault path and graph coverage."""

    def __init__(self, master):
        colors = theme.current()
        super().__init__(master, fg_color=colors["card_bg"], height=28, corner_radius=0)

        vault_path = str(store.get_vault_path())

        ctk.CTkLabel(
            self, text=f"{t('Vault')}: {vault_path}", text_color=colors["text_secondary"],
        ).pack(side="left", padx=12, pady=4)

        ctk.CTkLabel(
            self, text=_graph_coverage_text(), text_color=colors["text_secondary"],
        ).pack(side="right", padx=12, pady=4)


def _graph_coverage_text() -> str:
    current_graph = graph.get_graph()
    total = current_graph.number_of_nodes()
    if total == 0:
        return t("Graph coverage: —")
    known = sum(1 for _, data in current_graph.nodes(data=True) if data.get("confidence") != "unknown")
    return t("Graph coverage: {known}/{total}").format(known=known, total=total)
