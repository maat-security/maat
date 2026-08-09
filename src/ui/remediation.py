"""Remediation frame: a guided (never automatic) walkthrough for a
single prioritized gap — impact, a before/after simulation, an
ordered provider-specific runbook, and a self-reported "I completed
this" step that updates Maat's own model. Nothing here writes to any
external account; the user does that themselves, on the provider's own
site, following the steps shown.
"""

import sys
import webbrowser
from pathlib import Path

import customtkinter as ctk

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import graph  # noqa: E402
import remediation  # noqa: E402
import theme  # noqa: E402
from i18n import t  # noqa: E402


class RemediationFrame(ctk.CTkFrame):
    """Guided walkthrough for exactly one gap from get_prioritized_gaps()."""

    def __init__(self, master, gap: dict, on_done):
        colors = theme.current()
        super().__init__(master, fg_color=colors["bg"])
        self._gap = gap
        self._on_done = on_done
        self._build(colors)

    def _build(self, colors: dict) -> None:
        current_graph = graph.get_graph()
        simulation = remediation.simulate_fix(current_graph, self._gap)
        runbook = remediation.get_runbook(current_graph, self._gap)

        ctk.CTkLabel(
            self,
            text=t("Fix This"),
            text_color=theme.GOLD,
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(pady=(24, 8))

        ctk.CTkLabel(
            self,
            text=self._gap["description"],
            text_color=colors["text_primary"],
            wraplength=560,
            justify="center",
        ).pack(pady=(0, 12), padx=30)

        ctk.CTkLabel(
            self,
            text=self._impact_text(simulation),
            text_color=colors["text_secondary"],
            wraplength=560,
            justify="center",
            font=ctk.CTkFont(size=12),
        ).pack(pady=(0, 16), padx=30)

        if runbook["sequence_warning"]:
            self._build_warning(colors, runbook["sequence_warning"])

        self._build_steps(colors, runbook)

        button_row = ctk.CTkFrame(self, fg_color="transparent")
        button_row.pack(pady=(0, 20))

        ctk.CTkButton(
            button_row,
            text=t("Not Now"),
            fg_color=colors["card_bg"],
            text_color=colors["text_primary"],
            hover_color=theme.GOLD_HOVER,
            command=self._on_done,
            width=140,
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            button_row,
            text=t("I Completed This"),
            fg_color=theme.GOLD,
            text_color="#1A1A1A",
            hover_color=theme.GOLD_HOVER,
            command=self._mark_done,
            width=180,
        ).pack(side="left", padx=6)

    def _impact_text(self, simulation: dict) -> str:
        if simulation["after_exposed"] < simulation["before_exposed"]:
            before, after = simulation["before_exposed"], simulation["after_exposed"]
            return t(
                "Right now, your single riskiest point exposes {before} "
                "account{before_s}. Completing this drops that to {after} "
                "account{after_s}."
            ).format(
                before=before,
                before_s="" if before == 1 else "s",
                after=after,
                after_s="" if after == 1 else "s",
            )
        return t(
            "Completing this closes a real gap, though it isn't your single "
            "riskiest point right now."
        )

    def _build_warning(self, colors: dict, warning: str) -> None:
        row = ctk.CTkFrame(
            self, fg_color=colors["card_bg"], border_color=theme.ALERT, border_width=1, corner_radius=8,
        )
        row.pack(fill="x", padx=30, pady=(0, 12))
        ctk.CTkLabel(
            row,
            text=f"⚠ {warning}",
            text_color=theme.ALERT,
            wraplength=520,
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=14, pady=10)

    def _build_steps(self, colors: dict, runbook: dict) -> None:
        steps_card = ctk.CTkFrame(self, fg_color=colors["card_bg"], corner_radius=10)
        steps_card.pack(fill="both", expand=True, padx=30, pady=(0, 12))

        if not runbook["steps"]:
            ctk.CTkLabel(
                steps_card,
                text=t("No specific steps yet — use this account's own security settings."),
                text_color=colors["text_secondary"],
                wraplength=520,
            ).pack(pady=16, padx=16)
        else:
            for index, step in enumerate(runbook["steps"], start=1):
                ctk.CTkLabel(
                    steps_card,
                    text=f"{index}. {step}",
                    text_color=colors["text_primary"],
                    wraplength=520,
                    justify="left",
                    anchor="w",
                ).pack(fill="x", padx=16, pady=(10 if index == 1 else 4, 4))

        if runbook["deep_link"]:
            ctk.CTkButton(
                steps_card,
                text=t("Open Settings Page"),
                fg_color=colors["bg"],
                text_color=theme.GOLD,
                hover_color=colors["card_bg"],
                command=lambda: webbrowser.open(runbook["deep_link"]),
            ).pack(pady=(4, 12))

    def _mark_done(self) -> None:
        remediation.mark_gap_resolved(graph.get_graph(), self._gap)
        self._on_done()
