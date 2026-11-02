"""The Reports page: how your focus time is split across subjects."""
from datetime import date, timedelta

import customtkinter as ctk

from config import CARD, TEXT, MUTED, BLUE, GREEN, ORANGE, NAVY_ACTIVE
from helpers import format_duration
from widgets import StatCard

BAR_COLORS = [BLUE, GREEN, ORANGE, "#8B5CF6", "#EC4899", "#14B8A6"]


class ReportsPage(ctk.CTkScrollableFrame):
    PERIODS = {"Last 7 days": 7, "Last 30 days": 30, "All time": None}
    MAX_ROWS = 10

    def __init__(self, parent, db):
        super().__init__(parent, fg_color="transparent")
        self.db = db

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 4))

        ctk.CTkLabel(
            header, text="Study Reports",
            font=("Arial", 29, "bold"), text_color=TEXT
        ).pack(side="left")

        self.period_menu = ctk.CTkOptionMenu(
            header, values=list(self.PERIODS.keys()), width=140, height=34,
            command=lambda _: self.refresh()
        )
        self.period_menu.set("Last 7 days")
        self.period_menu.pack(side="right")

        ctk.CTkLabel(
            self, text="See where your focus time goes.",
            font=("Arial", 13), text_color=MUTED
        ).pack(anchor="w", pady=(0, 20))

        cards = ctk.CTkFrame(self, fg_color="transparent")
        cards.pack(fill="x", pady=(0, 20))
        self.total_card = self._card(cards, "Total Focus Time", BLUE)
        self.sessions_card = self._card(cards, "Sessions", GREEN)
        self.subjects_card = self._card(cards, "Subjects Studied", NAVY_ACTIVE)

        panel = ctk.CTkFrame(self, fg_color=CARD, corner_radius=12)
        panel.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            panel, text="Focus Time by Subject",
            font=("Arial", 16, "bold"), text_color=TEXT
        ).pack(anchor="w", padx=16, pady=(12, 4))

        self.rows_frame = ctk.CTkFrame(panel, fg_color="transparent")
        self.rows_frame.pack(fill="x", padx=16, pady=(0, 12))

    def _card(self, row, title, color):
        card = StatCard(row, title, color)
        card.pack(side="left", fill="x", expand=True, padx=(0, 12))
        return card

    # ----- page hooks ------------------------------------------------
    def on_show(self):
        self.refresh()

    def apply_theme(self):
        pass   # every widget here uses theme-aware colors

    # ----- data ------------------------------------------------------
    def refresh(self):
        days = self.PERIODS[self.period_menu.get()]
        since = None if days is None else date.today() - timedelta(days=days - 1)
        data = self.db.focus_by_subject(since)

        total_seconds = sum(seconds for _, _, seconds in data)
        total_sessions = sum(count for _, count, _ in data)
        self.total_card.set(format_duration(total_seconds))
        self.sessions_card.set(str(total_sessions))
        self.subjects_card.set(str(len(data)))

        for widget in self.rows_frame.winfo_children():
            widget.destroy()

        if not data:
            ctk.CTkLabel(
                self.rows_frame,
                text="No focus sessions in this period yet.\n"
                     "Finish a session on the Study Planner page to see your report.",
                font=("Arial", 13), text_color=MUTED, justify="left"
            ).pack(anchor="w", pady=10)
            return

        longest = max(seconds for _, _, seconds in data) or 1
        for index, (name, count, seconds) in enumerate(data[:self.MAX_ROWS]):
            share = round(seconds / total_seconds * 100) if total_seconds else 0
            self._add_row(
                name, count, seconds, share,
                fraction=seconds / longest,
                color=BAR_COLORS[index % len(BAR_COLORS)],
            )

        extra = len(data) - self.MAX_ROWS
        if extra > 0:
            ctk.CTkLabel(
                self.rows_frame, text=f"+ {extra} more subject{'s' if extra != 1 else ''}",
                font=("Arial", 12), text_color=MUTED
            ).pack(anchor="w", pady=(6, 0))

    def _add_row(self, name, count, seconds, share, fraction, color):
        item = ctk.CTkFrame(self.rows_frame, fg_color="transparent")
        item.pack(fill="x", pady=6)

        top = ctk.CTkFrame(item, fg_color="transparent")
        top.pack(fill="x")

        shown = name if len(name) <= 40 else name[:39] + "…"
        ctk.CTkLabel(
            top, text=shown, font=("Arial", 14, "bold"),
            text_color=TEXT, anchor="w"
        ).pack(side="left")
        ctk.CTkLabel(
            top, text=f"{format_duration(seconds)}  ·  {share}%",
            font=("Arial", 13), text_color=MUTED
        ).pack(side="right")

        bar = ctk.CTkProgressBar(item, height=10, progress_color=color)
        bar.pack(fill="x", pady=(4, 2))
        bar.set(fraction)

        ctk.CTkLabel(
            item, text=f"{count} session{'s' if count != 1 else ''}",
            font=("Arial", 11), text_color=MUTED, anchor="w"
        ).pack(anchor="w")
