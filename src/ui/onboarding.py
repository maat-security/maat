"""Onboarding frame: entry point for the three optional data-source paths.

Phase 0: stub only.
"""

import customtkinter as ctk


class OnboardingFrame(ctk.CTkFrame):
    """Placeholder for the future onboarding flow."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        ctk.CTkLabel(self, text="OnboardingFrame").pack(pady=20)
