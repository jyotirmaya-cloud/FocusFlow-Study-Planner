"""Reusable widgets: StatCard and DatePicker."""
import calendar
from datetime import date, datetime

import customtkinter as ctk

from config import (
    BG, CARD, TEXT, MUTED, BORDER, HOVER, HOVER_BLUE, BLUE, NAVY, WHITE
)
from helpers import set_window_icon


class StatCard(ctk.CTkFrame):
    """A small card with a title and one big number."""

    def __init__(self, parent, title, color):
        super().__init__(parent, fg_color=CARD, corner_radius=14)

        ctk.CTkLabel(
            self, text=title, font=("Arial", 13), text_color=MUTED
        ).pack(anchor="w", padx=16, pady=(14, 5))

        self.value_label = ctk.CTkLabel(
            self, text="0", font=("Arial", 28, "bold"), text_color=color
        )
        self.value_label.pack(anchor="w", padx=16, pady=(0, 14))

    def set(self, text):
        self.value_label.configure(text=text)


class DatePicker(ctk.CTkFrame):
    """A button that opens a calendar popup with month and year navigation."""

    MONTHS = list(calendar.month_name)[1:]
    WEEKDAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]

    def __init__(self, parent, value=""):
        super().__init__(parent, fg_color="transparent")
        self.selected = date.today()
        if value:
            try:
                self.selected = datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError:
                pass

        self.button = ctk.CTkButton(
            self, text="📅  " + self.get(), width=150, height=36,
            fg_color=CARD, hover_color=HOVER, text_color=TEXT,
            border_width=1, border_color=BORDER, anchor="w",
            command=self.open_popup
        )
        self.button.pack()

    def get(self):
        return self.selected.isoformat()

    def set_date(self, new_date):
        self.selected = new_date
        self.button.configure(text="📅  " + self.get())

    def open_popup(self):
        top = self.winfo_toplevel()
        popup = ctk.CTkToplevel(top)
        popup.title("Select date")
        popup.resizable(False, False)
        popup.configure(fg_color=BG)
        popup.transient(top)
        set_window_icon(popup)
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height() + 4
        popup.geometry(f"330x390+{x}+{y}")

        today = date.today()
        min_year = today.year - 5
        max_year = today.year + 10
        years = [str(y) for y in range(min_year, max_year + 1)]
        view = {
            "year": min(max(self.selected.year, min_year), max_year),
            "month": self.selected.month,
        }

        header = ctk.CTkFrame(popup, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(12, 6))
        grid = ctk.CTkFrame(popup, fg_color=CARD, corner_radius=10)
        grid.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        def close():
            popup.destroy()
            # Give focus back to a parent dialog if there is one
            if isinstance(top, ctk.CTkToplevel):
                try:
                    top.grab_set()
                except Exception:
                    pass

        def pick_day(day):
            self.set_date(date(view["year"], view["month"], day))
            close()

        def render():
            for widget in grid.winfo_children():
                widget.destroy()

            for col, name in enumerate(self.WEEKDAYS):
                ctk.CTkLabel(
                    grid, text=name, width=40,
                    text_color=MUTED, font=("Arial", 11, "bold")
                ).grid(row=0, column=col, padx=2, pady=(10, 4))

            weeks = calendar.monthcalendar(view["year"], view["month"])
            for row, week in enumerate(weeks, start=1):
                for col, day in enumerate(week):
                    if day == 0:
                        continue
                    current = date(view["year"], view["month"], day)
                    is_selected = current == self.selected
                    ctk.CTkButton(
                        grid, text=str(day), width=40, height=34,
                        corner_radius=8,
                        fg_color=BLUE if is_selected else "transparent",
                        text_color=WHITE if is_selected else TEXT,
                        hover_color=HOVER_BLUE,
                        border_width=1 if (current == today and not is_selected) else 0,
                        border_color=BLUE,
                        command=lambda d=day: pick_day(d)
                    ).grid(row=row, column=col, padx=2, pady=2)

        def set_view(year=None, month=None):
            if year is not None:
                view["year"] = year
            if month is not None:
                view["month"] = month
            month_menu.set(self.MONTHS[view["month"] - 1])
            year_menu.set(str(view["year"]))
            render()

        def step(delta):
            month = view["month"] + delta
            year = view["year"]
            if month < 1:
                month, year = 12, year - 1
            elif month > 12:
                month, year = 1, year + 1
            if year < min_year or year > max_year:
                return
            set_view(year, month)

        ctk.CTkButton(
            header, text="◀", width=34, height=30, fg_color=NAVY,
            command=lambda: step(-1)
        ).pack(side="left")

        month_menu = ctk.CTkOptionMenu(
            header, values=self.MONTHS, width=115, height=30,
            command=lambda v: set_view(month=self.MONTHS.index(v) + 1)
        )
        month_menu.pack(side="left", padx=(8, 4))

        year_menu = ctk.CTkOptionMenu(
            header, values=years, width=80, height=30,
            command=lambda v: set_view(year=int(v))
        )
        year_menu.pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            header, text="▶", width=34, height=30, fg_color=NAVY,
            command=lambda: step(1)
        ).pack(side="left")

        set_view()

        def grab():
            try:
                popup.grab_set()
                popup.focus_set()
            except Exception:
                pass

        popup.after(150, grab)
