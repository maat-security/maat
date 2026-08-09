"""Questionnaire frame: the four-question-per-account guided flow.

Phase 0: stub only.
"""

import customtkinter as ctk


class QuestionnaireFrame(ctk.CTkFrame):
    """Placeholder for the future guided questionnaire."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        ctk.CTkLabel(self, text="QuestionnaireFrame").pack(pady=20)
