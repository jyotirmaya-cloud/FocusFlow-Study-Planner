"""Pomodoro timer logic. No UI code: the page passes in callbacks."""


class PomodoroTimer:
    def __init__(self, scheduler, focus_minutes=25, break_minutes=5,
                 on_tick=None, on_focus_done=None, on_break_done=None):
        # scheduler is any tkinter widget (needs after / after_cancel)
        self.scheduler = scheduler
        self.focus_seconds = focus_minutes * 60
        self.break_seconds = break_minutes * 60
        self.remaining = self.focus_seconds
        self.running = False
        self.is_break = False
        self._job = None

        self.on_tick = on_tick or (lambda remaining: None)
        self.on_focus_done = on_focus_done or (lambda: None)
        self.on_break_done = on_break_done or (lambda: None)

    # ----- controls --------------------------------------------------
    def start(self):
        if self.running:
            return
        if self.remaining == 0:
            self.reset()
        self.running = True
        self._job = self.scheduler.after(1000, self._tick)

    def pause(self):
        self.running = False
        self.cancel()

    def reset(self):
        self.pause()
        self.is_break = False
        self.remaining = self.focus_seconds
        self.on_tick(self.remaining)

    def start_break(self):
        self.pause()
        self.is_break = True
        self.remaining = self.break_seconds
        self.on_tick(self.remaining)
        self.start()

    def set_durations(self, focus_minutes, break_minutes):
        self.focus_seconds = focus_minutes * 60
        self.break_seconds = break_minutes * 60
        self.reset()

    def cancel(self):
        if self._job is not None:
            self.scheduler.after_cancel(self._job)
            self._job = None

    # ----- internals -------------------------------------------------
    def _tick(self):
        self._job = None
        if not self.running:
            return

        self.remaining -= 1
        self.on_tick(self.remaining)

        if self.remaining > 0:
            self._job = self.scheduler.after(1000, self._tick)
            return

        # Time is up
        self.running = False
        self.scheduler.update_idletasks()
        if self.is_break:
            self.on_break_done()
        else:
            self.on_focus_done()
