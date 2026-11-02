"""The Study Planner page: Pomodoro timer linked to your tasks."""
from tkinter import messagebox

import customtkinter as ctk

from config import CARD, TEXT, MUTED, BLUE, GREEN, ORANGE
from helpers import format_clock, format_duration, play_sound, bring_to_front
from timer import PomodoroTimer


class PlannerPage(ctk.CTkFrame):
    FREE_LABEL = "No task (free focus)"

    def __init__(self, parent, db):
        super().__init__(parent, fg_color="transparent")
        self.db = db
        self.task_map = {self.FREE_LABEL: None}
        self.session_task = None   # (task_id, name) locked in at session start

        focus_min = db.get_int("focus_minutes", 25)
        break_min = db.get_int("break_minutes", 5)

        ctk.CTkLabel(
            self, text="Study Planner",
            font=("Arial", 29, "bold"), text_color=TEXT
        ).pack(anchor="w", pady=(0, 12))

        self._build_picker()
        self._build_timer_card(break_min)
        self._build_settings(focus_min, break_min)

        self.timer = PomodoroTimer(
            self, focus_minutes=focus_min, break_minutes=break_min,
            on_tick=self._show_time,
            on_focus_done=self._focus_done,
            on_break_done=self._break_done,
        )
        self._show_time(self.timer.remaining)

    # ----- layout ----------------------------------------------------
    def _build_picker(self):
        card = ctk.CTkFrame(self, fg_color=CARD, corner_radius=12)
        card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            card, text="What are you studying?",
            font=("Arial", 16, "bold"), text_color=TEXT
        ).pack(anchor="w", padx=16, pady=(12, 6))

        self.task_menu = ctk.CTkOptionMenu(
            card, values=[self.FREE_LABEL], height=36, dynamic_resizing=False
        )
        self.task_menu.set(self.FREE_LABEL)
        self.task_menu.pack(fill="x", padx=16, pady=(0, 14))

    def _build_timer_card(self, break_min):
        card = ctk.CTkFrame(self, fg_color=CARD, corner_radius=12)
        card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            card, text="Pomodoro Study Timer",
            font=("Arial", 18, "bold"), text_color=TEXT
        ).pack(pady=(14, 0))

        self.time_label = ctk.CTkLabel(
            card, text="25:00", font=("Arial", 52, "bold"), text_color=BLUE
        )
        self.time_label.pack(pady=(6, 0))

        self.status_label = ctk.CTkLabel(
            card, text="Focus Session", font=("Arial", 14), text_color=MUTED
        )
        self.status_label.pack(pady=2)

        buttons = ctk.CTkFrame(card, fg_color="transparent")
        buttons.pack(pady=(8, 4))

        ctk.CTkButton(
            buttons, text="Start", command=self.start, width=90, fg_color=GREEN
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            buttons, text="Pause", command=self.pause, width=90, fg_color=ORANGE
        ).pack(side="left", padx=5)
        self.break_btn = ctk.CTkButton(
            buttons, text=f"{break_min}-Min Break",
            command=self.start_break, width=110, fg_color=BLUE
        )
        self.break_btn.pack(side="left", padx=5)
        ctk.CTkButton(
            buttons, text="Reset", command=self.reset, width=90, fg_color=MUTED
        ).pack(side="left", padx=5)

        self.today_label = ctk.CTkLabel(
            card, text="Today: 0 sessions · 0m focus",
            font=("Arial", 12), text_color=MUTED
        )
        self.today_label.pack(pady=(2, 14))

    def _build_settings(self, focus_min, break_min):
        card = ctk.CTkFrame(self, fg_color=CARD, corner_radius=12)
        card.pack(fill="x")

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=12)

        ctk.CTkLabel(
            row, text="Focus (min)", text_color=MUTED, font=("Arial", 12)
        ).pack(side="left")
        self.focus_entry = ctk.CTkEntry(row, width=56, height=32, justify="center")
        self.focus_entry.insert(0, str(focus_min))
        self.focus_entry.pack(side="left", padx=(6, 14))

        ctk.CTkLabel(
            row, text="Break (min)", text_color=MUTED, font=("Arial", 12)
        ).pack(side="left")
        self.break_entry = ctk.CTkEntry(row, width=56, height=32, justify="center")
        self.break_entry.insert(0, str(break_min))
        self.break_entry.pack(side="left", padx=(6, 14))

        ctk.CTkButton(
            row, text="Apply", command=self.apply_durations,
            width=70, height=32, fg_color=BLUE
        ).pack(side="left")

        ctk.CTkButton(
            row, text="50 / 10", command=lambda: self._preset(50, 10),
            width=70, height=32, fg_color=MUTED
        ).pack(side="right")
        ctk.CTkButton(
            row, text="25 / 5", command=lambda: self._preset(25, 5),
            width=70, height=32, fg_color=MUTED
        ).pack(side="right", padx=(0, 8))

    # ----- page hooks ------------------------------------------------
    def on_show(self):
        self.refresh_tasks()
        self._update_today_label()

    def apply_theme(self):
        pass   # every widget here uses theme-aware colors

    # ----- task picker -----------------------------------------------
    def refresh_tasks(self):
        """Fill the picker with pending tasks, keeping the current choice."""
        current = self.task_menu.get()
        self.task_map.clear()
        self.task_map[self.FREE_LABEL] = None
        for task_id, subject in self.db.pending_tasks():
            label = subject if subject not in self.task_map else f"{subject} (#{task_id})"
            self.task_map[label] = task_id

        self.task_menu.configure(values=list(self.task_map.keys()))
        self.task_menu.set(current if current in self.task_map else self.FREE_LABEL)

    def _current_selection(self):
        """Return (task_id, task_name) for the picked task, or (None, None)."""
        task_id = self.task_map.get(self.task_menu.get())
        if task_id is None:
            return (None, None)
        row = self.db.get_task(task_id)
        return (task_id, row[0] if row else self.task_menu.get())

    def _clear_session(self):
        self.session_task = None
        self.task_menu.configure(state="normal")

    # ----- display ---------------------------------------------------
    def _show_time(self, remaining):
        self.time_label.configure(text=format_clock(remaining))

    def _status_text(self):
        if self.timer.is_break:
            return "Break Session"
        if self.session_task and self.session_task[1]:
            return f"Focus Session · {self.session_task[1]}"
        return "Focus Session"

    def _update_today_label(self):
        count, seconds = self.db.sessions_today()
        self.today_label.configure(
            text=f"Today: {count} session{'s' if count != 1 else ''} · "
                 f"{format_duration(seconds)} focus"
        )

    # ----- timer controls --------------------------------------------
    def start(self):
        if self.timer.running:
            return
        if self.timer.remaining == 0:
            self._clear_session()
            self.timer.reset()

        # Lock in the chosen task at the start of a fresh focus session
        if not self.timer.is_break and self.session_task is None:
            self.session_task = self._current_selection()
            self.task_menu.configure(state="disabled")

        self.timer.start()
        self.status_label.configure(text=self._status_text())

    def pause(self):
        self.timer.pause()
        self.status_label.configure(text="Timer Paused")

    def reset(self):
        self._clear_session()
        self.timer.reset()
        self.status_label.configure(text=self._status_text())

    def start_break(self):
        self._clear_session()
        self.timer.start_break()
        self.status_label.configure(text=self._status_text())

    # ----- timer callbacks -------------------------------------------
    def _focus_done(self):
        root = self.winfo_toplevel()
        play_sound(root)
        bring_to_front(root)

        task_id, name = self.session_task or (None, None)
        self.db.log_session(task_id, name, self.timer.focus_seconds)
        self._clear_session()
        self._update_today_label()
        self.status_label.configure(text="Session finished!")

        if messagebox.askyesno(
            "FocusFlow",
            f"Great work! Session logged.\n\n"
            f"Start a {self.timer.break_seconds // 60}-minute break?"
        ):
            self.start_break()

    def _break_done(self):
        root = self.winfo_toplevel()
        play_sound(root)
        bring_to_front(root)
        messagebox.showinfo("FocusFlow", "Break is over. Ready to focus again!")
        self.reset()

    # ----- custom durations ------------------------------------------
    def apply_durations(self):
        try:
            focus_min = int(self.focus_entry.get())
            break_min = int(self.break_entry.get())
        except ValueError:
            messagebox.showwarning("Invalid time", "Enter whole numbers of minutes.")
            return

        if not 1 <= focus_min <= 180 or not 1 <= break_min <= 60:
            messagebox.showwarning(
                "Invalid time",
                "Focus must be 1-180 minutes and break must be 1-60 minutes."
            )
            return

        if self.timer.running and not messagebox.askyesno(
            "FocusFlow",
            "Applying new lengths will reset the running timer. Continue?"
        ):
            return

        self.db.set_setting("focus_minutes", focus_min)
        self.db.set_setting("break_minutes", break_min)
        self.break_btn.configure(text=f"{break_min}-Min Break")
        self._clear_session()
        self.timer.set_durations(focus_min, break_min)
        self.status_label.configure(text=self._status_text())

    def _preset(self, focus_min, break_min):
        self.focus_entry.delete(0, "end")
        self.focus_entry.insert(0, str(focus_min))
        self.break_entry.delete(0, "end")
        self.break_entry.insert(0, str(break_min))
        self.apply_durations()
