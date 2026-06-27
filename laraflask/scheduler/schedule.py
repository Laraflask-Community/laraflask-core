"""
Laraflask Scheduler
Elegant task scheduling with cron-like expressiveness.
"""

from __future__ import annotations
import os
import time
import datetime
import logging
import subprocess
import threading
from typing import Any, Callable, List, Optional

logger = logging.getLogger('laraflask.scheduler')


class ScheduledEvent:
    """A scheduled event/task."""

    def __init__(self, callback: Any, description: str = ''):
        self._callback = callback
        self._description = description
        self._expression = '* * * * *'
        self._timezone = 'UTC'
        self._output_path: Optional[str] = None
        self._append_output = False
        self._without_overlapping = False
        self._run_in_background = False
        self._even_in_maintenance = False
        self._filters: List[Callable] = []
        self._rejects: List[Callable] = []
        self._before_callbacks: List[Callable] = []
        self._after_callbacks: List[Callable] = []
        self._last_run: Optional[datetime.datetime] = None

    # ─── Frequency ────────────────────────────────────────────────────────────

    def cron(self, expression: str) -> 'ScheduledEvent':
        self._expression = expression
        return self

    def every_minute(self) -> 'ScheduledEvent':
        return self.cron('* * * * *')

    def every_two_minutes(self) -> 'ScheduledEvent':
        return self.cron('*/2 * * * *')

    def every_five_minutes(self) -> 'ScheduledEvent':
        return self.cron('*/5 * * * *')

    def every_ten_minutes(self) -> 'ScheduledEvent':
        return self.cron('*/10 * * * *')

    def every_fifteen_minutes(self) -> 'ScheduledEvent':
        return self.cron('*/15 * * * *')

    def every_thirty_minutes(self) -> 'ScheduledEvent':
        return self.cron('*/30 * * * *')

    def hourly(self) -> 'ScheduledEvent':
        return self.cron('0 * * * *')

    def hourly_at(self, minute: int) -> 'ScheduledEvent':
        return self.cron(f"{minute} * * * *")

    def every_two_hours(self) -> 'ScheduledEvent':
        return self.cron('0 */2 * * *')

    def every_three_hours(self) -> 'ScheduledEvent':
        return self.cron('0 */3 * * *')

    def every_six_hours(self) -> 'ScheduledEvent':
        return self.cron('0 */6 * * *')

    def daily(self) -> 'ScheduledEvent':
        return self.cron('0 0 * * *')

    def daily_at(self, time_str: str) -> 'ScheduledEvent':
        parts = time_str.split(':')
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        return self.cron(f"{minute} {hour} * * *")

    def twice_daily(self, first: int = 1, second: int = 13) -> 'ScheduledEvent':
        return self.cron(f"0 {first},{second} * * *")

    def weekly(self) -> 'ScheduledEvent':
        return self.cron('0 0 * * 0')

    def weekly_on(self, day_of_week: int, time_str: str = '0:0') -> 'ScheduledEvent':
        parts = time_str.split(':')
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        return self.cron(f"{minute} {hour} * * {day_of_week}")

    def monthly(self) -> 'ScheduledEvent':
        return self.cron('0 0 1 * *')

    def monthly_on(self, day: int = 1, time_str: str = '0:0') -> 'ScheduledEvent':
        parts = time_str.split(':')
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        return self.cron(f"{minute} {hour} {day} * *")

    def quarterly(self) -> 'ScheduledEvent':
        return self.cron('0 0 1 1,4,7,10 *')

    def yearly(self) -> 'ScheduledEvent':
        return self.cron('0 0 1 1 *')

    def yearly_on(self, month: int = 1, day: int = 1, time_str: str = '0:0') -> 'ScheduledEvent':
        parts = time_str.split(':')
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        return self.cron(f"{minute} {hour} {day} {month} *")

    # ─── Day Constraints ──────────────────────────────────────────────────────

    def weekdays(self) -> 'ScheduledEvent':
        parts = self._expression.split()
        parts[4] = '1-5'
        return self.cron(' '.join(parts))

    def weekends(self) -> 'ScheduledEvent':
        parts = self._expression.split()
        parts[4] = '0,6'
        return self.cron(' '.join(parts))

    def sundays(self) -> 'ScheduledEvent':
        parts = self._expression.split()
        parts[4] = '0'
        return self.cron(' '.join(parts))

    def mondays(self) -> 'ScheduledEvent':
        parts = self._expression.split()
        parts[4] = '1'
        return self.cron(' '.join(parts))

    def tuesdays(self) -> 'ScheduledEvent':
        parts = self._expression.split()
        parts[4] = '2'
        return self.cron(' '.join(parts))

    def wednesdays(self) -> 'ScheduledEvent':
        parts = self._expression.split()
        parts[4] = '3'
        return self.cron(' '.join(parts))

    def thursdays(self) -> 'ScheduledEvent':
        parts = self._expression.split()
        parts[4] = '4'
        return self.cron(' '.join(parts))

    def fridays(self) -> 'ScheduledEvent':
        parts = self._expression.split()
        parts[4] = '5'
        return self.cron(' '.join(parts))

    def saturdays(self) -> 'ScheduledEvent':
        parts = self._expression.split()
        parts[4] = '6'
        return self.cron(' '.join(parts))

    # ─── Options ──────────────────────────────────────────────────────────────

    def timezone(self, tz: str) -> 'ScheduledEvent':
        self._timezone = tz
        return self

    def without_overlapping(self) -> 'ScheduledEvent':
        self._without_overlapping = True
        return self

    def run_in_background(self) -> 'ScheduledEvent':
        self._run_in_background = True
        return self

    def even_in_maintenance_mode(self) -> 'ScheduledEvent':
        self._even_in_maintenance = True
        return self

    def send_output_to(self, path: str, append: bool = False) -> 'ScheduledEvent':
        self._output_path = path
        self._append_output = append
        return self

    def append_output_to(self, path: str) -> 'ScheduledEvent':
        return self.send_output_to(path, append=True)

    def description(self, description: str) -> 'ScheduledEvent':
        self._description = description
        return self

    # ─── Conditions ───────────────────────────────────────────────────────────

    def when(self, callback: Callable) -> 'ScheduledEvent':
        self._filters.append(callback)
        return self

    def skip(self, callback: Callable) -> 'ScheduledEvent':
        self._rejects.append(callback)
        return self

    def environments(self, *envs: str) -> 'ScheduledEvent':
        return self.when(lambda: os.getenv('APP_ENV', 'production') in envs)

    # ─── Hooks ────────────────────────────────────────────────────────────────

    def before(self, callback: Callable) -> 'ScheduledEvent':
        self._before_callbacks.append(callback)
        return self

    def after(self, callback: Callable) -> 'ScheduledEvent':
        self._after_callbacks.append(callback)
        return self

    def on_success(self, callback: Callable) -> 'ScheduledEvent':
        return self.after(callback)

    def on_failure(self, callback: Callable) -> 'ScheduledEvent':
        self._after_callbacks.append(callback)
        return self

    def ping(self, url: str) -> 'ScheduledEvent':
        """Ping a URL after the event runs."""
        def _ping():
            try:
                import urllib.request
                urllib.request.urlopen(url, timeout=5)
            except Exception:
                pass
        return self.after(_ping)

    def ping_before(self, url: str) -> 'ScheduledEvent':
        def _ping():
            try:
                import urllib.request
                urllib.request.urlopen(url, timeout=5)
            except Exception:
                pass
        return self.before(_ping)

    # ─── Execution ────────────────────────────────────────────────────────────

    def is_due(self, now: datetime.datetime = None) -> bool:
        """Check if this event should run now."""
        now = now or datetime.datetime.now()

        for f in self._filters:
            if not f():
                return False

        for r in self._rejects:
            if r():
                return False

        return self._matches_cron(now)

    def _matches_cron(self, dt: datetime.datetime) -> bool:
        """Match datetime against cron expression."""
        try:
            from croniter import croniter
            return croniter.match(self._expression, dt)
        except ImportError:
            # Simple fallback
            parts = self._expression.split()
            if len(parts) != 5:
                return False
            minute, hour, dom, month, dow = parts
            return (
                self._field_match(minute, dt.minute) and
                self._field_match(hour, dt.hour) and
                self._field_match(dom, dt.day) and
                self._field_match(month, dt.month) and
                self._field_match(dow, dt.weekday())
            )

    def _field_match(self, field: str, value: int) -> bool:
        if field == '*':
            return True
        if ',' in field:
            return value in [int(v) for v in field.split(',')]
        if '-' in field:
            start, end = field.split('-')
            return int(start) <= value <= int(end)
        if '/' in field:
            _, step = field.split('/')
            return value % int(step) == 0
        return value == int(field)

    def run(self) -> None:
        """Execute this scheduled event."""
        for cb in self._before_callbacks:
            try:
                cb()
            except Exception as e:
                logger.error(f"Before callback error: {e}")

        logger.info(f"Running [{self._description or 'scheduled task'}]")

        try:
            if callable(self._callback):
                output = self._callback()
            elif isinstance(self._callback, str):
                result = subprocess.run(
                    self._callback, shell=True, capture_output=True, text=True
                )
                output = result.stdout

            if self._output_path and output:
                mode = 'a' if self._append_output else 'w'
                with open(self._output_path, mode) as f:
                    f.write(str(output))

            self._last_run = datetime.datetime.now()

        except Exception as e:
            logger.error(f"Scheduled task failed: {e}")

        for cb in self._after_callbacks:
            try:
                cb()
            except Exception as e:
                logger.error(f"After callback error: {e}")

    def summary(self) -> str:
        return f"{self._expression} -> {self._description or str(self._callback)}"


class Schedule:
    """
    The Laraflask scheduler.

    Usage in routes/console.py:
        Schedule.command('backup:run').daily()
        Schedule.call(my_function).hourly()
        Schedule.job(MyJob).everyFiveMinutes()
    """

    _events: List[Event] = []

    @classmethod
    def call(cls, callback: Callable, description: str = '') -> ScheduledEvent:
        """Schedule a closure/function."""
        event = ScheduledEvent(callback, description)
        cls._events.append(event)
        return event

    @classmethod
    def command(cls, command: str, parameters: List = None) -> ScheduledEvent:
        """Schedule an Artisan command."""
        cmd_parts = ['python', 'artisan.py', command]
        if parameters:
            cmd_parts.extend([str(p) for p in parameters])
        full_cmd = ' '.join(cmd_parts)
        event = ScheduledEvent(lambda: subprocess.run(full_cmd, shell=True), command)
        cls._events.append(event)
        return event

    @classmethod
    def job(cls, job_class: Any, queue: str = None) -> ScheduledEvent:
        """Schedule a queue job."""
        from laraflask.queue.queue import dispatch
        def run_job():
            job = job_class()
            if queue:
                job.queue = queue
            dispatch(job)
        event = ScheduledEvent(run_job, job_class.__name__)
        cls._events.append(event)
        return event

    @classmethod
    def exec(cls, command: str) -> ScheduledEvent:
        """Schedule a shell command."""
        event = ScheduledEvent(lambda: subprocess.run(command, shell=True), command)
        cls._events.append(event)
        return event

    @classmethod
    def get_events(cls) -> List[Event]:
        return cls._events

    @classmethod
    def due_events(cls, now: datetime.datetime = None) -> List[Event]:
        now = now or datetime.datetime.now()
        return [e for e in cls._events if e.is_due(now)]

    @classmethod
    def run_due(cls) -> int:
        """Run all due events."""
        events = cls.due_events()
        for event in events:
            event.run()
        return len(events)

    @classmethod
    def start_daemon(cls, tick: int = 60) -> None:
        """Start the scheduler daemon."""
        logger.info("Scheduler daemon started")
        while True:
            cls.run_due()
            time.sleep(tick)

    @classmethod
    def start_in_thread(cls) -> threading.Thread:
        """Start scheduler in a background thread."""
        thread = threading.Thread(target=cls.start_daemon, daemon=True)
        thread.start()
        return thread

    @classmethod
    def list(cls) -> List[str]:
        return [e.summary() for e in cls._events]
