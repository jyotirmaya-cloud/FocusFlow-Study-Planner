"""The Dashboard page: stats, streak, daily goal, weekly chart, deadlines."""
from datetime import date, timedelta

import customtkinter as ctk

from config import (
    CARD, CARD_ALT, TEXT, MUTED, GRID_LINE, EMPTY_BAR, BLUE, GREEN, RED,
    ORANGE, NAVY_ACTIVE, pick
)
from helpers import deadline_status, relative_due, format_duration
from widgets import StatCard


class DashboardPage(ctk.CTkScrollableFrame):
    def __init__(self, parent, db):
        super().__init__(parent, fg_color="transparent")
        self.db = db

        ctk.CTkLabel(
            self, text="My Dashboard",
            font=("Arial", 29, "bold"), text_color=TEXT
        ).pack(anchor="w")
        ctk.CTkLabel(
            self, text="Plan your learning. Track your progress.",
            font=("Arial", 13), text_color=MUTED
        ).pack(anchor="w", pady=(4, 20))

        row1 = self._row()
        self.total_card = self._card(row1, "Total Tasks", BLUE)
        self.completed_card = self._card(row1, "Completed", GREEN)
        self.pending_card = self._card(row1, "Pending", ORANGE)
        self.overdue_card = self._card(row1, "Overdue", RED)

        row2 = self._row()
        self.focus_today_card = self._card(row2, "Focus Time Today", BLUE)
        self.sessions_today_card = self._card(row2, "Sessions Today", GREEN)
        self.total_focus_card = self._card(row2, "Total Focus Time", NAVY_ACTIVE)
        self.streak_card = self._card(row2, "🔥 Day Streak", ORANGE)

        self._build_progress_and_goal()
        self._build_chart_and_upcoming()

    # ----- layout ----------------------------------------------------
    def _row(self):
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", pady=(0, 20))
        return row

    def _card(self, row, title, color):
        card = StatCard(row, title, color)
        card.pack(side="left", fill="x", expand=True, padx=(0, 12))
        return card

    def _build_progress_and_goal(self):
        row = self._row()

        # Study progress
        progress = ctk.CTkFrame(row, fg_color=CARD, corner_radius=12)
        progress.pack(side="left", fill="both", expand=True, padx=(0, 12))

        ctk.CTkLabel(
            progress, text="Study Progress",
            font=("Arial", 16, "bold"), text_color=TEXT
        ).pack(anchor="w", padx=16, pady=(12, 4))

        self.progress_label = ctk.CTkLabel(
            progress, text="0% completed", font=("Arial", 13), text_color=MUTED
        )
        self.progress_label.pack(anchor="w", padx=16, pady=(0, 8))

        self.progress_bar = ctk.CTkProgressBar(
            progress, height=14, progress_color=GREEN
        )
        self.progress_bar.pack(fill="x", padx=16, pady=(0, 14))
        self.progress_bar.set(0)

        # Daily goal
        goal = ctk.CTkFrame(row, fg_color=CARD, corner_radius=12)
        goal.pack(side="left", fill="both", expand=True)

        header = ctk.CTkFrame(goal, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(12, 4))

        ctk.CTkLabel(
            header, text="Daily Goal",
            font=("Arial", 16, "bold"), text_color=TEXT
        ).pack(side="left")

        self.goal_menu = ctk.CTkOptionMenu(
            header, values=[str(i) for i in range(1, 11)],
            width=64, height=26, command=self._change_goal
        )
        self.goal_menu.set(str(self.db.get_int("daily_goal", 3)))
        self.goal_menu.pack(side="right")

        ctk.CTkLabel(
            header, text="tasks / day", font=("Arial", 11), text_color=MUTED
        ).pack(side="right", padx=(0, 6))

        self.goal_label = ctk.CTkLabel(
            goal, text="0 / 3 tasks completed today",
            font=("Arial", 13), text_color=MUTED
        )
        self.goal_label.pack(anchor="w", padx=16, pady=(0, 8))

        self.goal_bar = ctk.CTkProgressBar(goal, height=14, progress_color=BLUE)
        self.goal_bar.pack(fill="x", padx=16, pady=(0, 14))
        self.goal_bar.set(0)

    def _build_chart_and_upcoming(self):
        lower = ctk.CTkFrame(self, fg_color="transparent")
        lower.pack(fill="x", pady=(0, 10))

        # Upcoming deadlines (packed first so it keeps its width)
        upcoming = ctk.CTkFrame(lower, fg_color=CARD, corner_radius=12, width=290)
        upcoming.pack(side="right", fill="y", padx=(12, 0))
        upcoming.pack_propagate(False)

        ctk.CTkLabel(
            upcoming, text="Upcoming Deadlines",
            font=("Arial", 16, "bold"), text_color=TEXT
        ).pack(anchor="w", padx=16, pady=(12, 6))

        self.upcoming_list = ctk.CTkFrame(upcoming, fg_color="transparent")
        self.upcoming_list.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        # Weekly chart
        chart = ctk.CTkFrame(lower, fg_color=CARD, corner_radius=12)
        chart.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(
            chart, text="Focus Minutes · Last 7 Days",
            font=("Arial", 16, "bold"), text_color=TEXT
        ).pack(anchor="w", padx=16, pady=(12, 0))

        self.chart_canvas = ctk.CTkCanvas(
            chart, height=190, bg=pick(CARD), highlightthickness=0
        )
        self.chart_canvas.pack(fill="x", padx=12, pady=(4, 12))
        self.chart_canvas.bind("<Configure>", lambda e: self.draw_chart())

    # ----- refresh ---------------------------------------------------
    def on_show(self):
        self.refresh()

    def apply_theme(self):
        self.draw_chart()

    def refresh(self):
        rows = self.db.task_deadlines()
        total = len(rows)
        completed = sum(1 for _, done in rows if done)
        overdue = sum(
            1 for deadline, done in rows
            if deadline_status(deadline, done)[1] == "overdue"
        )

        self.total_card.set(str(total))
        self.completed_card.set(str(completed))
        self.pending_card.set(str(total - completed))
        self.overdue_card.set(str(overdue))

        percentage = (completed / total * 100) if total else 0
        self.progress_label.configure(text=f"{percentage:.1f}% completed")
        self.progress_bar.set(percentage / 100)

        count, seconds = self.db.sessions_today()
        self.focus_today_card.set(format_duration(seconds))
        self.sessions_today_card.set(str(count))
        self.total_focus_card.set(format_duration(self.db.total_focus_seconds()))

        streak = self.db.streak()
        self.streak_card.set(f"{streak} day{'s' if streak != 1 else ''}")

        self._update_goal()
        self._update_upcoming()
        self.draw_chart()

    def _change_goal(self, value):
        self.db.set_setting("daily_goal", int(value))
        self._update_goal()

    def _update_goal(self):
        goal = self.db.get_int("daily_goal", 3)
        done = self.db.completed_today()

        text = f"{done} / {goal} tasks completed today"
        if done >= goal:
            text += "  🎉 Goal reached!"
        self.goal_label.configure(text=text)
        self.goal_bar.configure(progress_color=GREEN if done >= goal else BLUE)
        self.goal_bar.set(min(done / goal, 1))

    def _update_upcoming(self):
        for widget in self.upcoming_list.winfo_children():
            widget.destroy()

        rows = self.db.upcoming(limit=3)
        if not rows:
            ctk.CTkLabel(
                self.upcoming_list, text="No upcoming deadlines 🎉",
                font=("Arial", 13), text_color=MUTED
            ).pack(anchor="w", pady=8)
            return

        for subject, deadline in rows:
            text, color = relative_due(deadline)
            name = subject if len(subject) <= 22 else subject[:21] + "…"

            item = ctk.CTkFrame(self.upcoming_list, fg_color=CARD_ALT, corner_radius=8)
            item.pack(fill="x", pady=3)

            ctk.CTkLabel(
                item, text=name, font=("Arial", 13, "bold"),
                text_color=TEXT, anchor="w"
            ).pack(anchor="w", padx=10, pady=(6, 0))
            ctk.CTkLabel(
                item, text=f"{deadline}  ·  {text}",
                font=("Arial", 11), text_color=color, anchor="w"
            ).pack(anchor="w", padx=10, pady=(0, 6))

    def draw_chart(self):
        canvas = self.chart_canvas
        canvas.configure(bg=pick(CARD))
        canvas.delete("all")

        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width < 60 or height < 60:
            return

        today = date.today()
        days = [today - timedelta(days=i) for i in range(6, -1, -1)]
        by_day = self.db.focus_seconds_by_day(days[0])
        values = [by_day.get(d.isoformat(), 0) // 60 for d in days]
        top_value = max(max(values), 30)

        pad_x, pad_top, pad_bottom = 16, 24, 26
        chart_h = height - pad_top - pad_bottom
        slot = (width - 2 * pad_x) / 7
        bar_w = slot * 0.5
        base_y = height - pad_bottom

        canvas.create_line(
            pad_x, base_y, width - pad_x, base_y, fill=pick(GRID_LINE)
        )

        for i, (day, value) in enumerate(zip(days, values)):
            x0 = pad_x + i * slot + (slot - bar_w) / 2
            x1 = x0 + bar_w
            bar_h = max(chart_h * value / top_value, 3)

            if value == 0:
                color = pick(EMPTY_BAR)
            else:
                color = GREEN if day == today else BLUE

            canvas.create_rectangle(
                x0, base_y - bar_h, x1, base_y, fill=color, outline=""
            )
            if value > 0:
                canvas.create_text(
                    (x0 + x1) / 2, base_y - bar_h - 10, text=f"{value}m",
                    fill=pick(TEXT), font=("Arial", 9, "bold")
                )
            canvas.create_text(
                (x0 + x1) / 2, base_y + 12, text=day.strftime("%a"),
                fill=pick(MUTED), font=("Arial", 9)
            )
