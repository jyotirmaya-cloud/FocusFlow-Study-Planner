"""Shared colors, constants and theme helpers for FocusFlow."""
import os
import sys
import customtkinter as ctk

APP_NAME = "FocusFlow | Smart Study Planner"



def resource_path(name):
    """Path to a bundled file (works from source and inside a PyInstaller .exe)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def _data_dir():
    """Where the database lives.

    From source: next to the code, wherever you launch the app from.
    As an .exe: the FocusFlow folder inside %APPDATA% (the exe's own
    folder is temporary, so it can't hold your data).
    """
    if getattr(sys, "frozen", False):
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        folder = os.path.join(base, "FocusFlow")
        os.makedirs(folder, exist_ok=True)
        return folder
    return os.path.dirname(os.path.abspath(__file__))


DB_PATH = os.path.join(_data_dir(), "focusflow.db")
ICON_PATH = resource_path("icon.ico")

# Theme-aware colors are (light, dark) pairs. customtkinter switches them
# automatically when the appearance mode changes.
BG = ("#F4F6FB", "#0F172A")
CARD = ("#FFFFFF", "#1E293B")
CARD_ALT = ("#F8FAFC", "#273449")
TEXT = ("#1E293B", "#E2E8F0")
MUTED = ("#64748B", "#94A3B8")
BORDER = ("#CBD5E1", "#475569")
HOVER = ("#E8EEF9", "#334155")
HOVER_BLUE = ("#BFDBFE", "#1E3A8A")
TABLE_HEADER = ("#E8EEF9", "#334155")
TABLE_SELECT = ("#BFDBFE", "#1D4ED8")
GRID_LINE = ("#E2E8F0", "#334155")
EMPTY_BAR = ("#E2E8F0", "#334155")

# Same in both modes
NAVY = "#172554"
NAVY_ACTIVE = "#1E3A8A"
BLUE = "#3B82F6"
GREEN = "#16A34A"
RED = "#DC2626"
ORANGE = "#F59E0B"
WHITE = "#FFFFFF"
SIDEBAR_TEXT = "#CBD5E1"

PRIORITIES = ["High", "Medium", "Low"]
PRIORITY_LABELS = {"High": "▲ High", "Medium": "● Medium", "Low": "▼ Low"}


def pick(color):
    """Resolve a (light, dark) pair to a single color for widgets that
    customtkinter doesn't manage itself (ttk Treeview, plain canvas)."""
    if isinstance(color, (tuple, list)):
        return color[1] if ctk.get_appearance_mode() == "Dark" else color[0]
    return color
