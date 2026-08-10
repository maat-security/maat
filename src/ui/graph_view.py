"""Graph view frame: a visual exploration tool for the dependency
graph, reachable from the Dashboard — never the app's main screen (per
the product's own design decision that consequences, not the graph
itself, are the primary interface).

Draws nodes and edges on a plain tkinter Canvas (CustomTkinter has no
canvas widget of its own) using graph_layout.py's pure-Python
force-directed layout — no numpy dependency. Clicking a node shows the
same consequence-language blast-radius text the Dashboard already
uses, via metrics.translate_to_consequences() — this screen never
invents new metric language of its own.
"""

import sys
import tkinter as tk
from pathlib import Path

import customtkinter as ctk

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import graph  # noqa: E402
import graph_layout  # noqa: E402
import metrics  # noqa: E402
import theme  # noqa: E402
from i18n import t  # noqa: E402

CANVAS_WIDTH = 760
CANVAS_HEIGHT = 420
NODE_RADIUS = 22

NODE_TYPE_COLORS = {
    "Identity": theme.GOLD,
    "Factor": "#5B8DEF",
    "Device": "#4CAF50",
    "RecoveryChannel": "#9C6ADE",
    "Store": "#26A69A",
    "Provider": "#FF8A65",
    "Person": "#EC7FA9",
}
FALLBACK_NODE_COLOR = "#888888"


def _legend_labels() -> dict:
    """Built fresh on every call, not cached at import time, so a
    language switch is respected — same convention as
    ui/dashboard.py._component_labels()."""
    return {
        "Identity": t("Account"),
        "Factor": t("Sign-in Method"),
        "Device": t("Device"),
        "RecoveryChannel": t("Recovery Method"),
        "Store": t("Password Store"),
        "Provider": t("Provider"),
        "Person": t("Person"),
    }


class GraphViewFrame(ctk.CTkFrame):
    """Exploration screen: renders the live graph and lets the user
    click a node to see its blast radius in consequence language."""

    def __init__(self, master, on_back):
        colors = theme.current()
        super().__init__(master, fg_color=colors["bg"])
        self._on_back = on_back
        self._node_items = {}  # canvas item id -> node_id
        self._build(colors)

    def _build(self, colors: dict) -> None:
        self._build_header(colors)

        current_graph = graph.get_graph()
        if current_graph.number_of_nodes() == 0:
            self._build_empty_state(colors)
        else:
            self._build_canvas(colors)
            self._build_legend(colors)
            self._draw_graph(current_graph)

        self._detail_label = ctk.CTkLabel(
            self,
            text=t("Click a node to see what depends on it."),
            text_color=colors["text_secondary"],
            wraplength=680,
            justify="center",
        )
        self._detail_label.pack(pady=(8, 12), padx=20)

    def _build_header(self, colors: dict) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 8))

        ctk.CTkButton(
            header,
            text=t("Back to Dashboard"),
            fg_color=colors["card_bg"],
            text_color=colors["text_primary"],
            hover_color=theme.GOLD_HOVER,
            command=self._on_back,
            width=160,
        ).pack(side="left")

        ctk.CTkLabel(
            header,
            text=t("Graph View"),
            text_color=theme.GOLD,
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(side="left", expand=True)

    def _build_empty_state(self, colors: dict) -> None:
        ctk.CTkLabel(
            self,
            text=t("Your graph is empty. Add a few accounts to see your first result."),
            text_color=colors["text_primary"],
            wraplength=520,
            justify="center",
        ).pack(pady=60, padx=40, expand=True)

    def _build_canvas(self, colors: dict) -> None:
        canvas_frame = ctk.CTkFrame(self, fg_color=colors["card_bg"], corner_radius=10)
        canvas_frame.pack(padx=20, pady=(0, 8))

        self._graph_canvas = tk.Canvas(
            canvas_frame,
            width=CANVAS_WIDTH,
            height=CANVAS_HEIGHT,
            bg=colors["card_bg"],
            highlightthickness=0,
        )
        self._graph_canvas.pack(padx=8, pady=8)
        self._graph_canvas.bind("<Button-1>", self._on_canvas_click)

    def _build_legend(self, colors: dict) -> None:
        legend = ctk.CTkFrame(self, fg_color="transparent")
        legend.pack(pady=(0, 4))

        labels = _legend_labels()
        for node_type, color in NODE_TYPE_COLORS.items():
            item = ctk.CTkFrame(legend, fg_color="transparent")
            item.pack(side="left", padx=8)
            swatch = ctk.CTkLabel(item, text="●", text_color=color, font=ctk.CTkFont(size=14))
            swatch.pack(side="left")
            ctk.CTkLabel(
                item, text=labels[node_type], text_color=colors["text_secondary"], font=ctk.CTkFont(size=11),
            ).pack(side="left", padx=(2, 0))

    def _draw_graph(self, current_graph) -> None:
        positions = graph_layout.compute_layout(
            current_graph, width=CANVAS_WIDTH - 2 * NODE_RADIUS, height=CANVAS_HEIGHT - 2 * NODE_RADIUS,
        )
        # Shift everything inward so no node center falls closer to an
        # edge than its own radius, keeping circles fully on-canvas.
        positions = {n: (x + NODE_RADIUS, y + NODE_RADIUS) for n, (x, y) in positions.items()}

        for source, target in current_graph.edges():
            x1, y1 = positions[source]
            x2, y2 = positions[target]
            self._graph_canvas.create_line(x1, y1, x2, y2, fill="#999999", width=1.5, arrow=tk.LAST)

        for node_id, data in current_graph.nodes(data=True):
            x, y = positions[node_id]
            color = NODE_TYPE_COLORS.get(data.get("type"), FALLBACK_NODE_COLOR)
            item_id = self._graph_canvas.create_oval(
                x - NODE_RADIUS, y - NODE_RADIUS, x + NODE_RADIUS, y + NODE_RADIUS,
                fill=color, outline="", tags="node",
            )
            self._node_items[item_id] = node_id

            label = str(data.get("display_name") or node_id)
            if len(label) > 12:
                label = label[:11] + "…"
            self._graph_canvas.create_text(x, y + NODE_RADIUS + 10, text=label, fill="#888888", font=("", 9))

    def _on_canvas_click(self, event) -> None:
        clicked = self._graph_canvas.find_closest(event.x, event.y)
        if not clicked:
            return
        item_id = clicked[0]
        node_id = self._node_items.get(item_id)
        if node_id is None:
            return
        self._show_node_impact(node_id)

    def _show_node_impact(self, node_id: str) -> None:
        exposed = graph.get_blast_radius(node_id)
        text = metrics.translate_to_consequences("blast_radius", node_id, exposed)
        self._detail_label.configure(text=text)
