"""The Manage Tasks page and the Edit Task dialog."""
import csv
import tkinter as tk
from datetime import date
from tkinter import ttk, messagebox, filedialog

import customtkinter as ctk

from config import (
    BG, CARD, TEXT, MUTED, TABLE_HEADER, TABLE_SELECT, PRIORITIES,
    PRIORITY_LABELS, BLUE, GREEN, RED, pick
)
from helpers import deadline_status, validate_date, set_window_icon
from recurrence import REPEAT_CHOICES, repeat_key, repeat_label
from widgets import DatePicker

# Row colors per appearance mode: (background, foreground)
TAG_PALETTE = {
    "overdue": {"Light": ("#FEE2E2", "#B91C1C"), "Dark": ("#7F1D1D", "#FECACA")},
    "soon": {"Light": ("#FEF3C7", "#B45309"), "Dark": ("#78350F", "#FDE68A")},
    "done": {"Light": ("#FFFFFF", "#94A3B8"), "Dark": ("#1E293B", "#64748B")},
}


def _safe_cell(text):
    """Stop spreadsheets from running a task name like '=1+1' as a formula."""
    if text and text[0] in "=+-@\t\r":
        return "'" + text
    return text


class EditTaskDialog(ctk.CTkToplevel):
    def __init__(self, parent, db, task_id, on_saved):
        super().__init__(parent)
        self.db = db
        self.task_id = task_id
        self.on_saved = on_saved

        row = db.get_task(task_id)
        if not row:
            self.destroy()
            return
        subject, priority, deadline, repeat = row

        self.title("Edit Task")
        self.geometry("440x390")
        self.resizable(False, False)
        self.configure(fg_color=BG)
        self.transient(parent)
        set_window_icon(self)
        self.after(150, self._late_init)

        ctk.CTkLabel(
            self, text="Edit Task", font=("Arial", 20, "bold"), text_color=TEXT
        ).pack(anchor="w", padx=24, pady=(20, 12))

        self.subject_entry = ctk.CTkEntry(self, height=38)
        self.subject_entry.insert(0, subject)
        self.subject_entry.pack(fill="x", padx=24, pady=(0, 12))

        row2 = ctk.CTkFrame(self, fg_color="transparent")
        row2.pack(fill="x", padx=24, pady=(0, 12))

        self.priority_menu = ctk.CTkOptionMenu(
            row2, values=PRIORITIES, width=110, height=36
        )
        self.priority_menu.set(priority if priority in PRIORITIES else "Medium")
        self.priority_menu.pack(side="left", padx=(0, 10))

        self.date_picker = DatePicker(row2, deadline or "")
        self.date_picker.pack(side="left", padx=(0, 10))

        self.no_deadline_var = tk.BooleanVar(value=not deadline)
        ctk.CTkCheckBox(
            row2, text="No deadline", variable=self.no_deadline_var,
            text_color=TEXT, width=100
        ).pack(side="left")

        row3 = ctk.CTkFrame(self, fg_color="transparent")
        row3.pack(fill="x", padx=24, pady=(0, 12))

        self.repeat_menu = ctk.CTkOptionMenu(
            row3, values=REPEAT_CHOICES, width=130, height=36
        )
        self.repeat_menu.set(repeat_label(repeat))
        self.repeat_menu.pack(side="left")

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(side="bottom", fill="x", padx=24, pady=20)

        ctk.CTkButton(
            buttons, text="Save Changes", command=self.save,
            fg_color=BLUE, width=140
        ).pack(side="left", padx=(0, 10))
        ctk.CTkButton(
            buttons, text="Cancel", command=self.destroy,
            fg_color=MUTED, width=100
        ).pack(side="left")

        # Keyboard: Enter saves, Escape cancels
        self.bind("<Return>", lambda e: self.save())
        self.bind("<Escape>", lambda e: self.destroy())

    def _late_init(self):
        try:
            self.grab_set()
            self.subject_entry.focus_set()
        except Exception:
            pass   # the dialog was closed before this ran

    def save(self):
        subject = self.subject_entry.get().strip()
        deadline = "" if self.no_deadline_var.get() else self.date_picker.get()

        if not subject:
            messagebox.showwarning("Missing task", "Enter a task name.", parent=self)
            return
        if deadline and not validate_date(deadline):
            messagebox.showwarning(
                "Invalid date", "Use YYYY-MM-DD format.", parent=self
            )
            return

        repeat = repeat_key(self.repeat_menu.get())
        if repeat != "none" and not deadline:
            messagebox.showwarning(
                "Repeat needs a date",
                "Repeating tasks need a deadline. Untick 'No deadline' or "
                "set Repeat to 'No repeat'.", parent=self
            )
            return

        self.db.update_task(
            self.task_id, subject, self.priority_menu.get(), deadline, repeat
        )
        self.destroy()
        self.on_saved(self.task_id)


class TasksPage(ctk.CTkFrame):
    FILTERS = ["All", "Pending", "Completed"]
    SORT_OPTIONS = {
        "Sort: Deadline": "deadline",
        "Sort: Priority": "priority",
        "Sort: Newest": "newest",
        "Sort: Subject A-Z": "subject",
    }

    def __init__(self, parent, db):
        super().__init__(parent, fg_color="transparent")
        self.db = db

        ctk.CTkLabel(
            self, text="Manage Tasks",
            font=("Arial", 29, "bold"), text_color=TEXT
        ).pack(anchor="w", pady=(0, 12))

        self._build_form()
        self._build_toolbar()
        self._build_actions()   # packed at the bottom before the table
        self._build_table()
        self.apply_theme()

    # ----- layout ----------------------------------------------------
    def _build_form(self):
        card = ctk.CTkFrame(self, fg_color=CARD, corner_radius=12)
        card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            card, text="Add a Study Task",
            font=("Arial", 16, "bold"), text_color=TEXT
        ).pack(anchor="w", padx=14, pady=(10, 6))

        row1 = ctk.CTkFrame(card, fg_color="transparent")
        row1.pack(fill="x", padx=14, pady=(0, 8))

        self.subject_entry = ctk.CTkEntry(
            row1, placeholder_text="Enter subject or task",
            height=38, corner_radius=8
        )
        self.subject_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.subject_entry.bind("<Return>", lambda e: self.add_task())   # Enter adds

        ctk.CTkButton(
            row1, text="+ Add Task", command=self.add_task,
            height=38, fg_color=BLUE
        ).pack(side="left")

        row2 = ctk.CTkFrame(card, fg_color="transparent")
        row2.pack(fill="x", padx=14, pady=(0, 12))

        self.priority_menu = ctk.CTkOptionMenu(
            row2, values=PRIORITIES, width=110, height=36
        )
        self.priority_menu.set("Medium")
        self.priority_menu.pack(side="left", padx=(0, 10))

        self.date_picker = DatePicker(row2)
        self.date_picker.pack(side="left", padx=(0, 10))

        self.no_deadline_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            row2, text="No deadline", variable=self.no_deadline_var,
            text_color=TEXT, width=100
        ).pack(side="left", padx=(0, 10))

        self.repeat_menu = ctk.CTkOptionMenu(
            row2, values=REPEAT_CHOICES, width=120, height=36
        )
        self.repeat_menu.set(repeat_label("none"))
        self.repeat_menu.pack(side="left")

    def _build_toolbar(self):
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", pady=(0, 10))

        self.search_entry = ctk.CTkEntry(
            toolbar, placeholder_text="🔍  Search tasks...", height=36
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.search_entry.bind("<KeyRelease>", lambda e: self.load_tasks())

        self.filter_menu = ctk.CTkOptionMenu(
            toolbar, values=self.FILTERS, width=110, height=36,
            command=lambda _: self.load_tasks()
        )
        self.filter_menu.set("All")
        self.filter_menu.pack(side="left", padx=(0, 10))

        self.sort_menu = ctk.CTkOptionMenu(
            toolbar, values=list(self.SORT_OPTIONS.keys()), width=160, height=36,
            command=lambda _: self.load_tasks()
        )
        self.sort_menu.set("Sort: Deadline")
        self.sort_menu.pack(side="left")

    def _build_actions(self):
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(side="bottom", fill="x", pady=(10, 0))

        ctk.CTkButton(
            actions, text="✓ Toggle Completed",
            command=self.toggle_task, fg_color=GREEN, width=160
        ).pack(side="left", padx=(0, 10))
        ctk.CTkButton(
            actions, text="✎ Edit Task",
            command=self.edit_selected, fg_color=BLUE, width=120
        ).pack(side="left", padx=(0, 10))
        ctk.CTkButton(
            actions, text="Delete Task",
            command=self.delete_task, fg_color=RED, width=120
        ).pack(side="left")
        ctk.CTkButton(
            actions, text="⬇ Export CSV",
            command=self.export_csv, fg_color=MUTED, width=130
        ).pack(side="right")

    def _build_table(self):
        frame = ctk.CTkFrame(self, fg_color=CARD, corner_radius=12)
        frame.pack(fill="both", expand=True)

        columns = ("Subject", "Priority", "Deadline", "Repeat", "Status")
        self.table = ttk.Treeview(
            frame, columns=columns, show="headings", height=10
        )
        for column in columns:
            self.table.heading(column, text=column)
            self.table.column(column, width=110, anchor="center")
        self.table.column("Subject", width=240, anchor="w")
        self.table.column("Repeat", width=90, anchor="center")

        scroll = ctk.CTkScrollbar(frame, command=self.table.yview)
        self.table.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y", padx=(0, 6), pady=10)
        self.table.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)

        self.table.bind("<Double-1>", self._on_double_click)
        self.table.bind("<Delete>", lambda e: self._key_action(self.delete_task))
        self.table.bind("<Return>", lambda e: self._key_action(self.edit_selected))

    # ----- theming ---------------------------------------------------
    def apply_theme(self):
        """The ttk Treeview isn't theme-aware, so restyle it by hand."""
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Treeview", rowheight=32, font=("Arial", 10),
            background=pick(CARD), fieldbackground=pick(CARD),
            foreground=pick(TEXT), borderwidth=0
        )
        style.configure(
            "Treeview.Heading", font=("Arial", 10, "bold"),
            background=pick(TABLE_HEADER), foreground=pick(TEXT), relief="flat"
        )
        style.map(
            "Treeview",
            background=[("selected", pick(TABLE_SELECT))],
            foreground=[("selected", pick(TEXT))]
        )

        mode = ctk.get_appearance_mode()
        for tag, palette in TAG_PALETTE.items():
            background, foreground = palette[mode]
            self.table.tag_configure(tag, background=background, foreground=foreground)

    # ----- data ------------------------------------------------------
    def on_show(self):
        self.load_tasks()

    def load_tasks(self, select_id=None):
        for item in self.table.get_children():
            self.table.delete(item)

        rows = self.db.list_tasks(
            search=self.search_entry.get().strip(),
            status=self.filter_menu.get(),
            sort=self.SORT_OPTIONS[self.sort_menu.get()],
        )
        for task_id, subject, priority, deadline, completed, repeat in rows:
            status, tag = deadline_status(deadline, completed)
            self.table.insert(
                "", "end", iid=str(task_id),
                values=(
                    subject,
                    PRIORITY_LABELS.get(priority, "● Medium"),
                    deadline or "—",
                    repeat_label(repeat) if repeat and repeat != "none" else "—",
                    status,
                ),
                tags=(tag,) if tag else ()
            )

        if select_id is not None and self.table.exists(str(select_id)):
            self.table.selection_set(str(select_id))
            self.table.see(str(select_id))

    def _selected_id(self):
        selected = self.table.selection()
        if not selected:
            messagebox.showwarning("Select task", "Select a task first.")
            return None
        return int(selected[0])

    # ----- actions ---------------------------------------------------
    def add_task(self):
        subject = self.subject_entry.get().strip()
        deadline = "" if self.no_deadline_var.get() else self.date_picker.get()

        if not subject:
            messagebox.showwarning("Missing task", "Enter a task name.")
            return
        if deadline and not validate_date(deadline):
            messagebox.showwarning("Invalid date", "Use YYYY-MM-DD format.")
            return

        repeat = repeat_key(self.repeat_menu.get())
        if repeat != "none" and not deadline:
            messagebox.showwarning(
                "Repeat needs a date",
                "Repeating tasks need a deadline. Untick 'No deadline' or "
                "set Repeat to 'No repeat'."
            )
            return

        new_id = self.db.add_task(subject, deadline, self.priority_menu.get(), repeat)
        self.subject_entry.delete(0, "end")
        self.priority_menu.set("Medium")
        self.repeat_menu.set(repeat_label("none"))
        self.load_tasks(select_id=new_id)

    def toggle_task(self):
        task_id = self._selected_id()
        if task_id is None:
            return
        self.db.toggle_task(task_id)
        self.load_tasks(select_id=task_id)

    def delete_task(self):
        task_id = self._selected_id()
        if task_id is None:
            return

        name = self.table.item(str(task_id))["values"][0]
        if not messagebox.askyesno(
            "Delete task", f'Delete "{name}"?\n\nThis cannot be undone.'
        ):
            return

        self.db.delete_task(task_id)
        self.load_tasks()

    def _key_action(self, action):
        """Run an action from a key press, but only if a row is selected."""
        if self.table.selection():
            action()

    def export_csv(self):
        rows = self.db.export_tasks()
        if not rows:
            messagebox.showinfo("Export", "There are no tasks to export yet.")
            return

        path = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(), title="Export tasks",
            defaultextension=".csv", filetypes=[("CSV files", "*.csv")],
            initialfile=f"focusflow_tasks_{date.today().isoformat()}.csv"
        )
        if not path:
            return

        try:
            # utf-8-sig so Excel opens accented characters correctly
            with open(path, "w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.writer(handle)
                writer.writerow([
                    "Subject", "Priority", "Deadline", "Repeat",
                    "Status", "Completed On", "Created At",
                ])
                for (subject, priority, deadline, done,
                     done_on, created, repeat) in rows:
                    status, _ = deadline_status(deadline, done)
                    writer.writerow([
                        _safe_cell(subject), priority or "Medium", deadline or "",
                        repeat_label(repeat) if repeat and repeat != "none" else "",
                        status, done_on or "", created or "",
                    ])
        except OSError as error:
            messagebox.showerror("Export failed", f"Could not save the file:\n{error}")
            return

        messagebox.showinfo("Export complete", f"Saved {len(rows)} tasks to:\n{path}")

    def edit_selected(self):
        task_id = self._selected_id()
        if task_id is not None:
            self._open_editor(task_id)

    def _on_double_click(self, event):
        row = self.table.identify_row(event.y)
        if row:
            self._open_editor(int(row))

    def _open_editor(self, task_id):
        EditTaskDialog(
            self.winfo_toplevel(), self.db, task_id,
            on_saved=lambda tid: self.load_tasks(select_id=tid)
        )
