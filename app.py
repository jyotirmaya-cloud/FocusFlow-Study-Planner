"""The main window: sidebar, page switching and theme toggle."""
import customtkinter as ctk

from config import (
    APP_NAME, DB_PATH, BG, NAVY, NAVY_ACTIVE, WHITE, SIDEBAR_TEXT
)
from database import Database
from helpers import set_window_icon
from dashboard import DashboardPage
from tasks import TasksPage
from planner import PlannerPage
from reports import ReportsPage
from notifications import ReminderManager


class App(ctk.CTk):
    def __init__(self):
        db = Database(DB_PATH)

        # Appearance must be set before any widget is created
        dark = db.get_int("dark_mode", 0) == 1
        ctk.set_appearance_mode("dark" if dark else "light")
        ctk.set_default_color_theme("blue")

        super().__init__()
        self.db = db

        self.title(APP_NAME)
        self.geometry("1050x700")
        self.minsize(900, 600)
        self.configure(fg_color=BG)
        set_window_icon(self)

        self.sidebar = ctk.CTkFrame(self, width=200, fg_color=NAVY, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.container = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self.container.pack(side="left", fill="both", expand=True, padx=24, pady=20)

        self.pages = {
            "dashboard": DashboardPage(self.container, db),
            "tasks": TasksPage(self.container, db),
            "planner": PlannerPage(self.container, db),
            "reports": ReportsPage(self.container, db),
        }
        self.nav_buttons = {}
        self.current_page = None
        self.reminders = ReminderManager(self, db)

        self._build_sidebar(dark)
        self.show_page("dashboard")
        self.reminders.start()

        # Keyboard: Ctrl+1 to Ctrl+4 switch pages
        pages_in_order = ["dashboard", "tasks", "planner", "reports"]
        for number, key in enumerate(pages_in_order, start=1):
            self.bind(f"<Control-Key-{number}>", lambda e, k=key: self.show_page(k))

        self.protocol("WM_DELETE_WINDOW", self.close)

    # ----- sidebar ---------------------------------------------------
    def _build_sidebar(self, dark):
        ctk.CTkLabel(
            self.sidebar, text="FocusFlow",
            font=("Arial", 25, "bold"), text_color=WHITE
        ).pack(pady=(30, 8))

        ctk.CTkLabel(
            self.sidebar, text="SMART STUDY PLANNER",
            font=("Arial", 10), text_color=SIDEBAR_TEXT
        ).pack(pady=(0, 35))

        for key, label in [
            ("dashboard", "▣   Dashboard"),
            ("tasks", "✓   Manage Tasks"),
            ("planner", "◷   Study Planner"),
            ("reports", "▤   Study Report"),
        ]:
            button = ctk.CTkButton(
                self.sidebar, text=label, anchor="w",
                font=("Arial", 15, "bold"),
                fg_color="transparent", hover_color=NAVY_ACTIVE,
                text_color=SIDEBAR_TEXT, corner_radius=8, height=42,
                command=lambda k=key: self.show_page(k)
            )
            button.pack(fill="x", padx=14, pady=4)
            self.nav_buttons[key] = button

        # Bottom items: the first one packed sits lowest
        ctk.CTkLabel(
            self.sidebar, text="Build your future,\none task at a time.",
            font=("Arial", 12), text_color=SIDEBAR_TEXT, justify="left"
        ).pack(side="bottom", pady=(0, 25))

        self.theme_switch = ctk.CTkSwitch(
            self.sidebar, text="Dark mode", text_color=SIDEBAR_TEXT,
            command=self.toggle_theme
        )
        self.theme_switch.pack(side="bottom", pady=(0, 20))
        if dark:
            self.theme_switch.select()

        self.reminder_switch = ctk.CTkSwitch(
            self.sidebar, text="Reminders", text_color=SIDEBAR_TEXT,
            command=self.toggle_reminders
        )
        self.reminder_switch.pack(side="bottom", pady=(0, 10))
        if self.reminders.enabled:
            self.reminder_switch.select()

    # ----- behaviour -------------------------------------------------
    def show_page(self, name):
        if self.current_page:
            self.pages[self.current_page].pack_forget()

        page = self.pages[name]
        page.pack(fill="both", expand=True)
        page.on_show()
        self.current_page = name

        for key, button in self.nav_buttons.items():
            if key == name:
                button.configure(fg_color=NAVY_ACTIVE, text_color=WHITE)
            else:
                button.configure(fg_color="transparent", text_color=SIDEBAR_TEXT)

    def toggle_theme(self):
        dark = bool(self.theme_switch.get())
        ctk.set_appearance_mode("dark" if dark else "light")
        self.db.set_setting("dark_mode", 1 if dark else 0)
        for page in self.pages.values():
            page.apply_theme()

    def toggle_reminders(self):
        enabled = bool(self.reminder_switch.get())
        self.db.set_setting("reminders_on", 1 if enabled else 0)
        self.reminders.set_enabled(enabled)

    def close(self):
        self.reminders.cancel()
        self.pages["planner"].timer.cancel()
        self.db.close()
        self.destroy()
