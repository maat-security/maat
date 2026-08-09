"""Color tokens for Maat's dark and light appearance modes.

Gold accent and the red alert color are fixed regardless of mode per
the product's palette. Background, card, and text colors flip between
the dark and light token sets below.
"""

import customtkinter as ctk

GOLD = "#C9A84C"
GOLD_HOVER = "#B8952F"
ALERT = "#C0392B"

COLORS = {
    "dark": {
        "bg": "#1A1A1A",
        "card_bg": "#2D2D2D",
        "text_primary": "#F5F5F5",
        "text_secondary": "#555555",
    },
    "light": {
        "bg": "#F5F5F5",
        "card_bg": "#FFFFFF",
        "text_primary": "#1A1A1A",
        "text_secondary": "#555555",
    },
}


def current() -> dict:
    """Return the color token dict for the active CustomTkinter appearance mode."""
    mode = ctk.get_appearance_mode().lower()
    return COLORS.get(mode, COLORS["dark"])
