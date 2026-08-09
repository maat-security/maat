"""Dashboard frame: posture score, prioritized actions, alerts.

Phase 0: stub only — a placeholder frame with no real content. The
Phase 0 shell in main.py has its own inline dashboard; this frame is
where that content moves once scoring and gap-prioritization exist.
"""

import customtkinter as ctk


class DashboardFrame(ctk.CTkFrame):
    """Placeholder for the future posture dashboard."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        ctk.CTkLabel(self, text="DashboardFrame").pack(pady=20)
