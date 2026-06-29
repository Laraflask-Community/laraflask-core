"""Schedule - The Laraflask scheduler."""

from __future__ import annotations
import time
import datetime
import logging
import subprocess
import threading
from typing import Any, Callable, List

from laraflask.scheduler.scheduled_event import ScheduledEvent

logger = logging.getLogger('laraflask.scheduler')


class Schedule:
    """
    The Laraflask scheduler.

    Usage in routes/console.py:
        Schedule.command('backup:run').daily()
        Schedule.call(my_function).hourly()
        Schedule.job(MyJob).everyFiveMinutes()
    """

    _events: List[ScheduledEvent] = []

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
    def get_events(cls) -> List[ScheduledEvent]:
        return cls._events

    @classmethod
    def due_events(cls, now: datetime.datetime = None) -> List[ScheduledEvent]:
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
