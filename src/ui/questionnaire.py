"""Questionnaire frame: the four-question-per-account guided flow.

Structured as an explicit step index over a fixed question list — a
state machine over answers, not an input loop — per the desktop
distribution design note (PRD section 11): the same answers dict works
regardless of which renderer eventually drives it.

Every question is skippable and the account can be finished early —
repetition across many partial answers is what reveals recovery
cycles, so a partial pass is still useful. No single question blocks
the rest, per design principle 5.
"""

import sys
from pathlib import Path

import customtkinter as ctk

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import graph  # noqa: E402
import theme  # noqa: E402
from i18n import t  # noqa: E402

QUESTIONS = ("how_sign_in", "how_recover", "how_recovery_protected", "where_backups_live")


def _factor_kind_labels() -> dict:
    """Built fresh on every call (not cached at import time) so a
    language switch made earlier in the session is respected here."""
    return {
        "password": t("Password"),
        "sms": t("SMS"),
        "push": t("Push notification"),
        "totp": t("TOTP app"),
        "biometric": t("Biometric"),
        "passkey": t("Passkey"),
        "hardware_key": t("Hardware security key"),
    }


def _recovery_kind_labels() -> dict:
    return {
        "email": t("Backup email"),
        "phone": t("Phone number"),
        "recovery_codes": t("Recovery codes"),
        "other": t("Something else"),
    }


class QuestionnaireFrame(ctk.CTkFrame):
    """Guided, skippable, four-question flow for one account at a time."""

    def __init__(self, master, on_done):
        colors = theme.current()
        super().__init__(master, fg_color=colors["bg"])
        self._on_done = on_done
        self._step = 0
        self._answers = {}
        self._account_name = ""
        self._criticality = graph.DEFAULT_CRITICALITY
        self._build()

    def _build(self) -> None:
        colors = theme.current()
        self.configure(fg_color=colors["bg"])
        for child in self.winfo_children():
            child.destroy()

        ctk.CTkLabel(
            self,
            text=t("Answer Questions"),
            text_color=theme.GOLD,
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(pady=(24, 12))

        account_row = ctk.CTkFrame(self, fg_color="transparent")
        account_row.pack(pady=(0, 4))

        self._name_entry = ctk.CTkEntry(
            account_row, placeholder_text=t("Account name (e.g. Gmail)"), width=280,
        )
        self._name_entry.insert(0, self._account_name)
        self._name_entry.pack(side="left", padx=(0, 8))

        self._criticality_menu = ctk.CTkOptionMenu(
            account_row,
            values=[str(n) for n in range(1, 6)],
            fg_color=theme.GOLD,
            button_color=theme.GOLD,
            button_hover_color=theme.GOLD_HOVER,
            text_color="#1A1A1A",
        )
        self._criticality_menu.set(str(self._criticality))
        self._criticality_menu.pack(side="left")

        ctk.CTkLabel(
            self,
            text=t("How critical is this account? 5 = most critical (financial, primary email)"),
            text_color=colors["text_secondary"],
            font=ctk.CTkFont(size=11),
        ).pack(pady=(0, 16))

        self._question_container = ctk.CTkFrame(self, fg_color=colors["card_bg"], corner_radius=10)
        self._question_container.pack(padx=40, pady=(0, 12), fill="both", expand=True)

        self._render_question()

        nav_row = ctk.CTkFrame(self, fg_color="transparent")
        nav_row.pack(pady=(0, 8))

        ctk.CTkButton(
            nav_row,
            text=t("Back"),
            fg_color=colors["card_bg"],
            text_color=colors["text_primary"],
            hover_color=theme.GOLD_HOVER,
            command=self._go_back,
            width=100,
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            nav_row,
            text=t("Skip"),
            fg_color=colors["card_bg"],
            text_color=colors["text_primary"],
            hover_color=theme.GOLD_HOVER,
            command=self._skip,
            width=100,
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            nav_row,
            text=t("Next") if self._step < len(QUESTIONS) - 1 else t("Finish"),
            fg_color=theme.GOLD,
            text_color="#1A1A1A",
            hover_color=theme.GOLD_HOVER,
            command=self._go_next,
            width=100,
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            self,
            text=t("Finish and Return"),
            fg_color="transparent",
            text_color=colors["text_secondary"],
            hover_color=colors["card_bg"],
            command=self._finish_account,
        ).pack(pady=(0, 16))

    def _render_question(self) -> None:
        colors = theme.current()
        for child in self._question_container.winfo_children():
            child.destroy()

        question_key = QUESTIONS[self._step]
        prompt, widget_builder = self._question_spec(question_key, colors)

        ctk.CTkLabel(
            self._question_container,
            text=f"{self._step + 1}/{len(QUESTIONS)}",
            text_color=colors["text_secondary"],
            font=ctk.CTkFont(size=11),
        ).pack(pady=(16, 4))

        ctk.CTkLabel(
            self._question_container,
            text=prompt,
            text_color=colors["text_primary"],
            font=ctk.CTkFont(size=15, weight="bold"),
            wraplength=460,
            justify="center",
        ).pack(pady=(0, 16), padx=20)

        widget_builder(self._question_container)

    def _question_spec(self, question_key: str, colors: dict):
        if question_key == "how_sign_in":
            def build(container):
                labels = list(_factor_kind_labels().values())
                self._factor_menu = ctk.CTkOptionMenu(
                    container, values=labels, fg_color=theme.GOLD,
                    button_color=theme.GOLD, button_hover_color=theme.GOLD_HOVER,
                    text_color="#1A1A1A",
                )
                current = _factor_kind_labels().get(self._answers.get("how_sign_in"), labels[0])
                self._factor_menu.set(current)
                self._factor_menu.pack(pady=(0, 20))
            return t("How do you normally sign in to this account?"), build

        if question_key == "how_recover":
            def build(container):
                labels = list(_recovery_kind_labels().values())
                self._recovery_kind_menu = ctk.CTkOptionMenu(
                    container, values=labels, fg_color=theme.GOLD,
                    button_color=theme.GOLD, button_hover_color=theme.GOLD_HOVER,
                    text_color="#1A1A1A",
                )
                current = _recovery_kind_labels().get(self._answers.get("how_recover_kind"), labels[0])
                self._recovery_kind_menu.set(current)
                self._recovery_kind_menu.pack(pady=(0, 8))

                self._recovery_entry = ctk.CTkEntry(
                    container,
                    placeholder_text=t("Optional detail (e.g. which phone number)"),
                    width=320,
                )
                if self._answers.get("how_recover_detail"):
                    self._recovery_entry.insert(0, self._answers["how_recover_detail"])
                self._recovery_entry.pack(pady=(0, 20))
            return t("If you lost that, how would you get back in?"), build

        if question_key == "how_recovery_protected":
            def build(container):
                labels = list(_factor_kind_labels().values())
                self._recovery_factor_menu = ctk.CTkOptionMenu(
                    container, values=labels, fg_color=theme.GOLD,
                    button_color=theme.GOLD, button_hover_color=theme.GOLD_HOVER,
                    text_color="#1A1A1A",
                )
                current = _factor_kind_labels().get(self._answers.get("how_recovery_protected"), labels[0])
                self._recovery_factor_menu.set(current)
                self._recovery_factor_menu.pack(pady=(0, 20))
            return t("How is that recovery method itself protected?"), build

        def build(container):
            self._backup_entry = ctk.CTkEntry(
                container,
                placeholder_text=t("e.g. printed in a drawer, in my password manager"),
                width=380,
            )
            if self._answers.get("where_backups_live"):
                self._backup_entry.insert(0, self._answers["where_backups_live"])
            self._backup_entry.pack(pady=(0, 8))
            ctk.CTkLabel(
                container,
                text=t("Describe where — never enter the actual codes."),
                text_color=colors["text_secondary"],
                font=ctk.CTkFont(size=11),
            ).pack(pady=(0, 20))
        return t("Where do backup codes or your second-factor backup live?"), build

    def _capture_current_answer(self) -> None:
        question_key = QUESTIONS[self._step]

        if question_key == "how_sign_in":
            reverse = {v: k for k, v in _factor_kind_labels().items()}
            self._answers["how_sign_in"] = reverse.get(self._factor_menu.get())
        elif question_key == "how_recover":
            reverse = {v: k for k, v in _recovery_kind_labels().items()}
            self._answers["how_recover_kind"] = reverse.get(self._recovery_kind_menu.get())
            detail = self._recovery_entry.get().strip()
            if detail:
                self._answers["how_recover_detail"] = detail
        elif question_key == "how_recovery_protected":
            reverse = {v: k for k, v in _factor_kind_labels().items()}
            self._answers["how_recovery_protected"] = reverse.get(self._recovery_factor_menu.get())
        elif question_key == "where_backups_live":
            detail = self._backup_entry.get().strip()
            if detail:
                self._answers["where_backups_live"] = detail

    def _go_next(self) -> None:
        self._capture_current_answer()
        if self._step >= len(QUESTIONS) - 1:
            self._finish_account()
            return
        self._step += 1
        self._refresh_step()

    def _go_back(self) -> None:
        if self._step == 0:
            return
        self._capture_current_answer()
        self._step -= 1
        self._refresh_step()

    def _skip(self) -> None:
        self._answers.pop(QUESTIONS[self._step], None)
        if self._step >= len(QUESTIONS) - 1:
            self._finish_account()
            return
        self._step += 1
        self._refresh_step()

    def _refresh_step(self) -> None:
        self._account_name = self._name_entry.get().strip()
        self._criticality = int(self._criticality_menu.get())
        self._build()

    def _finish_account(self) -> None:
        self._capture_current_answer()
        self._account_name = self._name_entry.get().strip()
        self._criticality = int(self._criticality_menu.get())

        if self._account_name:
            _commit_account_to_graph(self._account_name, self._criticality, self._answers)

        self._account_name = ""
        self._criticality = graph.DEFAULT_CRITICALITY
        self._answers = {}
        self._step = 0
        self._on_done()


def _commit_account_to_graph(name: str, criticality: int, answers: dict) -> None:
    identity_id = graph.make_node_id(name)
    graph.add_node(
        identity_id,
        "Identity",
        {"display_name": name, "criticality": criticality, "confidence": "declared"},
    )

    factor_id = None
    if answers.get("how_sign_in"):
        factor_id = f"{identity_id}::factor"
        graph.add_node(factor_id, "Factor", {"kind": answers["how_sign_in"], "confidence": "declared"})
        graph.add_edge(factor_id, identity_id, "AUTHENTICATES")

    recovery_id = None
    if answers.get("how_recover_kind"):
        recovery_id = f"{identity_id}::recovery"
        graph.add_node(
            recovery_id,
            "RecoveryChannel",
            {
                "kind": answers["how_recover_kind"],
                "detail": answers.get("how_recover_detail"),
                "confidence": "declared",
            },
        )
        graph.add_edge(recovery_id, identity_id, "RECOVERS")

    if answers.get("how_recovery_protected") and recovery_id:
        recovery_factor_id = f"{identity_id}::recovery_factor"
        graph.add_node(
            recovery_factor_id,
            "Factor",
            {"kind": answers["how_recovery_protected"], "confidence": "declared"},
        )
        graph.add_edge(recovery_factor_id, recovery_id, "AUTHENTICATES")

    if answers.get("where_backups_live") and factor_id:
        store_id = f"{identity_id}::backup_store"
        graph.add_node(
            store_id, "Store", {"location": answers["where_backups_live"], "confidence": "declared"}
        )
        graph.add_edge(store_id, factor_id, "STORES")
