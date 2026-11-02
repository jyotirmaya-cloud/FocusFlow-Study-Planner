"""Small pure helpers: dates, formatting, sound."""
import os
from datetime import datetime, date

from config import RED, ORANGE, MUTED, ICON_PATH


def parse_date(text):
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def validate_date(text):
    return parse_date(text) is not None


def deadline_status(deadline, completed):
    """Return (status text, row tag) for a task."""
    if completed:
        return "Completed", "done"
    due = parse_date(deadline)
    if due is None:
        return "Pending", ""
    days = (due - date.today()).days
    if days < 0:
        return "Overdue", "overdue"
    if days == 0:
        return "Due today", "soon"
    if days == 1:
        return "Due tomorrow", "soon"
    return "Pending", ""


def relative_due(deadline):
    """Return (text, color) describing how soon a deadline is."""
    due = parse_date(deadline)
    if due is None:
        return deadline, MUTED
    days = (due - date.today()).days
    if days < 0:
        return f"{-days}d overdue", RED
    if days == 0:
        return "Today", ORANGE
    if days == 1:
        return "Tomorrow", ORANGE
    return f"In {days} days", MUTED


def format_clock(seconds):
    minutes, secs = divmod(seconds, 60)
    return f"{minutes:02d}:{secs:02d}"


def format_duration(seconds):
    minutes = seconds // 60
    if minutes >= 60:
        return f"{minutes // 60}h {minutes % 60}m"
    return f"{minutes}m"


def set_window_icon(window):
    """Give a window the FocusFlow icon.

    customtkinter swaps in its own icon about 200 ms after a window opens,
    so we wait a little longer and then set ours.
    """
    if not os.path.exists(ICON_PATH):
        return

    def apply():
        try:
            window.iconbitmap(ICON_PATH)
        except Exception:
            pass   # iconbitmap only works on Windows

    window.after(300, apply)


def play_sound(root):
    try:
        import winsound  # Windows only
        for freq in (880, 988, 1175):
            winsound.Beep(freq, 200)
    except Exception:
        root.bell()


def bring_to_front(root):
    try:
        root.deiconify()
        root.lift()
        root.attributes("-topmost", True)
        root.after(600, lambda: root.attributes("-topmost", False))
        root.focus_force()
    except Exception:
        pass
