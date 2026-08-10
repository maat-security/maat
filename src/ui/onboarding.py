"""Onboarding frame: entry point for the three optional data-source paths.

Import Password Manager and Answer Questions are real here. Connect
Integration is still a "coming soon" placeholder — no API client exists
yet for GitHub or any other provider.
"""

import queue
import sys
import threading
import tkinter.filedialog as filedialog
from pathlib import Path

import customtkinter as ctk

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import graph  # noqa: E402
import theme  # noqa: E402
from i18n import t  # noqa: E402
from importers import bitwarden, csv_generic, keepass, onepassword  # noqa: E402

IMPORTER_BY_LABEL = {
    "1Password (.1pux)": onepassword,
    "Bitwarden (.json)": bitwarden,
    "KeePass XML (2.x)": keepass,
    "Generic CSV": csv_generic,
}

EXTENSION_HINTS = {
    ".1pux": "1Password (.1pux)",
    ".json": "Bitwarden (.json)",
    ".xml": "KeePass XML (2.x)",
    ".csv": "Generic CSV",
}


class OnboardingFrame(ctk.CTkFrame):
    """The three-path onboarding entry point, shown whenever the graph
    doesn't have enough data yet to be worth showing as a dashboard."""

    def __init__(self, master, on_import_done, on_answer_questions):
        colors = theme.current()
        super().__init__(master, fg_color=colors["bg"])
        self._on_import_done = on_import_done
        self._on_answer_questions = on_answer_questions
        self._build(colors)

    def _build(self, colors) -> None:
        ctk.CTkLabel(
            self,
            text=t("Maat"),
            text_color=theme.GOLD,
            font=ctk.CTkFont(size=26, weight="bold"),
        ).pack(pady=(30, 4))

        ctk.CTkLabel(
            self,
            text=t("Add your first accounts to see where you stand."),
            text_color=colors["text_secondary"],
        ).pack(pady=(0, 30))

        panels_container = ctk.CTkFrame(self, fg_color="transparent")
        panels_container.pack(pady=10, padx=20, fill="both", expand=True)
        panels_container.grid_columnconfigure((0, 1, 2), weight=1)
        panels_container.grid_rowconfigure(0, weight=1)

        panels = (
            (t("Import Password Manager"), t("Bring in your account inventory"), self._start_import),
            (t("Answer Questions"), t("Map how you authenticate and recover access"), self._on_answer_questions),
            (t("Connect Integration"), t("Let Maat read your configuration directly"), self._show_coming_soon),
        )
        for index, (label, description, action) in enumerate(panels):
            self._build_panel(panels_container, colors, label, description, action, column=index)

        self._status_label = ctk.CTkLabel(self, text="", text_color=colors["text_secondary"])
        self._status_label.pack(pady=(0, 16))

    def _build_panel(self, container, colors, label, description, action, column) -> None:
        panel = ctk.CTkFrame(
            container,
            fg_color=colors["card_bg"],
            border_color=theme.GOLD,
            border_width=1,
            corner_radius=10,
        )
        panel.grid(row=0, column=column, padx=12, pady=10, sticky="nsew")

        ctk.CTkLabel(
            panel,
            text=label,
            text_color=colors["text_primary"],
            font=ctk.CTkFont(size=15, weight="bold"),
            wraplength=220,
        ).pack(pady=(24, 8), padx=16)

        ctk.CTkLabel(
            panel,
            text=description,
            text_color=colors["text_secondary"],
            wraplength=220,
        ).pack(pady=(0, 20), padx=16)

        ctk.CTkButton(
            panel,
            text=t("Start"),
            fg_color=theme.GOLD,
            text_color="#1A1A1A",
            hover_color=theme.GOLD_HOVER,
            command=action,
        ).pack(pady=(0, 24), padx=16)

    def _show_coming_soon(self) -> None:
        colors = theme.current()
        dialog = ctk.CTkToplevel(self)
        dialog.title(t("Coming Soon"))
        dialog.geometry("360x160")
        dialog.configure(fg_color=colors["bg"])
        dialog.resizable(False, False)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text=t("Connect Integration"),
            text_color=theme.GOLD,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(pady=(24, 8))

        ctk.CTkLabel(
            dialog,
            text=t("This is coming in a future phase."),
            text_color=colors["text_primary"],
        ).pack(pady=(0, 20))

        ctk.CTkButton(
            dialog,
            text=t("Close"),
            fg_color=theme.GOLD,
            text_color="#1A1A1A",
            hover_color=theme.GOLD_HOVER,
            command=dialog.destroy,
        ).pack()

    def _start_import(self) -> None:
        filepath = filedialog.askopenfilename(
            title=t("Select your password manager export"),
            filetypes=[
                (t("Supported exports"), "*.1pux *.json *.xml *.csv"),
                (t("All files"), "*.*"),
            ],
        )
        if not filepath:
            return
        self._show_format_picker(filepath)

    def _show_format_picker(self, filepath: str) -> None:
        colors = theme.current()
        suffix = Path(filepath).suffix.lower()
        default_label = EXTENSION_HINTS.get(suffix, "1Password (.1pux)")

        dialog = ctk.CTkToplevel(self)
        dialog.title(t("Confirm Format"))
        dialog.geometry("420x240")
        dialog.configure(fg_color=colors["bg"])
        dialog.resizable(False, False)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text=Path(filepath).name,
            text_color=colors["text_primary"],
            font=ctk.CTkFont(size=13, weight="bold"),
            wraplength=380,
        ).pack(pady=(20, 4), padx=16)

        ctk.CTkLabel(
            dialog,
            text=t("Which password manager is this export from?"),
            text_color=colors["text_secondary"],
            wraplength=380,
        ).pack(pady=(0, 12), padx=16)

        selector = ctk.CTkSegmentedButton(
            dialog,
            values=list(IMPORTER_BY_LABEL.keys()),
            selected_color=theme.GOLD,
            selected_hover_color=theme.GOLD_HOVER,
        )
        selector.set(default_label)
        selector.pack(pady=(0, 16))

        error_label = ctk.CTkLabel(dialog, text="", text_color=theme.ALERT, wraplength=380)
        error_label.pack(pady=(0, 4))

        import_button = ctk.CTkButton(
            dialog,
            text=t("Import"),
            fg_color=theme.GOLD,
            text_color="#1A1A1A",
            hover_color=theme.GOLD_HOVER,
        )
        import_button.pack()

        def run_import() -> None:
            importer = IMPORTER_BY_LABEL[selector.get()]
            import_button.configure(state="disabled", text=t("Importing…"))
            error_label.configure(text="")

            # Parsing now includes a Have I Been Pwned lookup per
            # password (see importers/_shared.py.compute_breach_flags),
            # which means real network round trips — run it off the Tk
            # main thread so the UI doesn't freeze. The worker thread
            # never touches a Tk widget or calls self.after() itself —
            # Tk widgets (and, on some Tcl builds, even after() from a
            # non-main thread) aren't safe to touch off the main thread.
            # It only puts its result on a thread-safe queue.Queue; the
            # main thread polls that queue via its own self.after() loop.
            result_queue = queue.Queue()

            def worker() -> None:
                try:
                    accounts = importer.parse(filepath)
                except ValueError as exc:
                    result_queue.put(("error", str(exc)))
                    return
                result_queue.put(("success", accounts))

            def poll_result() -> None:
                try:
                    kind, payload = result_queue.get_nowait()
                except queue.Empty:
                    self.after(50, poll_result)
                    return
                if kind == "error":
                    _on_import_error(payload)
                else:
                    _on_import_success(payload)

            threading.Thread(target=worker, daemon=True).start()
            self.after(50, poll_result)

        def _on_import_error(message: str) -> None:
            import_button.configure(state="normal", text=t("Import"))
            error_label.configure(text=message)

        def _on_import_success(accounts: list) -> None:
            added = _add_accounts_to_graph(accounts)
            failed_checks = sum(1 for a in accounts if a.get("breach_check_failed"))
            dialog.destroy()

            message = t("Imported {n} account{s}.").format(n=added, s="" if added == 1 else "s")
            if failed_checks:
                message += " " + t(
                    "Could not check {n} for known breaches — no connection to "
                    "Have I Been Pwned."
                ).format(n=failed_checks)
            self._status_label.configure(text=message)
            self._on_import_done()

        import_button.configure(command=run_import)


def _add_accounts_to_graph(accounts: list) -> int:
    """Add each parsed account as an Identity node with a single Factor
    node representing its strongest known sign-in method. Returns how
    many accounts were added."""
    added = 0
    for account in accounts:
        identity_id = graph.make_node_id(account["name"])
        graph.add_node(
            identity_id,
            "Identity",
            {
                "display_name": account["name"],
                "criticality": graph.DEFAULT_CRITICALITY,
                "confidence": "declared",
                "url": account.get("url"),
                "password_reused": account.get("password_reused", False),
                "password_age_days": account.get("password_age_days"),
                "breached": account.get("breached", False),
            },
        )

        if account.get("has_passkey"):
            factor_kind = "passkey"
        elif account.get("has_totp"):
            factor_kind = "totp"
        else:
            factor_kind = "password"

        factor_id = f"{identity_id}::factor"
        graph.add_node(factor_id, "Factor", {"kind": factor_kind, "confidence": "declared"})
        graph.add_edge(factor_id, identity_id, "AUTHENTICATES")
        added += 1

    return added
