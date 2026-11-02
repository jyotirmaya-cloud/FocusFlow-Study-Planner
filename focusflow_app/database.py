"""All SQLite access for FocusFlow. No UI code in here."""
import sqlite3
from datetime import date, datetime, timedelta

from recurrence import next_occurrence

SORT_SQL = {
    "deadline": "(deadline IS NULL OR deadline = ''), deadline, id",
    "priority": "CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END, id",
    "newest": "id DESC",
    "subject": "subject COLLATE NOCASE",
}


class Database:
    def __init__(self, path):
        self.conn = sqlite3.connect(path)
        self._create_tables()

    # ----- setup -----------------------------------------------------
    def _create_tables(self):
        c = self.conn
        c.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                deadline TEXT,
                completed INTEGER DEFAULT 0
            )
        """)

        # Add newer columns to databases created by older versions
        existing = [row[1] for row in c.execute("PRAGMA table_info(tasks)")]
        for name, ddl in [
            ("priority", "TEXT DEFAULT 'Medium'"),
            ("created_at", "TEXT"),
            ("completed_on", "TEXT"),
            ("repeat", "TEXT DEFAULT 'none'"),
            ("next_task_id", "INTEGER"),
        ]:
            if name not in existing:
                c.execute(f"ALTER TABLE tasks ADD COLUMN {name} {ddl}")

        c.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER,
                task_name TEXT,
                duration INTEGER NOT NULL,
                session_date TEXT NOT NULL,
                completed_at TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        c.commit()

    def close(self):
        self.conn.close()

    # ----- settings --------------------------------------------------
    def get_int(self, key, default):
        row = self.conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        try:
            return int(row[0]) if row else default
        except ValueError:
            return default

    def set_setting(self, key, value):
        self.conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, str(value))
        )
        self.conn.commit()

    # ----- tasks -----------------------------------------------------
    def add_task(self, subject, deadline, priority, repeat="none"):
        cur = self.conn.execute(
            "INSERT INTO tasks (subject, deadline, priority, repeat, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (subject, deadline, priority, repeat,
             datetime.now().isoformat(timespec="seconds"))
        )
        self.conn.commit()
        return cur.lastrowid

    def get_task(self, task_id):
        return self.conn.execute(
            "SELECT subject, priority, deadline, repeat FROM tasks WHERE id = ?",
            (task_id,)
        ).fetchone()

    def update_task(self, task_id, subject, priority, deadline, repeat="none"):
        self.conn.execute(
            "UPDATE tasks SET subject = ?, priority = ?, deadline = ?, repeat = ? "
            "WHERE id = ?",
            (subject, priority, deadline, repeat, task_id)
        )
        self.conn.commit()

    def toggle_task(self, task_id):
        """Flip done/pending. Returns the id of a newly created repeat, if any."""
        row = self.conn.execute(
            "SELECT completed, subject, priority, deadline, repeat, next_task_id "
            "FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if row is None:
            return None
        was_done, subject, priority, deadline, repeat, next_id = row

        self.conn.execute(
            "UPDATE tasks SET completed = 1 - completed, "
            "completed_on = CASE WHEN completed = 0 THEN ? ELSE NULL END "
            "WHERE id = ?",
            (date.today().isoformat(), task_id)
        )

        # Finishing a repeating task creates the next one. next_task_id makes
        # sure un-ticking and re-ticking never creates a duplicate.
        new_id = None
        if not was_done and next_id is None:
            following = next_occurrence(deadline, repeat)
            if following:
                cur = self.conn.execute(
                    "INSERT INTO tasks (subject, deadline, priority, repeat, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (subject, following.isoformat(), priority, repeat,
                     datetime.now().isoformat(timespec="seconds"))
                )
                new_id = cur.lastrowid
                self.conn.execute(
                    "UPDATE tasks SET next_task_id = ? WHERE id = ?",
                    (new_id, task_id)
                )
        self.conn.commit()
        return new_id

    def delete_task(self, task_id):
        self.conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self.conn.commit()

    def list_tasks(self, search="", status="All", sort="deadline"):
        where, params = [], []
        if search:
            where.append("subject LIKE ?")
            params.append(f"%{search}%")
        if status == "Pending":
            where.append("completed = 0")
        elif status == "Completed":
            where.append("completed = 1")

        sql = "SELECT id, subject, priority, deadline, completed, repeat FROM tasks"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY completed, " + SORT_SQL.get(sort, SORT_SQL["deadline"])
        return self.conn.execute(sql, params).fetchall()

    def export_tasks(self):
        """Every task with all of its columns, for CSV export."""
        return self.conn.execute(
            "SELECT subject, priority, deadline, completed, completed_on, created_at, "
            "repeat FROM tasks "
            "ORDER BY completed, (deadline IS NULL OR deadline = ''), deadline, id"
        ).fetchall()

    def task_deadlines(self):
        """(deadline, completed) for every task, used for dashboard counts."""
        return self.conn.execute("SELECT deadline, completed FROM tasks").fetchall()

    def pending_tasks(self):
        return self.conn.execute(
            "SELECT id, subject FROM tasks WHERE completed = 0 "
            "ORDER BY (deadline IS NULL OR deadline = ''), deadline, id"
        ).fetchall()

    def upcoming(self, limit=3):
        return self.conn.execute(
            "SELECT subject, deadline FROM tasks "
            "WHERE completed = 0 AND deadline IS NOT NULL AND deadline != '' "
            "ORDER BY deadline, id LIMIT ?", (limit,)
        ).fetchall()

    def reminder_candidates(self):
        """Pending tasks that are overdue or due by tomorrow."""
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        return self.conn.execute(
            "SELECT id, subject, deadline, priority FROM tasks "
            "WHERE completed = 0 AND deadline IS NOT NULL AND deadline != '' "
            "AND deadline <= ? "
            "ORDER BY deadline, "
            "CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END, id",
            (tomorrow,)
        ).fetchall()

    def completed_today(self):
        return self.conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE completed = 1 AND completed_on = ?",
            (date.today().isoformat(),)
        ).fetchone()[0]

    # ----- sessions --------------------------------------------------
    def log_session(self, task_id, task_name, seconds):
        now = datetime.now()
        self.conn.execute(
            "INSERT INTO sessions "
            "(task_id, task_name, duration, session_date, completed_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (task_id, task_name, seconds, now.date().isoformat(),
             now.isoformat(timespec="seconds"))
        )
        self.conn.commit()

    def sessions_today(self):
        """Return (number of sessions, total seconds) for today."""
        return self.conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(duration), 0) FROM sessions "
            "WHERE session_date = ?", (date.today().isoformat(),)
        ).fetchone()

    def total_focus_seconds(self):
        return self.conn.execute(
            "SELECT COALESCE(SUM(duration), 0) FROM sessions"
        ).fetchone()[0]

    def focus_seconds_by_day(self, start_day):
        """Return {iso date: seconds} for every day since start_day."""
        rows = self.conn.execute(
            "SELECT session_date, SUM(duration) FROM sessions "
            "WHERE session_date >= ? GROUP BY session_date",
            (start_day.isoformat(),)
        ).fetchall()
        return {day: (secs or 0) for day, secs in rows}

    def focus_by_subject(self, start_day=None):
        """Return [(subject, sessions, seconds)], biggest focus time first.

        Sessions are grouped by the task name saved when they were logged, so
        deleted tasks still appear. Sessions with no task show as 'Free focus'.
        """
        subject = "COALESCE(NULLIF(task_name, ''), 'Free focus')"
        sql = f"SELECT {subject}, COUNT(*), SUM(duration) FROM sessions"
        params = []
        if start_day is not None:
            sql += " WHERE session_date >= ?"
            params.append(start_day.isoformat())
        sql += f" GROUP BY {subject} ORDER BY SUM(duration) DESC, {subject}"
        return self.conn.execute(sql, params).fetchall()

    def streak(self):
        """Consecutive days with a finished session or a completed task."""
        rows = self.conn.execute(
            "SELECT session_date FROM sessions "
            "UNION SELECT completed_on FROM tasks "
            "WHERE completed = 1 AND completed_on IS NOT NULL"
        ).fetchall()
        active = {row[0] for row in rows if row[0]}

        day = date.today()
        if day.isoformat() not in active:
            day -= timedelta(days=1)   # today isn't over yet

        streak = 0
        while day.isoformat() in active:
            streak += 1
            day -= timedelta(days=1)
        return streak
