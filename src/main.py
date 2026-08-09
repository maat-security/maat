"""Maat desktop application entry point.

Window shell, the unified welcome screen (intro + language and
appearance controls + vault creation/unlock), and navigation between
onboarding, the guided questionnaire, and the posture dashboard. The
dashboard and onboarding frames themselves live in ui/ — this module
only owns which one is on screen.
"""

import sys
from pathlib import Path

import customtkinter as ctk

# Windows applies its own DPI scaling on top of CustomTkinter's internal
# widget scaling unless this is disabled, which stretches widget content
# past the raw pixel window size on any display above 100% scaling (very
# common on Windows laptops). Must be called before any CTk window exists.
ctk.deactivate_automatic_dpi_awareness()

# Ensure sibling modules (store.py, i18n.py, ...) resolve regardless of
# whether this file is launched directly or via PyInstaller's bootloader.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import graph  # noqa: E402  (import must follow the sys.path insert above)
import store  # noqa: E402
import theme  # noqa: E402
from i18n import t, get_locale, set_locale, LOCALES  # noqa: E402
from ui.dashboard import DashboardFrame  # noqa: E402
from ui.onboarding import OnboardingFrame  # noqa: E402
from ui.questionnaire import QuestionnaireFrame  # noqa: E402

WINDOW_TITLE = "Maat — Your identity, in balance"

# NIST 800-63B guidance: length matters, forced complexity (uppercase /
# digit / symbol requirements) does not — and actively pushes people
# toward predictable patterns. This app enforces a minimum length only.
MIN_PASSPHRASE_LENGTH = 12


class MaatApp(ctk.CTk):
    """Root application window. Owns navigation between the welcome
    screen and the main dashboard shell."""

    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("dark")

        self.title(t(WINDOW_TITLE))
        self.geometry("900x650")
        self.resizable(False, False)
        self.configure(fg_color=theme.current()["bg"])

        self._current_frame = None
        self._show_welcome_screen()

    def _swap_frame(self, frame: ctk.CTkFrame) -> None:
        if self._current_frame is not None:
            self._current_frame.destroy()
        self._current_frame = frame
        self._current_frame.pack(fill="both", expand=True)

    def _show_welcome_screen(self) -> None:
        self._swap_frame(WelcomeFrame(self, on_ready=self._show_main_screen))

    def _show_main_screen(self) -> None:
        """Show the dashboard if the graph has anything in it yet,
        otherwise the onboarding entry point. Re-evaluated every time
        this is called, so finishing an import or a questionnaire pass
        naturally flips from one to the other."""
        if graph.get_graph().number_of_nodes() > 0:
            self._swap_frame(DashboardFrame(self, on_add_data=self._show_onboarding))
        else:
            self._swap_frame(self._build_onboarding_frame())

    def _show_onboarding(self) -> None:
        self._swap_frame(self._build_onboarding_frame())

    def _build_onboarding_frame(self) -> OnboardingFrame:
        return OnboardingFrame(
            self,
            on_import_done=self._show_main_screen,
            on_answer_questions=self._show_questionnaire,
        )

    def _show_questionnaire(self) -> None:
        self._swap_frame(QuestionnaireFrame(self, on_done=self._show_main_screen))


class WelcomeFrame(ctk.CTkFrame):
    """The app's first screen: a brief product intro, language and
    appearance controls, and — depending on whether a vault already
    exists — either the vault creation form or the unlock form.
    """

    def __init__(self, master, on_ready):
        colors = theme.current()
        super().__init__(master, fg_color=colors["bg"])
        self._on_ready = on_ready
        self._build()

    def _build(self) -> None:
        colors = theme.current()
        self.configure(fg_color=colors["bg"])

        self._build_top_bar(colors)
        self._build_intro(colors)

        if store.store_exists():
            self._build_unlock_section(colors)
        else:
            self._build_create_section(colors)

    def _rebuild(self) -> None:
        """Tear down and recreate all content — used after a language or
        appearance change, since CTk widget text/colors are static once set."""
        for child in self.winfo_children():
            child.destroy()
        self._build()

    def _build_top_bar(self, colors) -> None:
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=20, pady=(16, 0))

        language_selector = ctk.CTkSegmentedButton(
            top_bar,
            values=["EN", "ES"],
            selected_color=theme.GOLD,
            selected_hover_color=theme.GOLD_HOVER,
            command=self._on_locale_selected,
        )
        language_selector.set(get_locale().upper())
        language_selector.pack(side="left")

        is_dark = ctk.get_appearance_mode() == "Dark"
        appearance_button = ctk.CTkButton(
            top_bar,
            text=t("☀️ Light") if is_dark else t("🌙 Dark"),
            fg_color=colors["card_bg"],
            text_color=colors["text_primary"],
            hover_color=theme.GOLD_HOVER,
            command=self._on_appearance_toggle,
            width=110,
        )
        appearance_button.pack(side="right")

    def _build_intro(self, colors) -> None:
        ctk.CTkLabel(
            self,
            text="🪶 " + t("Maat"),
            text_color=theme.GOLD,
            font=ctk.CTkFont(size=28, weight="bold"),
        ).pack(pady=(24, 4))

        ctk.CTkLabel(
            self,
            text=t("Your identity, in balance."),
            text_color=colors["text_secondary"],
        ).pack(pady=(0, 16))

        ctk.CTkLabel(
            self,
            text=t(
                "Maat maps your digital identity as a dependency graph — every "
                "account, device, and recovery channel — and shows you which "
                "single point of failure puts the most at risk. Local-first. "
                "No account, no telemetry, no data leaving this device."
            ),
            text_color=colors["text_primary"],
            wraplength=580,
            justify="center",
        ).pack(pady=(0, 20), padx=40)

    def _build_create_section(self, colors) -> None:
        ctk.CTkLabel(
            self,
            text=t("Create Your Vault"),
            text_color=colors["text_primary"],
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(pady=(4, 6))

        ctk.CTkLabel(
            self,
            text=t(
                "Choose a passphrase. It never leaves this device and "
                "cannot be recovered if lost."
            ),
            text_color=colors["text_secondary"],
            wraplength=500,
        ).pack(pady=(0, 16))

        self._passphrase_entry = ctk.CTkEntry(
            self, placeholder_text=t("Passphrase"), show="*", width=320,
        )
        self._passphrase_entry.pack(pady=6)

        self._confirm_entry = ctk.CTkEntry(
            self, placeholder_text=t("Confirm Passphrase"), show="*", width=320,
        )
        self._confirm_entry.pack(pady=6)
        self._confirm_entry.bind("<Return>", lambda _event: self._on_create_clicked())

        ctk.CTkLabel(
            self,
            text=t(
                "At least {n} characters. Longer is better than complex — "
                "a plain phrase beats P@ssw0rd!"
            ).format(n=MIN_PASSPHRASE_LENGTH),
            text_color=colors["text_secondary"],
            font=ctk.CTkFont(size=11),
            wraplength=400,
        ).pack(pady=(4, 0))

        self._error_label = ctk.CTkLabel(self, text="", text_color=theme.ALERT)
        self._error_label.pack(pady=(8, 0))

        ctk.CTkButton(
            self,
            text=t("Create"),
            fg_color=theme.GOLD,
            text_color="#1A1A1A",
            hover_color=theme.GOLD_HOVER,
            command=self._on_create_clicked,
            width=320,
        ).pack(pady=(14, 0))

    def _on_create_clicked(self) -> None:
        passphrase = self._passphrase_entry.get()
        confirm = self._confirm_entry.get()

        if not passphrase:
            self._error_label.configure(text=t("Passphrase cannot be empty."))
            return

        if len(passphrase) < MIN_PASSPHRASE_LENGTH:
            self._error_label.configure(
                text=t("Passphrase must be at least {n} characters.").format(
                    n=MIN_PASSPHRASE_LENGTH
                )
            )
            return

        if passphrase != confirm:
            self._error_label.configure(text=t("Passphrases do not match."))
            return

        try:
            store.init_store(passphrase)
        except store.StoreError as exc:
            self._error_label.configure(text=t(str(exc)))
            return

        self._on_ready()

    def _build_unlock_section(self, colors) -> None:
        ctk.CTkLabel(
            self,
            text=t("Unlock Your Vault"),
            text_color=colors["text_primary"],
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(pady=(4, 6))

        ctk.CTkLabel(
            self,
            text=t("Your vault is encrypted at rest. Enter your passphrase to continue."),
            text_color=colors["text_secondary"],
            wraplength=500,
        ).pack(pady=(0, 16))

        self._passphrase_entry = ctk.CTkEntry(
            self, placeholder_text=t("Passphrase"), show="*", width=320,
        )
        self._passphrase_entry.pack(pady=6)
        self._passphrase_entry.bind("<Return>", lambda _event: self._on_unlock_clicked())

        self._error_label = ctk.CTkLabel(self, text="", text_color=theme.ALERT)
        self._error_label.pack(pady=(8, 0))

        ctk.CTkButton(
            self,
            text=t("Unlock"),
            fg_color=theme.GOLD,
            text_color="#1A1A1A",
            hover_color=theme.GOLD_HOVER,
            command=self._on_unlock_clicked,
            width=320,
        ).pack(pady=(14, 0))

    def _on_unlock_clicked(self) -> None:
        passphrase = self._passphrase_entry.get()

        try:
            store.unlock_store(passphrase)
        except store.StoreError as exc:
            self._error_label.configure(text=t(str(exc)))
            return

        self._on_ready()

    def _on_locale_selected(self, value: str) -> None:
        set_locale(value.lower())
        self._rebuild()

    def _on_appearance_toggle(self) -> None:
        new_mode = "Light" if ctk.get_appearance_mode() == "Dark" else "Dark"
        ctk.set_appearance_mode(new_mode)
        self.master.configure(fg_color=theme.current()["bg"])
        self._rebuild()


def main() -> None:
    app = MaatApp()
    app.mainloop()


if __name__ == "__main__":
    main()
