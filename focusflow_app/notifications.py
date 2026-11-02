"""Deadline reminders: a pop-up summary of overdue and due-soon tasks.

Pure logic (group_reminders, should_notify) is kept separate from the
pop-up window (ReminderDialog) and the scheduler (ReminderManager).
"""
from datetime import date, datetime

import customtkinter as ctk

from config import BG, CARD, TEXT, MUTED, BLUE, RED, ORANGE
from helpers import play_sound, set_window_icon, relative_due

CHECK_INTERVAL_MS = 60 * 60 * 1000        # remind again every hour
RETRY_WHILE_FOCUSING_MS = 5 * 60 * 1000   # never interrupt a focus session
MAX_SHOWN = 8


def group_reminders(rows, today=None):
    """Sort (id, subject, deadline, priority) rows into overdue/today/tomorrow."""
    today = today or date.today()
    groups = {"overdue": [], "today": [], "tomorrow": []}
    for _task_id, subject, deadline, priority in rows:
        try:
            due = datetime.strptime(deadline, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue
        days = (due - today).days
        item = (subject, deadline, priority)
        if days < 0:
            groups["overdue"].append(item)
        elif days == 0:
            groups["today"].append(item)
        elif days == 1:
            groups["tomorrow"].append(item)
    return groups


def should_notify(groups, startup):
    """At startup, mention anything due by tomorrow. For the hourly repeats,
    only nag about tasks that are overdue or due today."""
    urgent = bool(groups["overdue"] or groups["today"])
    if startup:
        return urgent or bool(groups["tomorrow"])
    return urgent


class ReminderDialog(ctk.CTkToplevel):
    SECTIONS = [
        ("overdue", "Overdue", RED),
        ("today", "Due today", ORANGE),
        ("tomorrow", "Due tomorrow", BLUE),
    ]

    def __init__(self, parent, groups, on_open, on_silence, on_closed):
        super().__init__(parent)
        self.on_open = on_open
        self.on_silence = on_silence
        self.on_closed = on_closed
        self._closed = False

        total = sum(len(items) for items in groups.values())
        sections = sum(1 for items in groups.values() if items)
        shown = min(total, MAX_SHOWN)

        self.title("FocusFlow Reminder")
        self.geometry(f"440x{190 + shown * 30 + sections * 34 + (24 if total > shown else 0)}")
        self.resizable(False, False)
        self.configure(fg_color=BG)
        set_window_icon(self)
        self.protocol("WM_DELETE_WINDOW", self.close)

        ctk.CTkLabel(
            self, text="⏰  Deadline reminder",
            font=("Arial", 20, "bold"), text_color=TEXT
        ).pack(anchor="w", padx=24, pady=(20, 2))

        verb = "needs" if total == 1 else "need"
        ctk.CTkLabel(
            self, text=f"{total} task{'s' if total != 1 else ''} {verb} your attention",
            font=("Arial", 13), text_color=MUTED
        ).pack(anchor="w", padx=24, pady=(0, 12))

        body = ctk.CTkFrame(self, fg_color=CARD, corner_radius=12)
        body.pack(fill="both", expand=True, padx=24)

        count = 0
        for key, label, color in self.SECTIONS:
            items = groups[key]
            if not items:
                continue
            ctk.CTkLabel(
                body, text=label, font=("Arial", 13, "bold"), text_color=color
            ).pack(anchor="w", padx=14, pady=(10, 2))

            for subject, deadline, _priority in items:
                if count >= MAX_SHOWN:
                    break
                count += 1
                name = subject if len(subject) <= 34 else subject[:33] + "…"
                row = ctk.CTkFrame(body, fg_color="transparent")
                row.pack(fill="x", padx=14, pady=1)
                ctk.CTkLabel(
                    row, text=f"•  {name}", font=("Arial", 13),
                    text_color=TEXT, anchor="w"
                ).pack(side="left")
                text, text_color = relative_due(deadline)
                ctk.CTkLabel(
                    row, text=text, font=("Arial", 12), text_color=text_color
                ).pack(side="right")

        if total > count:
            ctk.CTkLabel(
                body, text=f"+ {total - count} more", font=("Arial", 12),
                text_color=MUTED
            ).pack(anchor="w", padx=14, pady=(6, 0))
        ctk.CTkFrame(body, fg_color="transparent", height=8).pack()

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(side="bottom", fill="x", padx=24, pady=18)

        ctk.CTkButton(
            buttons, text="Open Manage Tasks", command=self._open,
            fg_color=BLUE, width=150
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            buttons, text="Remind me later", command=self.close,
            fg_color=MUTED, width=120
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            buttons, text="Dismiss today", command=self._silence,
            fg_color=MUTED, width=100
        ).pack(side="left")

        self.after(100, self._raise)

    def _raise(self):
        try:
            self.lift()
            self.attributes("-topmost", True)
            self.after(500, lambda: self.attributes("-topmost", False))
        except Exception:
            pass   # closed already, or the platform doesn't support it

    def _open(self):
        self.on_open()
        self.close()

    def _silence(self):
        self.on_silence()
        self.close()

    def close(self):
        if self._closed:
            return
        self._closed = True
        self.destroy()
        self.on_closed()


class ReminderManager:
    """Checks for due tasks at startup and then once an hour."""

    def __init__(self, app, db):
        self.app = app
        self.db = db
        self.enabled = db.get_int("reminders_on", 1) == 1
        self.dialog = None
        self.silenced_on = None   # date the user chose "Dismiss today"
        self._job = None

    # ----- control ---------------------------------------------------
    def start(self):
        """Run the first check a moment after the window appears."""
        self.cancel()
        if self.enabled:
            self._job = self.app.after(1500, lambda: self.check(startup=True))

    def set_enabled(self, enabled):
        self.enabled = enabled
        self.cancel()
        if enabled:
            self.silenced_on = None
            self.check(startup=True)

    def cancel(self):
        if self._job is not None:
            self.app.after_cancel(self._job)
            self._job = None

    # ----- the check -------------------------------------------------
    def check(self, startup=False):
        self._job = None
        if not self.enabled:
            return

        planner = self.app.pages["planner"]
        focusing = planner.timer.running and not planner.timer.is_break
        delay = RETRY_WHILE_FOCUSING_MS if focusing else CHECK_INTERVAL_MS
        self._job = self.app.after(delay, self.check)
        if focusing:
            return

        if self.dialog is not None or self.silenced_on == date.today():
            return

        groups = group_reminders(self.db.reminder_candidates())
        if not should_notify(groups, startup):
            return

        play_sound(self.app)
        self.dialog = ReminderDialog(
            self.app, groups,
            on_open=self._open_tasks,
            on_silence=self._silence_today,
            on_closed=self._dialog_closed,
        )

    def _open_tasks(self):
        self.app.show_page("tasks")
        try:
            self.app.deiconify()
            self.app.lift()
        except Exception:
            pass

    def _silence_today(self):
        self.silenced_on = date.today()

    def _dialog_closed(self):
        self.dialog = None
