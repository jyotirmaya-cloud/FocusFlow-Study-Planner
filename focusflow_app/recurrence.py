"""Rules for repeating tasks. Pure Python, no UI."""
import calendar
from datetime import date, datetime, timedelta

REPEAT_LABELS = {
    "none": "No repeat",
    "daily": "Daily",
    "weekly": "Weekly",
    "monthly": "Monthly",
}
REPEAT_CHOICES = list(REPEAT_LABELS.values())


def repeat_key(label):
    """Menu label -> stored key ('Weekly' -> 'weekly')."""
    for key, text in REPEAT_LABELS.items():
        if text == label:
            return key
    return "none"


def repeat_label(key):
    return REPEAT_LABELS.get(key or "none", "No repeat")


def add_months(day, months):
    index = day.month - 1 + months
    year = day.year + index // 12
    month = index % 12 + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def next_occurrence(deadline, repeat, today=None):
    """Next due date after `deadline` that is still in the future.

    If you finish a task late, the next one skips past today instead of being
    born overdue. Monthly steps always count from the original date, so
    Jan 31 -> Feb 28 -> Mar 31 (no drifting to the 28th).
    Returns None if the task isn't a valid repeating task.
    """
    if repeat not in ("daily", "weekly", "monthly"):
        return None
    try:
        due = datetime.strptime(deadline, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None

    today = today or date.today()
    step = 1
    while True:
        if repeat == "daily":
            candidate = due + timedelta(days=step)
        elif repeat == "weekly":
            candidate = due + timedelta(weeks=step)
        else:
            candidate = add_months(due, step)
        if candidate > today:
            return candidate
        step += 1
